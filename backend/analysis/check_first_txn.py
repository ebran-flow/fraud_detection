#!/usr/bin/env python3
"""
Check First Transaction in Database
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal


def main():
    """Check first transaction"""
    run_id = "66ec2b21c7585"

    db = SessionLocal()
    try:
        # Get first transaction (oldest)
        result = db.execute(text("""
            SELECT txn_date, txn_type, amount, float_balance, description
            FROM umtn_raw_statements
            WHERE run_id = :run_id
            ORDER BY txn_date ASC
            LIMIT 1
        """), {"run_id": run_id})

        row = result.fetchone()
        if row:
            print(f"\nFirst Transaction (oldest):")
            print(f"  Date: {row[0]}")
            print(f"  Type: {row[1]}")
            print(f"  Amount: {row[2]}")
            print(f"  Float Balance: {row[3]}")
            print(f"  Description: {row[4]}")

            # Calculate what opening balance should be
            txn_type = row[1]
            amount = float(row[2])
            float_balance = float(row[3])

            if txn_type == 'CASH_OUT':
                # Balance increases with CASH_OUT, so: Opening = Balance - amount
                opening = float_balance - amount
                print(f"\n  Logic: CASH_OUT increases balance")
                print(f"  Opening Balance = {float_balance} - {amount} = {opening}")
            elif txn_type == 'CASH_IN':
                # Balance decreases with CASH_IN, so: Opening = Balance + amount
                opening = float_balance + amount
                print(f"\n  Logic: CASH_IN decreases balance")
                print(f"  Opening Balance = {float_balance} + {amount} = {opening}")
            elif txn_type == 'BILL PAYMENT':
                # Balance decreases with BILL PAYMENT, so: Opening = Balance + amount
                opening = float_balance + amount
                print(f"\n  Logic: BILL PAYMENT decreases balance")
                print(f"  Opening Balance = {float_balance} + {amount} = {opening}")
            else:
                # TRANSFER: amount is signed
                opening = float_balance - amount
                print(f"\n  Logic: TRANSFER (signed amount)")
                print(f"  Opening Balance = {float_balance} - {amount} = {opening}")

        # Also check order: get first 3 to see ordering
        print(f"\n\nFirst 3 Transactions in Database (ASC order):")
        print("-" * 80)
        result = db.execute(text("""
            SELECT txn_date, txn_type, amount, float_balance
            FROM umtn_raw_statements
            WHERE run_id = :run_id
            ORDER BY txn_date ASC
            LIMIT 3
        """), {"run_id": run_id})

        for i, row in enumerate(result.fetchall(), 1):
            print(f"{i}. {row[0]} | {row[1]:<15} | Amount: {row[2]:<10} | Balance: {row[3]}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
