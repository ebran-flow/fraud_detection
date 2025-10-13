#!/usr/bin/env python3
"""
Test UMTN Processing
Tests processing UMTN statements (duplicate detection, balance calculation, etc.)
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal
from app.services.processor import process_statement
from sqlalchemy import text


def main():
    """Test processing a UMTN statement"""
    # Use the run_id we imported earlier
    run_id = "66ec2b21c7585"

    print(f"\n{'='*70}")
    print(f"Testing UMTN Processing")
    print(f"{'='*70}")
    print(f"Run ID: {run_id}")
    print(f"{'='*70}\n")

    db = SessionLocal()
    try:
        # Check if already processed
        result = db.execute(text("SELECT COUNT(*) FROM umtn_processed_statements WHERE run_id = :run_id"), {"run_id": run_id})
        proc_count = result.scalar()

        if proc_count > 0:
            print(f"⚠️  Statement already processed ({proc_count} records), re-processing...")
            # Delete existing processed records
            print("Deleting existing processed records...")
            db.execute(text("DELETE FROM umtn_processed_statements WHERE run_id = :run_id"), {"run_id": run_id})
            db.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {"run_id": run_id})
            db.commit()

        # Process statement
        print("\n1. Processing statement...")
        result = process_statement(db, run_id)

        print(f"   ✅ Processing complete")
        print(f"   - Provider: {result['provider_code']}")
        print(f"   - Processed: {result['processed_count']} transactions")
        print(f"   - Duplicates: {result['duplicate_count']}")
        print(f"   - Balance Match: {result['balance_match']}")
        print(f"   - Verification Status: {result['verification_status']}")

        # Verify processed data
        print(f"\n2. Verifying processed data...")
        result = db.execute(text("SELECT COUNT(*) FROM umtn_processed_statements WHERE run_id = :run_id"), {"run_id": run_id})
        proc_count = result.scalar()
        print(f"   - Processed statements: {proc_count}")

        result = db.execute(text("SELECT COUNT(*) FROM summary WHERE run_id = :run_id"), {"run_id": run_id})
        summary_count = result.scalar()
        print(f"   - Summary records: {summary_count}")

        # Show summary details
        print(f"\n3. Summary Details...")
        result = db.execute(text("""
            SELECT
                balance_match,
                verification_status,
                verification_reason,
                first_balance,
                last_balance,
                calculated_closing_balance,
                credits,
                debits,
                fees,
                duplicate_count,
                missing_days_detected,
                gap_related_balance_changes,
                balance_diff_changes
            FROM summary
            WHERE run_id = :run_id
        """), {"run_id": run_id})

        summary = result.fetchone()
        if summary:
            print(f"   - Balance Match: {summary[0]}")
            print(f"   - Verification: {summary[1]}")
            print(f"   - Reason: {summary[2]}")
            print(f"   - First Balance: {summary[3]}")
            print(f"   - Last Balance: {summary[4]}")
            print(f"   - Calculated Closing: {summary[5]}")
            print(f"   - Total Credits: {summary[6]}")
            print(f"   - Total Debits: {summary[7]}")
            print(f"   - Total Fees: {summary[8]}")
            print(f"   - Duplicates: {summary[9]}")
            print(f"   - Missing Days: {'Yes' if summary[10] else 'No'}")
            print(f"   - Gap-Related Balance Changes: {summary[11]}")
            print(f"   - Total Balance Diff Changes: {summary[12]}")

        # Show sample processed transactions
        print(f"\n4. Sample Processed Transactions (first 5)...")
        result = db.execute(text("""
            SELECT
                txn_date,
                txn_type,
                amount,
                float_balance as balance,
                calculated_running_balance,
                balance_diff,
                is_duplicate,
                is_special_txn
            FROM umtn_processed_statements
            WHERE run_id = :run_id
            ORDER BY txn_date DESC
            LIMIT 5
        """), {"run_id": run_id})

        rows = result.fetchall()
        for i, row in enumerate(rows, 1):
            print(f"\n   Transaction {i}:")
            print(f"      Date: {row[0]}")
            print(f"      Type: {row[1]}")
            print(f"      Amount: {row[2]}")
            print(f"      Statement Balance: {row[3]}")
            print(f"      Calculated Balance: {row[4]}")
            print(f"      Balance Diff: {row[5]}")
            print(f"      Duplicate: {row[6]}")
            print(f"      Special: {row[7]}")

        print(f"\n✅ Processing test complete!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
