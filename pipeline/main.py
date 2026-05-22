import argparse
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.ingestion import ingest_pdf
from pipeline.extractor import GeminiExtractor
from db.storage import RuleStore
from pipeline.logger import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Compliance-as-Code PDF Ingestion Engine")
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF policy document")
    parser.add_argument("--dry-run", action="store_true", help="Extract rules but do not store them in MongoDB")
    
    args = parser.parse_args()
    filename = os.path.basename(args.pdf)
    
    logger.info(f"Starting ingestion for {filename}")
    
    # 1. Ingestion
    try:
        chunks = ingest_pdf(args.pdf)
    except Exception as e:
        logger.error(f"Failed to ingest PDF: {e}")
        sys.exit(1)
        
    # 2. Extraction
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import config
    
    extractor = GeminiExtractor()
    all_rules = []
    
    logger.info(f"Extracting rules from {len(chunks)} chunks concurrently using {config.MAX_WORKERS} workers...")
    
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_chunk = {
            executor.submit(extractor.extract_rules, chunk, filename): (i, chunk)
            for i, chunk in enumerate(chunks, 1)
        }
        
        for future in as_completed(future_to_chunk):
            i, chunk = future_to_chunk[future]
            try:
                rules = future.result()
                logger.info(f"[{i}/{len(chunks)}] Finished '{chunk.title}': Extracted {len(rules)} rules.")
                all_rules.extend(rules)
            except Exception as e:
                logger.error(f"[{i}/{len(chunks)}] Extraction failed for '{chunk.title}': {e}")
        
    if not all_rules:
        logger.warning("No rules were extracted from the document.")
        sys.exit(0)
        
    # 3. Storage
    if args.dry_run:
        logger.info(f"[DRY-RUN] Would have upserted {len(all_rules)} rules to MongoDB.")
        for r in all_rules:
            print(r.model_dump_json(indent=2))
    else:
        store = RuleStore()
        logger.info(f"Upserting {len(all_rules)} rules to MongoDB...")
        stats = store.upsert_rules_batch(all_rules)
        logger.info(f"Storage complete. Stats: {stats}")

if __name__ == "__main__":
    main()
