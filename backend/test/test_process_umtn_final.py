#!/usr/bin/env python3
"""
Test script to process UMTN statements with ADJUSTMENT and LOAN_REPAYMENT transactions
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.processor import process_statement
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "mysql+pymysql://root:password@127.0.0.1:3307/fraud_detection"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Statements with special transactions from different months
TEST_RUN_IDS = [
    '657dd50270b2f',  # 2023-09: 2 ADJUSTMENT
    '65805b3eb5340',  # 2023-09: 1 ADJUSTMENT (already processed successfully!)
    '660e6066b1dab',  # 2024-01: 1 ADJUSTMENT
    '663a1921d7189',  # 2024-02: 1 ADJUSTMENT
    '665f0c8a236e3',  # 2024-03: 1 ADJUSTMENT
    '674d664b7aaaf',  # 2024-09: 1 ADJUSTMENT
    '679d7badbc313',  # 2024-10: 1 ADJUSTMENT
    '679e346a28a3d',  # 2024-11: 1 ADJUSTMENT
    '681475d42984a',  # 2025-02: 1 ADJUSTMENT
    '684008c412cf6',  # 2025-03: 1 ADJUSTMENT + 2 LOAN_REPAYMENT (our known case!)
    '6863b346144ea',  # 2025-04: 1 ADJUSTMENT + 16 LOAN_REPAYMENT
    '68639937f2428',  # 2025-04: 20 LOAN_REPAYMENT
    '688c846e2c646',  # 2025-05: 5 LOAN_REPAYMENT (our known case!)
    '68b6a8d69dadd',  # 2025-06: 22 LOAN_REPAYMENT
]

def main():
    """Process test statements"""
    db = SessionLocal()

    results = []
    for run_id in TEST_RUN_IDS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {run_id}")
        logger.info(f"{'='*60}")

        try:
            result = process_statement(db, run_id)
            results.append(result)

            logger.info(f"✓ Success: {result['run_id']}")
            logger.info(f"  - Processed: {result['processed_count']} transactions")
            logger.info(f"  - Duplicates: {result['duplicate_count']}")
            logger.info(f"  - Balance match: {result['balance_match']}")
            logger.info(f"  - Verification: {result['verification_status']}")

        except Exception as e:
            logger.error(f"✗ Failed: {run_id} - {e}")
            import traceback
            logger.error(traceback.format_exc())
            results.append({'run_id': run_id, 'status': 'error', 'error': str(e)})

    db.close()

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")

    successful = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') != 'success']

    logger.info(f"Total processed: {len(TEST_RUN_IDS)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")

    if successful:
        balance_matched = [r for r in successful if r.get('balance_match') == 'Success']
        verified_pass = [r for r in successful if r.get('verification_status') == 'PASS']
        logger.info(f"Balance matched: {len(balance_matched)}/{len(successful)}")
        logger.info(f"Verification PASS: {len(verified_pass)}/{len(successful)}")

    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
