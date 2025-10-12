#!/usr/bin/env python3
"""
Parallel Import for Airtel (UMTN) Statements

Imports multiple airtel statements in parallel using multiprocessing.
Handles upload phase (parse + save to raw_statements + metadata).

Usage:
    python import_airtel_parallel.py --workers 8              # 8 parallel workers
    python import_airtel_parallel.py --workers 12 --dry-run   # Preview with 12 workers
    python import_airtel_parallel.py --workers 8 --month 2025-10  # Specific month
"""

import sys
import csv
import argparse
import logging
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, Manager, cpu_count
from functools import partial
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
        logging.FileHandler('import_airtel_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths (relative to backend folder)
BACKEND_DIR = Path(__file__).parent
MAPPER_CSV = BACKEND_DIR / "docs" / "data" / "statements" / "mapper.csv"
EXTRACTED_DIR = BACKEND_DIR / "docs" / "data" / "UMTN" / "extracted"
PROVIDER_CODE = "UMTN"


def read_airtel_statements(mapper_csv: Path, target_month: str = None):
    """
    Read mapper.csv and filter Airtel (UMTN) statements
    Sorts by date (newest first)

    Args:
        mapper_csv: Path to mapper.csv
        target_month: Optional filter for specific month (e.g., "2025-09")
    """
    statements = []

    with open(mapper_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter for UMTN (Airtel)
            if row['acc_prvdr_code'] != 'UMTN':
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


def process_single_statement(statement_info, existing_run_ids, dry_run=False):
    """
    Process a single statement (worker function)
    Returns: dict with status and details
    """
    run_id = statement_info['run_id']

    try:
        # Check if already exists (from pre-loaded set)
        if run_id in existing_run_ids:
            return {
                'status': 'skipped',
                'run_id': run_id,
                'message': 'Already imported'
            }

        # Find file
        file_path = find_statement_file(run_id, EXTRACTED_DIR)
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
                'message': f'Would import {file_path.name}'
            }

        # Create own database session
        db = SessionLocal()

        try:
            # Double-check in DB (in case another worker just added it)
            if crud.check_run_id_exists(db, run_id, PROVIDER_CODE):
                return {
                    'status': 'skipped',
                    'run_id': run_id,
                    'message': 'Already imported (race condition)'
                }

            # Get parser
            parser = get_parser(PROVIDER_CODE, str(file_path))

            # Parse file
            raw_statements, metadata = parser(str(file_path), run_id)

            # Enrich with mapper data
            metadata = enrich_metadata_with_mapper(metadata, run_id)

            # Save to database
            metadata_obj = crud.create(db, Metadata, metadata)
            crud.bulk_create_raw(db, PROVIDER_CODE, raw_statements)
            db.commit()

            return {
                'status': 'success',
                'run_id': run_id,
                'message': f'Imported {len(raw_statements)} transactions',
                'count': len(raw_statements)
            }

        except Exception as e:
            db.rollback()
            return {
                'status': 'error',
                'run_id': run_id,
                'message': f'Error: {str(e)}'
            }
        finally:
            db.close()

    except Exception as e:
        return {
            'status': 'error',
            'run_id': run_id,
            'message': f'Outer error: {str(e)}'
        }


def log_progress(result, counter, total, start_time):
    """Log progress for each completed statement"""
    counter['count'] += 1
    current = counter['count']

    status = result['status']
    run_id = result['run_id']
    message = result.get('message', '')

    # Calculate speed
    elapsed = (datetime.now() - start_time).total_seconds()
    speed = current / elapsed if elapsed > 0 else 0
    remaining = total - current
    eta_seconds = remaining / speed if speed > 0 else 0
    eta_hours = eta_seconds / 3600

    # Track by status
    counter[status] = counter.get(status, 0) + 1

    # Log based on status
    if status == 'success':
        logger.info(f"[{current}/{total}] ✅ {run_id} - {message} | Speed: {speed:.2f}/s | ETA: {eta_hours:.1f}h")
    elif status == 'skipped':
        if current % 10 == 0:  # Only log every 10th skip
            logger.info(f"[{current}/{total}] ⏭️  {run_id} - {message}")
    elif status == 'not_found':
        logger.warning(f"[{current}/{total}] ❌ {run_id} - File not found")
    elif status == 'error':
        logger.error(f"[{current}/{total}] ❌ {run_id} - {message}")
    elif status == 'dry_run':
        if current % 10 == 0:
            logger.info(f"[{current}/{total}] [DRY RUN] {run_id}")


def main():
    parser = argparse.ArgumentParser(description='Parallel import for Airtel (UMTN) statements')
    parser.add_argument('--workers', type=int, default=6, help='Number of parallel workers (default: 6, max: 12)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--month', type=str, help='Filter by specific month (e.g., 2025-09)')
    args = parser.parse_args()

    # Validate paths
    if not MAPPER_CSV.exists():
        logger.error(f"❌ Mapper CSV not found: {MAPPER_CSV}")
        return 1

    if not EXTRACTED_DIR.exists():
        logger.error(f"❌ Extracted directory not found: {EXTRACTED_DIR}")
        return 1

    # Validate workers (optimized for direct DB access)
    max_workers = 12  # Safe limit for direct DB access
    if args.workers > max_workers:
        logger.warning(f"⚠️  Requested {args.workers} workers, limiting to {max_workers}")
        args.workers = max_workers

    # Start
    start_time = datetime.now()
    logger.info(f"\n{'='*70}")
    if args.month:
        logger.info(f"PARALLEL IMPORT {args.month} AIRTEL STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    else:
        logger.info(f"PARALLEL IMPORT ALL AIRTEL STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"{'='*70}\n")

    # Read mapper
    logger.info("Reading mapper.csv...")
    statements = read_airtel_statements(MAPPER_CSV, target_month=args.month)

    if args.month:
        logger.info(f"Found {len(statements)} Airtel statements from {args.month}\n")
    else:
        logger.info(f"Found {len(statements)} Airtel statements\n")
        if len(statements) > 0:
            logger.info(f"Date range: {statements[0]['created_date']} to {statements[-1]['created_date']}\n")

    if not statements:
        logger.warning("No statements found")
        return 0

    # Pre-load existing run_ids to avoid repeated DB queries
    logger.info("Pre-loading existing run_ids from database...")
    db = SessionLocal()
    try:
        # Get all existing UMTN run_ids
        existing_run_ids = set(crud.get_all_run_ids(db, PROVIDER_CODE))
        logger.info(f"Found {len(existing_run_ids)} existing run_ids in database\n")
    finally:
        db.close()

    # Filter out already imported statements
    statements_to_process = [s for s in statements if s['run_id'] not in existing_run_ids]
    already_imported = len(statements) - len(statements_to_process)

    logger.info(f"Already imported: {already_imported}")
    logger.info(f"To process: {len(statements_to_process)}\n")

    if not statements_to_process:
        logger.info("No new statements to import")
        return 0

    # Setup progress tracking
    manager = Manager()
    counter = manager.dict()
    counter['count'] = 0
    counter['success'] = 0
    counter['skipped'] = 0
    counter['error'] = 0
    counter['not_found'] = 0

    # Create worker function with fixed parameters
    worker_func = partial(
        process_single_statement,
        existing_run_ids=existing_run_ids,
        dry_run=args.dry_run
    )

    # Process in parallel
    logger.info(f"Starting parallel import with {args.workers} workers...\n")

    with Pool(processes=args.workers) as pool:
        for result in pool.imap_unordered(worker_func, statements_to_process):
            log_progress(result, counter, len(statements_to_process), start_time)

    # Summary
    duration = datetime.now() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total statements: {len(statements)}")
    logger.info(f"Already imported:  {already_imported}")
    logger.info(f"Processed:         {len(statements_to_process)}")
    logger.info(f"✅ Success:        {counter.get('success', 0)}")
    logger.info(f"⏭️  Skipped:        {counter.get('skipped', 0)}")
    logger.info(f"❌ Not found:      {counter.get('not_found', 0)}")
    logger.info(f"❌ Errors:         {counter.get('error', 0)}")
    logger.info(f"{'='*70}")
    logger.info(f"Duration: {duration}")
    if len(statements_to_process) > 0:
        logger.info(f"Average speed: {len(statements_to_process) / duration.total_seconds():.2f} statements/second")
    logger.info(f"✅ Complete!\n")

    return 0


if __name__ == '__main__':
    exit(main())
