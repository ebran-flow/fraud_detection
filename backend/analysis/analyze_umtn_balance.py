#!/usr/bin/env python3
"""
Analyze UMTN Balance Logic
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal


def main():
    """Analyze balance changes"""
    run_id = "66ec2b21c7585"

    db = SessionLocal()
    try:
        print(f"\n{'='*70}")
        print(f"UMTN Balance Logic Analysis")
        print(f"{'='*70}\n")

        # Get first 10 transactions to understand the pattern
        result = db.execute(text("""
            SELECT txn_date, txn_type, amount, float_balance, description
            FROM umtn_raw_statements
            WHERE run_id = :run_id
            ORDER BY txn_date ASC
            LIMIT 15
        """), {"run_id": run_id})

        rows = result.fetchall()

        print("Analyzing First 15 Transactions:")
        print("-" * 120)
        print(f"{'#':<3} {'Date':<20} {'Type':<15} {'Amount':>10} {'Float Bal':>10} {'Calc Diff':>12} {'Pattern':<10}")
        print("-" * 120)

        prev_balance = None
        for i, row in enumerate(rows, 1):
            txn_date = str(row[0])
            txn_type = row[1]
            amount = float(row[2])
            float_balance = float(row[3])

            if prev_balance is not None:
                # Calculate what the balance change was
                actual_change = float_balance - prev_balance

                # Determine the pattern based on transaction type
                if txn_type == 'CASH_OUT':
                    # For CASH_OUT: agent pays cash, receives mobile money
                    # Expected: balance increases by amount
                    expected_change = amount
                    pattern = "+amount" if abs(actual_change - amount) < 0.01 else f"?({actual_change:.0f})"
                elif txn_type == 'CASH_IN':
                    # For CASH_IN: agent receives cash, pays mobile money
                    # Expected: balance decreases by amount
                    expected_change = -amount
                    pattern = "-amount" if abs(actual_change + amount) < 0.01 else f"?({actual_change:.0f})"
                elif txn_type == 'BILL PAYMENT':
                    # For BILL PAYMENT: agent pays bill
                    # Expected: balance decreases by amount
                    expected_change = -amount
                    pattern = "-amount" if abs(actual_change + amount) < 0.01 else f"?({actual_change:.0f})"
                elif txn_type == 'TRANSFER':
                    # For TRANSFER: could be positive or negative
                    # If amount matches change, pattern is direct
                    if abs(actual_change - amount) < 0.01:
                        pattern = "=amount"
                    else:
                        pattern = f"?({actual_change:.0f})"
                else:
                    pattern = f"?({actual_change:.0f})"

                print(f"{i:<3} {txn_date:<20} {txn_type:<15} {amount:>10.2f} {float_balance:>10.2f} {actual_change:>12.2f} {pattern:<10}")
            else:
                print(f"{i:<3} {txn_date:<20} {txn_type:<15} {amount:>10.2f} {float_balance:>10.2f} {'(First)':>12} {'-':<10}")

            prev_balance = float_balance

        print(f"\n{'='*70}\n")

    finally:
        db.close()


if __name__ == '__main__':
    main()
