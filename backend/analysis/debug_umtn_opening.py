#!/usr/bin/env python3
"""
Debug UMTN Opening Balance Calculation
"""
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal
from app.services.balance_utils import calculate_opening_balance_mtn, apply_transaction_mtn


def main():
    """Debug opening balance calculation"""
    run_id = "66ec2b21c7585"

    db = SessionLocal()
    try:
        # Get first 5 transactions in order
        result = db.execute(text("""
            SELECT txn_date, txn_type, amount, fee, float_balance
            FROM umtn_raw_statements
            WHERE run_id = :run_id
            ORDER BY txn_date ASC, float_balance DESC
            LIMIT 10
        """), {"run_id": run_id})

        rows = result.fetchall()
        if not rows:
            print("No transactions found!")
            return

        # Get first transaction details
        first_txn = rows[0]
        first_balance = float(first_txn[4])
        first_amount = float(first_txn[2])
        first_fee = float(first_txn[3])
        first_txn_type = str(first_txn[1])

        print(f"\nFirst Transaction (with same-timestamp ordering):")
        print(f"  Date: {first_txn[0]}")
        print(f"  Type: {first_txn_type}")
        print(f"  Amount: {first_amount}")
        print(f"  Fee: {first_fee}")
        print(f"  Float Balance: {first_balance}")

        # Calculate opening balance using the function
        opening_balance = calculate_opening_balance_mtn(first_balance, first_amount, first_txn_type, first_fee)
        print(f"\nOpening Balance Calculated: {opening_balance}")

        # Now apply the first transaction and verify
        print(f"\n\nApplying Transactions (with same-timestamp ordering):")
        print(f"{'='*100}")
        running_balance = opening_balance
        print(f"Starting Balance (Opening): {running_balance}")

        for i, row in enumerate(rows, 1):
            txn_date = row[0]
            txn_type = str(row[1])
            amount = float(row[2])
            fee = float(row[3])
            stmt_balance = float(row[4])

            print(f"\nTransaction {i}: {txn_type} Amount={amount} Fee={fee}")
            print(f"  Before: {running_balance:.2f}")

            # Apply transaction
            running_balance = apply_transaction_mtn(running_balance, amount, txn_type, fee)

            print(f"  After:  {running_balance:.2f}")
            print(f"  Statement Balance: {stmt_balance:.2f}")
            print(f"  Difference: {running_balance - stmt_balance:.2f}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
