#!/usr/bin/env python3
"""
Analyze New Transaction Types
Understand how ADJUSTMENT, DEPOSIT, LOAN_REPAYMENT, REFUND, REVERSAL affect balance
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.db import SessionLocal


def main():
    """Analyze new transaction types"""
    new_types = ['ADJUSTMENT', 'DEPOSIT', 'LOAN_REPAYMENT', 'REFUND', 'REVERSAL']

    print(f"\n{'='*100}")
    print("ANALYZING NEW TRANSACTION TYPES")
    print(f"{'='*100}\n")

    db = SessionLocal()
    try:
        for txn_type in new_types:
            print(f"{txn_type}:")
            print("-" * 100)

            # Get 5 examples with context
            result = db.execute(text("""
                SELECT
                    run_id,
                    txn_date,
                    amount,
                    fee,
                    float_balance,
                    description
                FROM umtn_raw_statements
                WHERE txn_type = :txn_type
                ORDER BY txn_date ASC
                LIMIT 5
            """), {"txn_type": txn_type})

            examples = result.fetchall()
            if not examples:
                print(f"  No examples found\n")
                continue

            for i, ex in enumerate(examples, 1):
                run_id, txn_date, amount, fee, float_balance, desc = ex
                print(f"\n  Example {i}: {run_id}")
                print(f"    Date: {txn_date}")
                print(f"    Amount: {amount}")
                print(f"    Fee: {fee}")
                print(f"    Float Balance: {float_balance}")
                print(f"    Description: {desc[:80] if desc else 'N/A'}")

                # Get previous transaction to see balance change
                result2 = db.execute(text("""
                    SELECT
                        txn_date,
                        txn_type,
                        amount,
                        float_balance
                    FROM umtn_raw_statements
                    WHERE run_id = :run_id
                      AND txn_date < :txn_date
                    ORDER BY txn_date DESC, float_balance DESC
                    LIMIT 1
                """), {"run_id": run_id, "txn_date": txn_date})

                prev = result2.fetchone()
                if prev:
                    prev_balance = float(prev[3])
                    curr_balance = float(float_balance)
                    balance_change = curr_balance - prev_balance
                    amount_val = float(amount)

                    print(f"    Previous: {prev[0]} | {prev[1]} | Balance: {prev_balance}")
                    print(f"    Balance Change: {balance_change} (Amount: {amount_val})")

                    # Determine pattern
                    if abs(balance_change - amount_val) < 0.01:
                        pattern = "Balance change = +amount"
                    elif abs(balance_change + amount_val) < 0.01:
                        pattern = "Balance change = -amount"
                    else:
                        pattern = f"Unknown pattern (diff: {balance_change - amount_val})"
                    print(f"    Pattern: {pattern}")

            print()

    finally:
        db.close()

    print(f"{'='*100}\n")


if __name__ == '__main__':
    main()
