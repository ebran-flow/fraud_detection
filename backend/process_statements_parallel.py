#!/usr/bin/env python3
"""
Parallel Statement Processing Script
Processes raw_statements → processed_statements + summary in parallel

Usage:
    python process_statements_parallel.py --workers 8
    python process_statements_parallel.py --workers 16 --dry-run
    python process_statements_parallel.py --workers 4 --provider UATL
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, Manager
from functools import partial
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')
sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal
from app.services.processor import process_statement
from app.models.metadata import Metadata
from app.models.summary import Summary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_statements_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_unprocessed_run_ids(provider_code=None, force=False):
    """Get run_ids that need processing"""
    db = SessionLocal()
    try:
        query = db.query(Metadata.run_id, Metadata.acc_prvdr_code)

        if provider_code:
            query = query.filter(Metadata.acc_prvdr_code == provider_code)

        if not force:
            query = query.outerjoin(Summary, Metadata.run_id == Summary.run_id)
            query = query.filter(Summary.run_id == None)

        results = query.all()
        return [{'run_id': r.run_id, 'provider_code': r.acc_prvdr_code} for r in results]
    finally:
        db.close()


def process_single_run_id(run_info, dry_run=False):
    """Process a single run_id (worker function)"""
    run_id = run_info['run_id']
    provider_code = run_info['provider_code']

    try:
        if dry_run:
            return {'status': 'dry_run', 'run_id': run_id, 'provider_code': provider_code}

        db = SessionLocal()
        try:
            result = process_statement(db, run_id)
            return {
                'status': 'success',
                'run_id': run_id,
                'provider_code': provider_code,
                'processed_count': result.get('processed_count', 0),
                'duplicate_count': result.get('duplicate_count', 0),
                'quality_issues_count': result.get('quality_issues_count', 0),
                'balance_match': result.get('balance_match', 'Unknown'),
                'verification_status': result.get('verification_status', 'Unknown'),
            }
        except Exception as e:
            db.rollback()
            return {'status': 'error', 'run_id': run_id, 'provider_code': provider_code, 'message': str(e)}
        finally:
            db.close()
    except Exception as e:
        return {'status': 'error', 'run_id': run_id, 'provider_code': provider_code, 'message': str(e)}


def log_progress(result, counter, total, start_time):
    """Log progress for each completed statement"""
    counter['count'] += 1
    current = counter['count']
    status = result['status']
    
    elapsed = (datetime.now() - start_time).total_seconds()
    speed = current / elapsed if elapsed > 0 else 0
    eta_hours = ((total - current) / speed / 3600) if speed > 0 else 0

    counter[status] = counter.get(status, 0) + 1

    if status == 'success':
        counter['total_processed'] = counter.get('total_processed', 0) + result.get('processed_count', 0)
        counter['total_duplicates'] = counter.get('total_duplicates', 0) + result.get('duplicate_count', 0)
        counter['total_quality_issues'] = counter.get('total_quality_issues', 0) + result.get('quality_issues_count', 0)
        
        logger.info(
            f"[{current}/{total}] ✅ {result['provider_code']} {result['run_id']} - "
            f"{result['processed_count']} txns, {result['duplicate_count']} dups, "
            f"{result['quality_issues_count']} quality issues | "
            f"Speed: {speed:.2f}/s | ETA: {eta_hours:.1f}h"
        )
    elif status == 'error':
        logger.error(f"[{current}/{total}] ❌ {result['run_id']} - {result.get('message', 'Error')}")


def main():
    parser = argparse.ArgumentParser(description='Parallel statement processing')
    parser.add_argument('--workers', type=int, default=8, help='Number of workers (default: 8)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--provider', type=str, choices=['UATL', 'UMTN'], help='Filter by provider')
    parser.add_argument('--force', action='store_true', help='Reprocess all')
    args = parser.parse_args()

    if args.workers > 32:
        logger.warning(f"Limiting workers to 32 (requested: {args.workers})")
        args.workers = 32

    start_time = datetime.now()
    logger.info(f"\n{'='*80}")
    logger.info(f"PARALLEL STATEMENT PROCESSING - Workers: {args.workers}")
    logger.info(f"{'='*80}\n")

    logger.info("Loading unprocessed statements...")
    run_ids = get_unprocessed_run_ids(provider_code=args.provider, force=args.force)

    if not run_ids:
        logger.info("✅ No statements to process!")
        return 0

    logger.info(f"Found {len(run_ids)} statements to process\n")

    manager = Manager()
    counter = manager.dict()
    counter['count'] = 0
    counter['success'] = 0
    counter['error'] = 0
    counter['total_processed'] = 0
    counter['total_duplicates'] = 0
    counter['total_quality_issues'] = 0

    worker_func = partial(process_single_run_id, dry_run=args.dry_run)

    logger.info(f"Starting parallel processing...\n")

    with Pool(processes=args.workers) as pool:
        for result in pool.imap_unordered(worker_func, run_ids):
            log_progress(result, counter, len(run_ids), start_time)

    duration = datetime.now() - start_time
    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total statements: {len(run_ids)}")
    logger.info(f"✅ Success:        {counter.get('success', 0)}")
    logger.info(f"❌ Errors:         {counter.get('error', 0)}")
    logger.info(f"")
    logger.info(f"Total transactions processed: {counter.get('total_processed', 0):,}")
    logger.info(f"Total duplicates:             {counter.get('total_duplicates', 0):,}")
    logger.info(f"Total quality issues:         {counter.get('total_quality_issues', 0):,}")
    logger.info(f"{'='*80}")
    logger.info(f"Duration: {duration}")
    logger.info(f"Average: {len(run_ids) / duration.total_seconds():.2f} statements/s")
    logger.info(f"✅ Complete!\n")

    return 0


if __name__ == '__main__':
    exit(main())
