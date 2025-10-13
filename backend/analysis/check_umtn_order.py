#!/usr/bin/env python3
"""
Check UMTN Transaction Order
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal


def main():
    """Check transaction order"""
    run_id = "66ec2b21c7585"

    db = SessionLocal()
    try:
        # Get first 5 and last 5 transactions in chronological order
        print(f"\n{'='*70}")
        print(f"UMTN Transaction Order Analysis")
        print(f"Run ID: {run_id}")
        print(f"{'='*70}\n")

        # First 5 (oldest)
        print("FIRST 5 TRANSACTIONS (Oldest):")
        print("-" * 70)
        result = db.execute(text("""
            SELECT txn_date, txn_type, amount, float_balance, txn_id
            FROM umtn_raw_statements
            WHERE run_id = :run_id
            ORDER BY txn_date ASC
            LIMIT 5
        """), {"run_id": run_id})

        for i, row in enumerate(result.fetchall(), 1):
            print(f"{i}. Date: {row[0]}, Type: {row[1]}, Amount: {row[2]}, Float Balance: {row[3]}")

        # Last 5 (newest)
        print(f"\n\nLAST 5 TRANSACTIONS (Newest):")
        print("-" * 70)
        result = db.execute(text("""
            SELECT txn_date, txn_type, amount, float_balance, txn_id
            FROM umtn_raw_statements
            WHERE run_id = :run_id
            ORDER BY txn_date DESC
            LIMIT 5
        """), {"run_id": run_id})

        for i, row in enumerate(result.fetchall(), 1):
            print(f"{i}. Date: {row[0]}, Type: {row[1]}, Amount: {row[2]}, Float Balance: {row[3]}")

        # Count and date range
        print(f"\n\nSUMMARY:")
        print("-" * 70)
        result = db.execute(text("""
            SELECT
                COUNT(*) as total,
                MIN(txn_date) as first_date,
                MAX(txn_date) as last_date,
                (SELECT float_balance FROM umtn_raw_statements WHERE run_id = :run_id ORDER BY txn_date ASC LIMIT 1) as first_balance,
                (SELECT float_balance FROM umtn_raw_statements WHERE run_id = :run_id ORDER BY txn_date DESC LIMIT 1) as last_balance
            FROM umtn_raw_statements
            WHERE run_id = :run_id
        """), {"run_id": run_id})

        row = result.fetchone()
        print(f"Total Transactions: {row[0]}")
        print(f"Date Range: {row[1]} to {row[2]}")
        print(f"First Balance (oldest): {row[3]}")
        print(f"Last Balance (newest): {row[4]}")
        print(f"Balance Change: {float(row[4]) - float(row[3])}")

        print(f"\n{'='*70}\n")

    finally:
        db.close()


if __name__ == '__main__':
    main()
