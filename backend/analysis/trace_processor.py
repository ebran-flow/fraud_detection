#!/usr/bin/env python3
"""
Trace Processor Logic
Replicates what the processor does to find the 880066 discrepancy
"""
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal
from app.services.balance_utils import calculate_opening_balance_mtn, apply_transaction_mtn


def main():
    """Trace processor logic"""
    run_id = "66ec2b21c7585"
    balance_field = 'float_balance'

    db = SessionLocal()
    try:
        # Step 1: Load raw statements (simulating what processor does)
        print("\n" + "="*80)
        print("STEP 1: Load raw statements from database")
        print("="*80)
        result = db.execute(text("""
            SELECT id, txn_date, txn_type, amount, fee, float_balance
            FROM umtn_raw_statements
            WHERE run_id = :run_id
        """), {"run_id": run_id})

        rows = result.fetchall()
        print(f"Loaded {len(rows)} raw statements")

        # Step 2: Create DataFrame
        print("\n" + "="*80)
        print("STEP 2: Create DataFrame")
        print("="*80)
        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'txn_date': row[1],
                'txn_type': row[2],
                'amount': float(row[3]),
                'fee': float(row[4]),
                'float_balance': float(row[5])
            })
        df = pd.DataFrame(data)
        print(f"DataFrame shape: {df.shape}")
        print(f"First row BEFORE sorting:")
        print(f"  {df.iloc[0][['txn_date', 'txn_type', 'amount', 'fee', 'float_balance']].to_dict()}")

        # Step 3: Sort dataframe
        print("\n" + "="*80)
        print("STEP 3: Sort by ['txn_date', 'float_balance'], ascending=[True, False]")
        print("="*80)
        df = df.sort_values(['txn_date', balance_field], ascending=[True, False]).reset_index(drop=True)
        print(f"First row AFTER sorting:")
        first_row = df.iloc[0]
        print(f"  Date: {first_row['txn_date']}")
        print(f"  Type: {first_row['txn_type']}")
        print(f"  Amount: {first_row['amount']}")
        print(f"  Fee: {first_row['fee']}")
        print(f"  Balance: {first_row['float_balance']}")

        # Step 4: Calculate opening balance
        print("\n" + "="*80)
        print("STEP 4: Calculate opening balance")
        print("="*80)
        first_balance = first_row['float_balance']
        first_amount = first_row['amount']
        first_fee = first_row['fee']
        first_txn_type = first_row['txn_type']

        opening_balance = calculate_opening_balance_mtn(first_balance, first_amount, first_txn_type, first_fee)
        print(f"Opening balance calculated: {opening_balance}")

        # Step 5: Find where the diff first becomes non-zero
        print("\n" + "="*80)
        print("STEP 5: Find first transaction where diff != 0")
        print("="*80)
        running_balance = opening_balance
        for i in range(len(df)):
            row = df.iloc[i]
            running_balance = apply_transaction_mtn(running_balance, row['amount'], row['txn_type'], row['fee'])
            diff = running_balance - row['float_balance']

            if abs(diff) > 0.01:
                # Print context: previous transaction, this transaction, next transaction
                print(f"\nFirst non-zero diff at transaction {i+1}:")
                if i > 0:
                    prev_row = df.iloc[i-1]
                    print(f"\n  Previous transaction {i}:")
                    print(f"    Date: {prev_row['txn_date']}")
                    print(f"    Type: {prev_row['txn_type']}")
                    print(f"    Amount: {prev_row['amount']}")
                    print(f"    Fee: {prev_row['fee']}")
                    print(f"    Balance: {prev_row['float_balance']}")

                print(f"\n  This transaction {i+1} (FIRST MISMATCH):")
                print(f"    Date: {row['txn_date']}")
                print(f"    Type: {row['txn_type']}")
                print(f"    Amount: {row['amount']}")
                print(f"    Fee: {row['fee']}")
                print(f"    Statement Balance: {row['float_balance']:.2f}")
                print(f"    Calculated Balance: {running_balance:.2f}")
                print(f"    Difference: {diff:.2f}")

                if i < len(df) - 1:
                    next_row = df.iloc[i+1]
                    print(f"\n  Next transaction {i+2}:")
                    print(f"    Date: {next_row['txn_date']}")
                    print(f"    Type: {next_row['txn_type']}")
                    print(f"    Amount: {next_row['amount']}")
                    print(f"    Fee: {next_row['fee']}")
                    print(f"    Balance: {next_row['float_balance']}")
                break

        # Step 6: Check last balance
        print("\n" + "="*80)
        print("STEP 6: Calculate final balance")
        print("="*80)
        running_balance = opening_balance
        for i in range(len(df)):
            row = df.iloc[i]
            running_balance = apply_transaction_mtn(running_balance, row['amount'], row['txn_type'], row['fee'])

        last_row = df.iloc[-1]
        print(f"Calculated closing balance: {running_balance:.2f}")
        print(f"Statement closing balance: {last_row['float_balance']:.2f}")
        print(f"Difference: {running_balance - last_row['float_balance']:.2f}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
