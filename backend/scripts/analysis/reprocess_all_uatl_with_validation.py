#!/usr/bin/env python3
"""
Reprocess all UATL statements with validation
Tracks improvements vs degradations in balance matching
"""
import os
import sys
import time
import json
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
    level=logging.WARNING,
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

# Create degradations log file
DEGRADATIONS_LOG = '/tmp/uatl_reprocessing_degradations.jsonl'

def save_old_summary(conn, run_id):
    """Save old summary data before reprocessing"""
    result = conn.execute(text("""
        SELECT balance_match, balance_diff_changes, balance_diff_change_ratio,
               calculated_closing_balance, last_balance
        FROM summary WHERE run_id = :run_id
    """), {'run_id': run_id})

    row = result.fetchone()
    if not row:
        return None

    return {
        'balance_match': row[0],
        'balance_diff_changes': row[1],
        'balance_diff_change_ratio': float(row[2]) if row[2] else 0.0,
        'calculated_closing': float(row[3]) if row[3] else 0.0,
        'stated_closing': float(row[4]) if row[4] else 0.0
    }

def get_new_summary(conn, run_id):
    """Get new summary data after reprocessing"""
    result = conn.execute(text("""
        SELECT balance_match, balance_diff_changes, balance_diff_change_ratio,
               calculated_closing_balance, last_balance,
               uses_implicit_cashback, uses_implicit_ind02_commission
        FROM summary WHERE run_id = :run_id
    """), {'run_id': run_id})

    row = result.fetchone()
    if not row:
        return None

    return {
        'balance_match': row[0],
        'balance_diff_changes': row[1],
        'balance_diff_change_ratio': float(row[2]) if row[2] else 0.0,
        'calculated_closing': float(row[3]) if row[3] else 0.0,
        'stated_closing': float(row[4]) if row[4] else 0.0,
        'uses_implicit_cashback': bool(row[5]),
        'uses_implicit_ind02_commission': bool(row[6])
    }

def compare_results(run_id, old, new):
    """Compare old vs new and categorize"""
    if not old:
        return 'NEW'  # No old data

    # Check for degradation
    degraded = False
    reasons = []

    # Balance match degradation
    if old['balance_match'] == 'Success' and new['balance_match'] == 'Failed':
        degraded = True
        reasons.append('balance_match degraded from Success to Failed')

    # Balance diff changes increased
    if new['balance_diff_changes'] > old['balance_diff_changes']:
        degraded = True
        diff_increase = new['balance_diff_changes'] - old['balance_diff_changes']
        reasons.append(f'balance_diff_changes increased by {diff_increase}')

    # Check for improvement
    improved = False
    improvements = []

    # Balance match improved
    if old['balance_match'] == 'Failed' and new['balance_match'] == 'Success':
        improved = True
        improvements.append('balance_match improved from Failed to Success')

    # Balance diff changes decreased
    if new['balance_diff_changes'] < old['balance_diff_changes']:
        improved = True
        diff_decrease = old['balance_diff_changes'] - new['balance_diff_changes']
        improvements.append(f'balance_diff_changes decreased by {diff_decrease}')

    if degraded:
        # Log degradation
        with open(DEGRADATIONS_LOG, 'a') as f:
            log_entry = {
                'run_id': run_id,
                'type': 'DEGRADATION',
                'reasons': reasons,
                'old': old,
                'new': new
            }
            f.write(json.dumps(log_entry) + '\n')
        return 'DEGRADED'
    elif improved:
        return 'IMPROVED'
    else:
        return 'UNCHANGED'

def reprocess_all_uatl_with_validation():
    """Reprocess all UATL statements with validation"""

    # Create engine
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )
    Session = sessionmaker(bind=engine)

    # Clear degradations log
    with open(DEGRADATIONS_LOG, 'w') as f:
        pass

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

    improved_count = 0
    degraded_count = 0
    unchanged_count = 0
    new_count = 0

    balance_success_count = 0
    balance_fail_count = 0
    uses_cashback_count = 0
    no_cashback_count = 0
    uses_ind02_count = 0
    no_ind02_count = 0

    # Process each statement
    for idx, run_id in enumerate(run_ids, 1):
        try:
            # Save old summary
            with engine.connect() as conn:
                old_summary = save_old_summary(conn, run_id)

            # Delete existing processed data
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM uatl_processed_statements WHERE run_id = :run_id"), {'run_id': run_id})
                conn.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {'run_id': run_id})
                conn.commit()

            # Reprocess
            db = Session()
            result = process_statement(db, run_id)
            db.close()

            # Get new summary
            with engine.connect() as conn:
                new_summary = get_new_summary(conn, run_id)

            # Compare
            comparison = compare_results(run_id, old_summary, new_summary)

            if comparison == 'IMPROVED':
                improved_count += 1
            elif comparison == 'DEGRADED':
                degraded_count += 1
            elif comparison == 'UNCHANGED':
                unchanged_count += 1
            else:  # NEW
                new_count += 1

            # Track new results
            if new_summary:
                if new_summary['balance_match'] == 'Success':
                    balance_success_count += 1
                else:
                    balance_fail_count += 1

                if new_summary['uses_implicit_cashback']:
                    uses_cashback_count += 1
                else:
                    no_cashback_count += 1

                if new_summary['uses_implicit_ind02_commission']:
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

                print(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Rate: {rate:.1f}/s | ETA: {eta_mins:.1f}m")
                print(f"  Changes: {improved_count}↑ {degraded_count}↓ {unchanged_count}= {new_count}NEW")
                print(f"  Balance: {balance_success_count}✓/{balance_fail_count}✗ | "
                      f"Cashback: {uses_cashback_count}Y/{no_cashback_count}N | "
                      f"IND02: {uses_ind02_count}Y/{no_ind02_count}N")
                if degraded_count > 0:
                    print(f"  ⚠️  WARNING: {degraded_count} degradations detected! Check {DEGRADATIONS_LOG}")

        except Exception as e:
            errors += 1
            logger.error(f"Error processing {run_id}: {e}")

    # Final report
    elapsed = time.time() - start_time
    elapsed_mins = elapsed / 60

    print(f"\n{'='*80}")
    print(f"REPROCESSING COMPLETE WITH VALIDATION")
    print(f"{'='*80}")
    print(f"Total statements: {total}")
    print(f"Processed: {processed}")
    print(f"Successful: {success} ({success/total*100:.1f}%)")
    print(f"Errors: {errors}")
    print(f"Time: {elapsed_mins:.1f} minutes ({processed/elapsed:.1f} statements/sec)")
    print()
    print(f"CHANGE ANALYSIS:")
    print(f"  Improved:   {improved_count} ({improved_count/success*100:.1f}%) ↑")
    print(f"  Degraded:   {degraded_count} ({degraded_count/success*100:.1f}%) ↓")
    print(f"  Unchanged:  {unchanged_count} ({unchanged_count/success*100:.1f}%) =")
    print(f"  New:        {new_count}")
    print()
    print(f"BALANCE MATCH:")
    print(f"  Success: {balance_success_count} ({balance_success_count/success*100:.1f}%)")
    print(f"  Failed:  {balance_fail_count} ({balance_fail_count/success*100:.1f}%)")
    print()
    print(f"DETECTION RESULTS:")
    print(f"  Merchant Payment Cashback (4%):")
    print(f"    Uses:    {uses_cashback_count} ({uses_cashback_count/success*100:.1f}%)")
    print(f"    Doesn't: {no_cashback_count} ({no_cashback_count/success*100:.1f}%)")
    print(f"  IND02 Commission (0.5%):")
    print(f"    Uses:    {uses_ind02_count} ({uses_ind02_count/success*100:.1f}%)")
    print(f"    Doesn't: {no_ind02_count} ({no_ind02_count/success*100:.1f}%)")
    print()
    if degraded_count > 0:
        print(f"⚠️  DEGRADATIONS LOG: {DEGRADATIONS_LOG}")
        print(f"   Review {degraded_count} degraded statements to understand why")
    print(f"{'='*80}")

if __name__ == '__main__':
    reprocess_all_uatl_with_validation()
