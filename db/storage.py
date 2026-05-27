from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConnectionFailure, BulkWriteError
from typing import List, Optional, Dict
import sys
import os

# Add parent dir to path to import config and logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from db.schema import SecurityRule
from pipeline.logger import get_logger

logger = get_logger(__name__)

class RuleStore:
    def __init__(self, uri: str = config.MONGO_URI, db_name: str = config.DB_NAME, collection_name: str = config.COLLECTION_NAME):
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        
        if self.uri.startswith("mongomock://"):
            import mongomock
            self.client = mongomock.MongoClient()
        else:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            try:
                # Test connection
                self.client.admin.command('ping')
            except ConnectionFailure as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
                
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        
        # Violations collection
        self.violations_collection = self.db[config.VIOLATIONS_COLLECTION_NAME]
        
        # Ensure unique index for deduplication
        self.collection.create_index("rule_id", unique=True)
        logger.info(f"Connected to MongoDB at {self.uri}, database: {self.db_name}, collection: {self.collection_name}")

    def upsert_rule(self, rule: SecurityRule) -> bool:
        """
        Upserts a single rule. Uses rule_id for deduplication.
        Returns True if a new rule was inserted, False if updated/already existed.
        """
        rule_dict = rule.model_dump(mode='json')
        
        # Don't overwrite created_at on updates
        created_at = rule_dict.pop('created_at')
        
        update_op = {
            "$set": rule_dict,
            "$setOnInsert": {"created_at": created_at}
        }
        
        result = self.collection.update_one(
            {"rule_id": rule.rule_id},
            update_op,
            upsert=True
        )
        
        return result.upserted_id is not None

    def upsert_rules_batch(self, rules: List[SecurityRule]) -> dict:
        """
        Bulk upserts multiple rules. Performs in-memory deduplication first.
        Returns stats about the operation.
        """
        if not rules:
            return {"inserted": 0, "updated": 0, "duplicates_in_batch": 0}

        # In-memory deduplication for the batch
        unique_rules = {}
        duplicates_in_batch = 0
        
        for rule in rules:
            if rule.rule_id in unique_rules:
                duplicates_in_batch += 1
            else:
                unique_rules[rule.rule_id] = rule
                
        operations = []
        for rule_id, rule in unique_rules.items():
            rule_dict = rule.model_dump(mode='json')
            created_at = rule_dict.pop('created_at')
            
            operations.append(
                UpdateOne(
                    {"rule_id": rule_id},
                    {
                        "$set": rule_dict,
                        "$setOnInsert": {"created_at": created_at}
                    },
                    upsert=True
                )
            )

        try:
            result = self.collection.bulk_write(operations, ordered=False)
            return {
                "inserted": result.upserted_count,
                "updated": result.modified_count,
                "duplicates_in_batch": duplicates_in_batch
            }
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error: {bwe.details}")
            # Even on error, some might have succeeded
            return {
                "inserted": bwe.details.get('nUpserted', 0),
                "updated": bwe.details.get('nModified', 0),
                "duplicates_in_batch": duplicates_in_batch,
                "error": str(bwe)
            }

    def get_rule(self, rule_id: str) -> Optional[dict]:
        """Fetch a single rule by ID."""
        return self.collection.find_one({"rule_id": rule_id}, {"_id": 0})
        
    def get_all_rules(self, unique: bool = True, similarity_threshold: float = 0.8) -> List[dict]:
        """Fetch all rules, optionally deduplicating similar ones."""
        rules = list(self.collection.find({}, {"_id": 0}))
        if not unique:
            return rules

        # Group rules by category to optimize comparisons
        by_category = {}
        for rule in rules:
            cat = rule.get("category", "")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(rule)

        unique_rules = []
        for cat, cat_rules in by_category.items():
            cat_unique = []
            for rule in cat_rules:
                is_duplicate = False
                for u_rule in cat_unique:
                    if self._are_rules_similar(rule, u_rule, similarity_threshold):
                        is_duplicate = True
                        logger.info(
                            f"Filtered out duplicate rule in category '{cat}': "
                            f"'{rule.get('technical_parameter')}' is similar to '{u_rule.get('technical_parameter')}'"
                        )
                        break
                if not is_duplicate:
                    cat_unique.append(rule)
            unique_rules.extend(cat_unique)

        return unique_rules

    def get_all_rules_as_dict(self) -> Dict[str, dict]:
        """
        Returns all rules keyed by technical_parameter for O(1) cache lookups.
        If multiple rules share the same technical_parameter, only the first is kept
        (this is fine — rules should have unique parameters after deduplication).
        """
        rules = list(self.collection.find({}, {"_id": 0}))
        rules_dict = {}
        for rule in rules:
            param = rule.get("technical_parameter", "")
            if param and param not in rules_dict:
                rules_dict[param] = rule
        return rules_dict

    def insert_violation(self, violation_dict: dict) -> str:
        """
        Inserts a compliance violation document into the violations collection.
        Returns the inserted document's _id as a string.
        """
        result = self.violations_collection.insert_one(violation_dict)
        logger.info(
            f"Violation recorded: device={violation_dict.get('device_id')}, "
            f"rule={violation_dict.get('suggested_id')}, "
            f"severity={violation_dict.get('severity')}",
        )
        return str(result.inserted_id)

    def _are_rules_similar(self, r1: dict, r2: dict, threshold: float = 0.8) -> bool:
        """Helper to check if two rules are similar using difflib.SequenceMatcher."""
        # Must be in the same category (already handled by grouping, but good safeguard)
        if r1.get("category") != r2.get("category"):
            return False

        # If logic or expected value are completely different, they are distinct checks
        if r1.get("logic") != r2.get("logic") or r1.get("expected_value") != r2.get("expected_value"):
            return False

        # Compare similarity of the technical_parameter text using built-in SequenceMatcher
        from difflib import SequenceMatcher
        p1 = r1.get("technical_parameter", "")
        p2 = r2.get("technical_parameter", "")

        similarity = SequenceMatcher(None, p1, p2).ratio()
        return similarity >= threshold

    def get_all_violations(self, limit=100, skip=0, status_filter=None) -> list[dict]:
        """Fetch violations with pagination and optional status filter."""
        query = {}
        if status_filter and status_filter != "all":
            query["action_taken"] = status_filter
        
        # Need to convert ObjectId to string for JSON serialization later
        violations = list(
            self.violations_collection
                .find(query)
                .sort("violated_at", -1)
                .skip(skip)
                .limit(limit)
        )
        for v in violations:
            v["_id"] = str(v["_id"])
        return violations

    def count_violations(self, status_filter=None) -> int:
        """Count violations, optionally filtered by status."""
        query = {}
        if status_filter and status_filter != "all":
            query["action_taken"] = status_filter
        return self.violations_collection.count_documents(query)

    def get_violation_by_id(self, violation_id: str) -> dict | None:
        """Fetch a single violation by its _id."""
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            v = self.violations_collection.find_one({"_id": ObjectId(violation_id)})
            if v:
                v["_id"] = str(v["_id"])
            return v
        except InvalidId:
            return None

    def get_active_violation(self, device_id: str, technical_parameter: str) -> dict | None:
        """Fetch the current active (unresolved) violation for a given device and parameter."""
        # Active means it's NOT an AUTOMATED_FIX (i.e. it's still an open issue)
        v = self.violations_collection.find_one({
            "device_id": device_id,
            "technical_parameter": technical_parameter,
            "action_taken": {"$ne": "AUTOMATED_FIX"}
        })
        if v:
            v["_id"] = str(v["_id"])
        return v

    def escalate_expired_grace_periods(self) -> int:
        """Bulk updates all expired GRACE_PERIOD violations to LOGGED_FOR_REVIEW and upgrades severity to HIGH."""
        from datetime import datetime, timezone
        result = self.violations_collection.update_many(
            {
                "action_taken": "GRACE_PERIOD",
                "grace_period_expires_at": {"$lt": datetime.now(timezone.utc).isoformat()}
            },
            {
                "$set": {
                    "action_taken": "LOGGED_FOR_REVIEW",
                    "severity": "HIGH",
                    "remediation_logs": "[SYSTEM AUTOMATION] Grace period expired. Escalated to HIGH risk error and LOGGED_FOR_REVIEW."
                }
            }
        )
        return result.modified_count

    def update_violation(self, violation_id: str, update_data: dict) -> bool:
        """Update a violation document. Returns True if modified."""
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            result = self.violations_collection.update_one(
                {"_id": ObjectId(violation_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except InvalidId:
            return False

    def get_unique_device_count(self) -> int:
        """Count distinct device_ids across all violations."""
        return len(self.violations_collection.distinct("device_id"))
