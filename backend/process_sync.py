#!/usr/bin/env python3
"""
Synchronous Processing for UATL and UMTN Statements

Processes statements one by one (no parallel processing).
Useful for debugging and seeing detailed error messages immediately.

Usage:
    python process_sync.py --provider UMTN                           # Process all UMTN
    python process_sync.py --provider UATL --dry-run                 # Preview UATL
    python process_sync.py --provider UMTN --month 2023-10           # Specific month
    python process_sync.py --provider UATL --limit 10                # Process only first 10
    python process_sync.py --provider UATL --run-id 6800f84e92d22    # Process specific run_id
"""

import sys
import csv
import argparse
import logging
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).parent / '.env')

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal
from app.services import crud_v2 as crud
from app.services.parsers import get_parser
from app.services.mapper import enrich_metadata_with_mapper
from app.models.metadata import Metadata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths (relative to backend folder)
BACKEND_DIR = Path(__file__).parent
MAPPER_CSV = BACKEND_DIR / "docs" / "data" / "statements" / "mapper.csv"


def read_statements(mapper_csv: Path, provider_code: str, target_month: str = None, run_id_filter: str = None):
    """
    Read mapper.csv and filter statements by provider
    Sorts by date (newest first)

    Args:
        mapper_csv: Path to mapper.csv
        provider_code: Provider code to filter (UATL or UMTN)
        target_month: Optional filter for specific month (e.g., "2025-09")
        run_id_filter: Optional filter for specific run_id
    """
    statements = []

    with open(mapper_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter for specific run_id if provided
            if run_id_filter and row['run_id'] != run_id_filter:
                continue

            # Filter for provider and successful status
            if not (row['acc_prvdr_code'] == provider_code and row['lambda_status'] == 'score_calc_success'):
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


def process_single_statement(statement_info, db, provider_code, extracted_dir, dry_run=False):
    """
    Process a single statement
    Returns: dict with status and details
    """
    run_id = statement_info['run_id']

    try:
        # Check if already exists
        if crud.check_run_id_exists(db, run_id, provider_code):
            return {
                'status': 'skipped',
                'run_id': run_id,
                'message': 'Already uploaded'
            }

        # Find file
        file_path = find_statement_file(run_id, extracted_dir)
        if not file_path:
            return {
                'status': 'not_found',
                'run_id': run_id,
                'message': 'File not found'
            }

        if dry_run:
            return {
                'status': 'dry_run',
                'run_id': run_id,
                'message': f'Would upload {file_path.name}'
            }

        # Get parser
        parser = get_parser(provider_code, str(file_path))

        # Parse file
        logger.info(f"Parsing {file_path}")
        raw_statements, metadata = parser(str(file_path), run_id)

        # Enrich with mapper data
        metadata = enrich_metadata_with_mapper(metadata, run_id)

        # Save to database
        metadata_obj = crud.create(db, Metadata, metadata)
        crud.bulk_create_raw(db, provider_code, raw_statements)
        db.commit()

        return {
            'status': 'success',
            'run_id': run_id,
            'message': f'Uploaded {len(raw_statements)} transactions',
            'count': len(raw_statements)
        }

    except Exception as e:
        db.rollback()
        logger.exception(f"Error processing {run_id}")
        return {
            'status': 'error',
            'run_id': run_id,
            'message': f'Error: {str(e)}'
        }


def main():
    parser = argparse.ArgumentParser(description='Synchronous processing for UATL and UMTN statements')
    parser.add_argument('--provider', type=str, required=True, choices=['UATL', 'UMTN'],
                        help='Provider code (UATL or UMTN)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--month', type=str, help='Filter by specific month (e.g., 2025-09 or 2023-10)')
    parser.add_argument('--limit', type=int, help='Limit number of statements to process')
    parser.add_argument('--run-id', type=str, help='Process specific run_id only')
    args = parser.parse_args()

    # Set paths based on provider
    provider_code = args.provider
    extracted_dir = BACKEND_DIR / "docs" / "data" / provider_code / "extracted"

    # Validate paths
    if not MAPPER_CSV.exists():
        logger.error(f"❌ Mapper CSV not found: {MAPPER_CSV}")
        return 1

    if not extracted_dir.exists():
        logger.error(f"❌ Extracted directory not found: {extracted_dir}")
        return 1

    # Start
    start_time = datetime.now()
    logger.info(f"\n{'='*70}")
    if args.run_id:
        logger.info(f"SYNCHRONOUS PROCESS {provider_code} STATEMENT: {args.run_id} - {'DRY RUN' if args.dry_run else 'LIVE'}")
    elif args.month:
        logger.info(f"SYNCHRONOUS PROCESS {args.month} {provider_code} STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    else:
        logger.info(f"SYNCHRONOUS PROCESS ALL {provider_code} STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"{'='*70}\n")

    # Read mapper
    logger.info("Reading mapper.csv...")
    statements = read_statements(MAPPER_CSV, provider_code, target_month=args.month, run_id_filter=args.run_id)

    if args.month:
        logger.info(f"Found {len(statements)} {provider_code} statements from {args.month}\n")
    elif args.run_id:
        logger.info(f"Found {len(statements)} statement(s) matching run_id: {args.run_id}\n")
    else:
        logger.info(f"Found {len(statements)} {provider_code} statements\n")
        if len(statements) > 0:
            logger.info(f"Date range: {statements[0]['created_date']} to {statements[-1]['created_date']}\n")

    if not statements:
        logger.warning("No statements found")
        return 0

    # Pre-load existing run_ids to skip already imported statements
    # (but skip this check if user specified a specific run_id)
    if not args.run_id:
        logger.info("Checking for existing run_ids in database...")
        db = SessionLocal()
        try:
            existing_run_ids = set(crud.get_all_run_ids(db, provider_code))
            logger.info(f"Found {len(existing_run_ids)} existing run_ids in database\n")
        finally:
            db.close()

        # Filter out already uploaded statements
        statements_to_process = [s for s in statements if s['run_id'] not in existing_run_ids]
        already_uploaded = len(statements) - len(statements_to_process)

        logger.info(f"Already uploaded: {already_uploaded}")
        logger.info(f"To process: {len(statements_to_process)}\n")

        if not statements_to_process:
            logger.info("No new statements to process")
            return 0
    else:
        # User specified a run_id, process it even if it exists
        statements_to_process = statements
        already_uploaded = 0
        logger.info("Processing specific run_id (will overwrite if exists)\n")

    # Apply limit if specified (after filtering)
    if args.limit:
        statements_to_process = statements_to_process[:args.limit]
        logger.info(f"Limited to first {args.limit} statements\n")

    # Create database session for processing
    db = SessionLocal()

    try:
        # Counters
        counter = {
            'count': 0,
            'success': 0,
            'skipped': 0,
            'error': 0,
            'not_found': 0,
            'dry_run': 0
        }

        # Process statements one by one
        total = len(statements_to_process)
        for i, statement_info in enumerate(statements_to_process, 1):
            run_id = statement_info['run_id']

            logger.info(f"\n{'='*70}")
            logger.info(f"[{i}/{total}] Processing: {run_id}")
            logger.info(f"{'='*70}")

            result = process_single_statement(statement_info, db, provider_code, extracted_dir, args.dry_run)

            counter['count'] += 1
            status = result['status']
            counter[status] = counter.get(status, 0) + 1

            # Log result
            if status == 'success':
                logger.info(f"[{i}/{total}] ✅ {run_id} - {result['message']}")
            elif status == 'skipped':
                logger.info(f"[{i}/{total}] ⏭️  {run_id} - {result['message']}")
            elif status == 'not_found':
                logger.warning(f"[{i}/{total}] ❌ {run_id} - File not found")
            elif status == 'error':
                logger.error(f"[{i}/{total}] ❌ {run_id} - {result['message']}")
            elif status == 'dry_run':
                logger.info(f"[{i}/{total}] [DRY RUN] {run_id} - {result['message']}")

            # Calculate and display progress
            elapsed = (datetime.now() - start_time).total_seconds()
            speed = counter['count'] / elapsed if elapsed > 0 else 0
            remaining = total - counter['count']
            eta_seconds = remaining / speed if speed > 0 else 0
            eta_minutes = eta_seconds / 60

            logger.info(f"Progress: {counter['count']}/{total} | Speed: {speed:.2f}/s | ETA: {eta_minutes:.1f}m")

    finally:
        db.close()

    # Summary
    duration = datetime.now() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY - {provider_code}")
    logger.info(f"{'='*70}")
    logger.info(f"Total statements:  {len(statements)}")
    logger.info(f"Already uploaded:  {already_uploaded}")
    logger.info(f"Processed:         {counter['count']}")
    logger.info(f"✅ Success:        {counter.get('success', 0)}")
    logger.info(f"⏭️  Skipped:        {counter.get('skipped', 0)}")
    logger.info(f"❌ Not found:      {counter.get('not_found', 0)}")
    logger.info(f"❌ Errors:         {counter.get('error', 0)}")
    if args.dry_run:
        logger.info(f"🔍 Dry run:        {counter.get('dry_run', 0)}")
    logger.info(f"{'='*70}")
    logger.info(f"Duration: {duration}")
    if duration.total_seconds() > 0 and counter['count'] > 0:
        logger.info(f"Average speed: {counter['count'] / duration.total_seconds():.2f} statements/second")
    logger.info(f"✅ Complete!\n")

    return 0


if __name__ == '__main__':
    exit(main())
