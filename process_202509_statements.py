#!/usr/bin/env python3
"""
Process All UATL Statements (Newest to Oldest)

Filters all UATL statements from mapper.csv, sorts by date (newest first),
finds them in extracted directory, and processes them through the backend workflow.

Usage:
    python process_202509_statements.py              # Upload and process all
    python process_202509_statements.py --dry-run    # Preview
    python process_202509_statements.py --upload-only # Only upload
    python process_202509_statements.py --month 2025-09 # Only specific month
"""

import sys
import csv
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.db import SessionLocal
from backend.app.services import crud_v2 as crud
from backend.app.services.parsers import get_parser
from backend.app.services.mapper import enrich_metadata_with_mapper
from backend.app.services.processor import process_statement
from backend.app.models.metadata import Metadata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_202509.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
MAPPER_CSV = Path("/home/ebran/Developer/projects/airtel_fraud_detection/docs/data/statements/mapper.csv")
EXTRACTED_DIR = Path("/home/ebran/Developer/projects/airtel_fraud_detection/docs/data/UATL/extracted")
PROVIDER_CODE = "UATL"


def read_uatl_statements(mapper_csv: Path, target_month: str = None):
    """
    Read mapper.csv and filter UATL statements
    Sorts by date (newest first)

    Args:
        mapper_csv: Path to mapper.csv
        target_month: Optional filter for specific month (e.g., "2025-09")
    """
    statements = []

    with open(mapper_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter for UATL
            if row['acc_prvdr_code'] != 'UATL':
                continue

            # Optional month filter
            if target_month and not row['created_date'].startswith(target_month):
                continue

            statements.append({
                'run_id': row['run_id'],
                'acc_number': row['acc_number'],
                'rm_name': row['rm_name'],
                'created_date': row['created_date']
            })

    # Sort by date (newest first)
    statements.sort(key=lambda x: x['created_date'], reverse=True)

    return statements


def find_statement_file(run_id: str, extracted_dir: Path):
    """Find statement file in extracted directory"""
    matches = list(extracted_dir.glob(f"{run_id}.*"))
    return matches[0] if matches else None


def upload_statement(db, file_path: Path, run_id: str, provider_code: str):
    """
    Upload statement to database (parse and save)
    Returns: (success: bool, message: str)
    """
    try:
        # Check if already exists
        if crud.check_run_id_exists(db, run_id, provider_code):
            return False, "Already exists"

        # Get parser
        parser = get_parser(provider_code, str(file_path))

        # Parse file
        raw_statements, metadata = parser(str(file_path), run_id)

        # Enrich with mapper data
        metadata = enrich_metadata_with_mapper(metadata, run_id)

        # Save to database
        metadata_obj = crud.create(db, Metadata, metadata)
        crud.bulk_create_raw(db, provider_code, raw_statements)
        db.commit()

        return True, f"Uploaded {len(raw_statements)} transactions"

    except Exception as e:
        db.rollback()
        return False, f"Error: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description='Process all UATL statements (latest to oldest)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--upload-only', action='store_true', help='Upload only, no processing')
    parser.add_argument('--month', type=str, help='Filter by specific month (e.g., 2025-09)')
    args = parser.parse_args()

    # Validate paths
    if not MAPPER_CSV.exists():
        logger.error(f"❌ Mapper CSV not found: {MAPPER_CSV}")
        return 1

    if not EXTRACTED_DIR.exists():
        logger.error(f"❌ Extracted directory not found: {EXTRACTED_DIR}")
        return 1

    # Start
    start_time = datetime.now()
    logger.info(f"\n{'='*70}")
    if args.month:
        logger.info(f"PROCESS {args.month} UATL STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    else:
        logger.info(f"PROCESS ALL UATL STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"{'='*70}\n")

    # Read mapper
    logger.info("Reading mapper.csv...")
    statements = read_uatl_statements(MAPPER_CSV, target_month=args.month)

    if args.month:
        logger.info(f"Found {len(statements)} statements from {args.month} (sorted newest first)\n")
    else:
        logger.info(f"Found {len(statements)} UATL statements (sorted newest first)\n")
        if len(statements) > 0:
            logger.info(f"Date range: {statements[0]['created_date']} to {statements[-1]['created_date']}\n")

    if not statements:
        logger.warning("No statements found")
        return 0

    # Process statements
    db = SessionLocal()

    try:
        upload_success = 0
        upload_skip = 0
        upload_error = 0
        not_found = 0
        to_process = []

        logger.info("STEP 1: Uploading statements...\n")

        for idx, stmt in enumerate(statements, 1):
            run_id = stmt['run_id']
            logger.info(f"[{idx}/{len(statements)}] {run_id}")

            # Find file
            file_path = find_statement_file(run_id, EXTRACTED_DIR)
            if not file_path:
                logger.warning(f"  ❌ File not found")
                not_found += 1
                continue

            logger.info(f"  📄 {file_path.name}")

            # Check if already uploaded
            if crud.check_run_id_exists(db, run_id, PROVIDER_CODE):
                logger.info(f"  ⏭️  Already uploaded")
                upload_skip += 1

                # Check if needs processing
                if not crud.get_summary_by_run_id(db, run_id):
                    to_process.append(run_id)

                continue

            if args.dry_run:
                logger.info(f"  [DRY RUN] Would upload")
                continue

            # Upload
            success, message = upload_statement(db, file_path, run_id, PROVIDER_CODE)

            if success:
                logger.info(f"  ✅ {message}")
                upload_success += 1
                to_process.append(run_id)
            else:
                logger.error(f"  ❌ {message}")
                if "Already exists" in message:
                    upload_skip += 1
                else:
                    upload_error += 1

        # Upload summary
        logger.info(f"\n{'='*70}")
        logger.info(f"UPLOAD SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Total:         {len(statements)}")
        logger.info(f"✅ Uploaded:   {upload_success}")
        logger.info(f"⏭️  Skipped:    {upload_skip}")
        logger.info(f"❌ Not found:  {not_found}")
        logger.info(f"❌ Errors:     {upload_error}")
        logger.info(f"{'='*70}\n")

        # Process
        if args.upload_only:
            logger.info("Upload-only mode")
            return 0

        if not to_process:
            logger.info("No statements to process")
            return 0

        logger.info(f"STEP 2: Processing {len(to_process)} statements...\n")

        process_success = 0
        process_error = 0

        for idx, run_id in enumerate(to_process, 1):
            logger.info(f"[{idx}/{len(to_process)}] {run_id}")

            if args.dry_run:
                logger.info(f"  [DRY RUN] Would process")
                continue

            try:
                result = process_statement(db, run_id)

                if result.get('status') == 'success':
                    verification = result.get('verification_status', 'N/A')
                    balance = result.get('balance_match', 'N/A')
                    logger.info(f"  ✅ {verification} | {balance}")
                    process_success += 1
                else:
                    logger.error(f"  ❌ {result.get('message', 'Unknown error')}")
                    process_error += 1

            except Exception as e:
                logger.error(f"  ❌ {str(e)}")
                process_error += 1

        # Processing summary
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Total:         {len(to_process)}")
        logger.info(f"✅ Success:    {process_success}")
        logger.info(f"❌ Errors:     {process_error}")
        logger.info(f"{'='*70}\n")

    finally:
        db.close()

    # Done
    duration = datetime.now() - start_time
    logger.info(f"Duration: {duration}")
    logger.info(f"✅ Complete!\n")

    return 0


if __name__ == '__main__':
    exit(main())
