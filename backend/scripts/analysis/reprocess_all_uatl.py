#!/usr/bin/env python3
"""
Reprocess all UATL (Airtel) statements with implicit fee/commission detection
"""
import os
import sys
import time
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.processor import process_statement

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise - only show warnings/errors
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

def reprocess_all_uatl():
    """Reprocess all UATL statements with implicit fee detection"""

    # Create engine
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )
    Session = sessionmaker(bind=engine)

    # Get all UATL run_ids
    print("Fetching UATL statements...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT run_id FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            ORDER BY run_id
        """))
        run_ids = [row[0] for row in result]

    total = len(run_ids)
    print(f"Found {total} UATL statements to reprocess\n")

    # Statistics
    start_time = time.time()
    processed = 0
    success = 0
    errors = 0
    balance_success = 0
    balance_fail = 0

    uses_cashback_count = 0
    no_cashback_count = 0
    uses_ind02_count = 0
    no_ind02_count = 0

    # Process each statement
    for idx, run_id in enumerate(run_ids, 1):
        try:
            # Delete existing processed data
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM uatl_processed_statements WHERE run_id = :run_id"), {'run_id': run_id})
                conn.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {'run_id': run_id})
                conn.commit()

            # Reprocess
            db = Session()
            result = process_statement(db, run_id)
            db.close()

            # Get results
            with engine.connect() as conn:
                r = conn.execute(text("""
                    SELECT balance_match, uses_implicit_cashback, uses_implicit_ind02_commission
                    FROM summary WHERE run_id = :run_id
                """), {'run_id': run_id})
                row = r.fetchone()

                if row:
                    if row[0] == 'Success':
                        balance_success += 1
                    else:
                        balance_fail += 1

                    if row[1]:
                        uses_cashback_count += 1
                    else:
                        no_cashback_count += 1

                    if row[2]:
                        uses_ind02_count += 1
                    else:
                        no_ind02_count += 1

            success += 1
            processed += 1

            # Progress update every 100 statements
            if idx % 100 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                remaining = (total - idx) / rate if rate > 0 else 0
                eta_mins = remaining / 60

                print(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | "
                      f"Rate: {rate:.1f}/s | ETA: {eta_mins:.1f}m | "
                      f"Success: {success} | Errors: {errors}")
                print(f"  Cashback: {uses_cashback_count}Y/{no_cashback_count}N | "
                      f"IND02: {uses_ind02_count}Y/{no_ind02_count}N | "
                      f"Balance: {balance_success}✓/{balance_fail}✗")

        except Exception as e:
            errors += 1
            logger.error(f"Error processing {run_id}: {e}")
            if errors % 10 == 0:
                print(f"  WARNING: {errors} errors so far")

    # Final report
    elapsed = time.time() - start_time
    elapsed_mins = elapsed / 60

    print(f"\n{'='*80}")
    print(f"REPROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Total statements: {total}")
    print(f"Processed: {processed}")
    print(f"Successful: {success} ({success/total*100:.1f}%)")
    print(f"Errors: {errors} ({errors/total*100:.1f}%)")
    print(f"Time: {elapsed_mins:.1f} minutes ({processed/elapsed:.1f} statements/sec)")
    print()
    print(f"MERCHANT PAYMENT CASHBACK:")
    print(f"  Uses implicit cashback:   {uses_cashback_count} ({uses_cashback_count/success*100:.1f}%)")
    print(f"  No implicit cashback:     {no_cashback_count} ({no_cashback_count/success*100:.1f}%)")
    print()
    print(f"IND02 COMMISSION:")
    print(f"  Uses implicit commission: {uses_ind02_count} ({uses_ind02_count/success*100:.1f}%)")
    print(f"  No implicit commission:   {no_ind02_count} ({no_ind02_count/success*100:.1f}%)")
    print()
    print(f"BALANCE MATCH:")
    print(f"  Success: {balance_success} ({balance_success/success*100:.1f}%)")
    print(f"  Failed:  {balance_fail} ({balance_fail/success*100:.1f}%)")
    print(f"{'='*80}")

if __name__ == '__main__':
    reprocess_all_uatl()
