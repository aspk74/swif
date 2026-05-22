import hashlib
import json
import time
from typing import List
from pydantic import ValidationError
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from pipeline.logger import get_logger
from db.schema import LLMExtractionResult, SecurityRule
from pipeline.ingestion import Chunk

logger = get_logger(__name__)

def generate_rule_id(category: str, technical_parameter: str, expected_value: str) -> str:
    """Deterministically generates a collision-resistant rule ID based on content hash."""
    slug = category.lower().replace(" ", "_")[:20]
    content_str = f"{technical_parameter}::{expected_value}".encode("utf-8")
    content_hash = hashlib.sha256(content_str).hexdigest()[:8]
    return f"{slug}-{content_hash}"


# We retry API errors (e.g. rate limits, 500s) with exponential backoff using Tenacity.
@retry(
    stop=stop_after_attempt(config.MAX_API_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def call_gemini_api(client: genai.Client, prompt: str, schema) -> str:
    """Makes the API call to Gemini with structured output enforcement."""
    # We use Google GenAI SDK's structured output capability if available,
    # or just request JSON. Since the SDK natively supports pydantic schemas in `response_schema`,
    # we'll use that for stronger guarantees.
    
    # Workaround for the schema generation in the GenAI SDK
    response = client.models.generate_content(
        model=config.GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            # We don't enforce response_schema natively here to let Pydantic handle validation/repair
            # to fulfill the requirement of a repair loop. We ask for JSON.
            temperature=0.1
        )
    )
    return response.text

class GeminiExtractor:
    def __init__(self, api_key: str = config.GEMINI_API_KEY):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key)
        
    def extract_rules(self, chunk: Chunk, filename: str) -> List[SecurityRule]:
        """Extracts rules from a chunk using a prompt and schema repair loop."""
        
        system_instructions = f"""
You are an expert cybersecurity architect. Your task is to extract actionable, deterministic security rules from the provided policy text.
You MUST output a valid JSON array of objects. Each object MUST match this schema exactly:
{{
  "suggested_id": "string",
  "category": "string",
  "technical_parameter": "string",
  "expected_value": "string",
  "logic": "string (MUST BE one of: EQUALS, NOT_EQUALS, CONTAINS, NOT_CONTAINS, GREATER_THAN, GREATER_THAN_OR_EQUAL, LESS_THAN, LESS_THAN_OR_EQUAL, REGEX_MATCH, EXISTS)",
  "severity": "string (MUST BE one of: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)"
}}

If a rule contains any other important attributes or contextual details (such as "remediation", "tags", or specific references), you may include them as extra dynamic fields in the JSON object.

If no rules are found, output an empty array [].
"""
        
        prompt = f"{system_instructions}\n\nHere is the policy section '{chunk.title}':\n\n{chunk.text}"
        
        # Repair loop for Schema Validation
        for attempt in range(1, config.MAX_REPAIR_RETRIES + 1):
            try:
                if attempt > 1:
                    time.sleep(config.EXTRACTION_DELAY_SECONDS) # Respect rate limits on retry/repair
                raw_response = call_gemini_api(self.client, prompt, schema=None)
                
                # Try parsing JSON array
                try:
                    data = json.loads(raw_response)
                except json.JSONDecodeError as e:
                    raise ValidationError(f"Invalid JSON: {e}", model=LLMExtractionResult) # Trigger repair
                
                if not isinstance(data, list):
                    raise ValidationError("Response must be a JSON array", model=LLMExtractionResult)
                
                if not data:
                    return [] # Valid empty extraction
                    
                # Try parsing into Pydantic models
                extracted_results = []
                for item in data:
                    # This will raise ValidationError if schema doesn't match
                    result = LLMExtractionResult(**item)
                    extracted_results.append(result)
                
                # If we get here, validation succeeded! Map to full SecurityRule
                final_rules = []
                for res in extracted_results:
                    rule_id = generate_rule_id(res.category, res.technical_parameter, res.expected_value)
                    
                    # Extract any dynamic extra fields from LLMExtractionResult
                    extra_fields = res.model_extra or {}
                    
                    full_rule = SecurityRule(
                        rule_id=rule_id,
                        suggested_id=res.suggested_id,
                        category=res.category,
                        technical_parameter=res.technical_parameter,
                        expected_value=res.expected_value,
                        logic=res.logic,
                        severity=res.severity,
                        source_document=filename,
                        chunk_reference=f"{chunk.title} (Pages {chunk.start_page}-{chunk.end_page})",
                        **extra_fields
                    )
                    final_rules.append(full_rule)
                    
                # Secondary Guardrail: Verify the extracted rules against the source text
                verified_rules = self.verify_rules(chunk, final_rules)
                return verified_rules
                
            except ValidationError as ve:
                logger.warning(f"Schema validation failed on attempt {attempt}: {ve}")
                if attempt == config.MAX_REPAIR_RETRIES:
                    logger.error(f"Failed to repair schema after {config.MAX_REPAIR_RETRIES} attempts.")
                    return []
                
                # Append the error and prompt again for repair
                prompt += f"\n\nYOUR PREVIOUS RESPONSE FAILED VALIDATION:\n{ve}\n\nPlease fix the JSON array to strictly conform to the schema."
                
            except Exception as e:
                # If it's an API error that Tenacity gave up on, fail the chunk.
                logger.error(f"API or unexpected error extracting chunk '{chunk.title}': {e}")
                return []
                
        return []

    def verify_rules(self, chunk: Chunk, proposed_rules: List[SecurityRule]) -> List[SecurityRule]:
        """Runs a secondary prompt to verify proposed rules against the source chunk text."""
        if not proposed_rules:
            return []
            
        logger.info(f"Verifying {len(proposed_rules)} proposed rules for chunk '{chunk.title}'...")
        
        # We only need to show the LLM the fields that matter for semantic verification
        simplified_rules = []
        for r in proposed_rules:
            simplified_rules.append({
                "suggested_id": r.suggested_id,
                "technical_parameter": r.technical_parameter,
                "expected_value": r.expected_value,
                "logic": r.logic.value
            })
            
        rules_json = json.dumps(simplified_rules, indent=2)
        
        system_instructions = """
You are a strict compliance auditor. Your job is to verify extracted rules against the original source text.
You must ensure no rules are hallucinated. For each proposed rule, verify that:
1. The technical parameter and expected value are explicitly supported by the text.
2. The logic operator is correct based on the text.

Output a JSON array of boolean values (true or false) corresponding to the validity of each rule in the exact same order as the proposed rules.
For example, if there are 3 rules, output: [true, false, true]
"""
        prompt = f"{system_instructions}\n\nSOURCE TEXT:\n{chunk.text}\n\nPROPOSED RULES:\n{rules_json}"
        
        for attempt in range(1, config.MAX_REPAIR_RETRIES + 1):
            try:
                if attempt > 1:
                    time.sleep(config.EXTRACTION_DELAY_SECONDS)
                raw_response = call_gemini_api(self.client, prompt, schema=None)
                data = json.loads(raw_response)
                
                if not isinstance(data, list) or len(data) != len(proposed_rules):
                    raise ValueError(f"Expected a JSON array of {len(proposed_rules)} booleans.")
                    
                verified_rules = []
                for i, is_valid in enumerate(data):
                    if is_valid is True:
                        verified_rules.append(proposed_rules[i])
                    else:
                        logger.warning(f"Hallucination Guardrail: Rejected hallucinated rule '{proposed_rules[i].suggested_id}' ({proposed_rules[i].technical_parameter}).")
                        
                return verified_rules
                
            except Exception as e:
                logger.warning(f"Verification validation failed on attempt {attempt}: {e}")
                prompt += f"\n\nYOUR PREVIOUS RESPONSE WAS INVALID: {e}\nPlease output ONLY a JSON array of booleans."
                
        logger.error("Verification loop failed completely. Rejecting rules to be safe.")
        return []
