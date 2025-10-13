#!/usr/bin/env python3
"""
Investigate Failed UMTN Files
Analyzes why certain XLSX files fail balance verification
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.db import SessionLocal


def main():
    """Investigate failed files"""
    # Failed run_ids from the comprehensive test
    failed_run_ids = [
        '657dd50270b2f',  # 2023-12
        '65805b3eb5340',  # 2023-12
        '65aa8fa085892',  # 2024-01
        '660e6066b1dab',  # 2024-04
        '663a1921d7189',  # 2024-05
        '665f0c8a236e3',  # 2024-06
        '672a012540926',  # 2024-11
        '674d664b7aaaf',  # 2024-12
        '679d7badbc313',  # 2025-02
        '681475d42984a',  # 2025-05
        '684008c412cf6',  # 2025-06
        '68639937f2428',  # 2025-07
        '6863b346144ea',  # 2025-07
        '688c846e2c646',  # 2025-08
        '68b6a8d69dadd',  # 2025-09
    ]

    print(f"\n{'='*80}")
    print("INVESTIGATING FAILED UMTN FILES")
    print(f"{'='*80}\n")

    db = SessionLocal()
    try:
        # Analyze each failed file
        for i, run_id in enumerate(failed_run_ids[:3], 1):  # Check first 3
            print(f"[{i}/3] Analyzing {run_id}")
            print("-" * 80)

            # Get summary info
            result = db.execute(text("""
                SELECT
                    balance_match,
                    verification_status,
                    verification_reason,
                    first_balance,
                    last_balance,
                    calculated_closing_balance,
                    balance_diff_changes
                FROM summary
                WHERE run_id = :run_id
            """), {"run_id": run_id})

            summary = result.fetchone()
            if not summary:
                print(f"  No summary found for {run_id}")
                continue

            print(f"  Balance Match: {summary[0]}")
            print(f"  Verification: {summary[1]}")
            print(f"  Reason: {summary[2]}")
            print(f"  First Balance: {summary[3]}")
            print(f"  Last Balance: {summary[4]}")
            print(f"  Calculated Closing: {summary[5]}")
            print(f"  Balance Diff Changes: {summary[6]}")

            # Check for unknown transaction types
            result = db.execute(text("""
                SELECT DISTINCT txn_type
                FROM umtn_raw_statements
                WHERE run_id = :run_id
                ORDER BY txn_type
            """), {"run_id": run_id})

            txn_types = [row[0] for row in result.fetchall()]
            print(f"  Transaction Types: {', '.join(txn_types)}")

            # Find first transaction with non-zero balance_diff
            result = db.execute(text("""
                SELECT
                    txn_date,
                    txn_type,
                    amount,
                    fee,
                    float_balance,
                    calculated_running_balance,
                    balance_diff
                FROM umtn_processed_statements
                WHERE run_id = :run_id
                  AND ABS(balance_diff) > 0.01
                ORDER BY txn_date ASC
                LIMIT 1
            """), {"run_id": run_id})

            first_mismatch = result.fetchone()
            if first_mismatch:
                print(f"\n  First Mismatch:")
                print(f"    Date: {first_mismatch[0]}")
                print(f"    Type: {first_mismatch[1]}")
                print(f"    Amount: {first_mismatch[2]}")
                print(f"    Fee: {first_mismatch[3]}")
                print(f"    Statement Balance: {first_mismatch[4]}")
                print(f"    Calculated Balance: {first_mismatch[5]}")
                print(f"    Difference: {first_mismatch[6]}")

            # Get context: 2 transactions before and 2 after
            result = db.execute(text("""
                SELECT
                    txn_date,
                    txn_type,
                    amount,
                    fee,
                    float_balance,
                    calculated_running_balance,
                    balance_diff
                FROM umtn_processed_statements
                WHERE run_id = :run_id
                  AND txn_date <= :mismatch_date
                ORDER BY txn_date DESC
                LIMIT 3
            """), {"run_id": run_id, "mismatch_date": first_mismatch[0] if first_mismatch else None})

            print(f"\n  Context (before mismatch):")
            for row in reversed(list(result.fetchall())):
                print(f"    {row[0]} | {row[1]:<15} | Amt:{row[2]:>10.2f} | Fee:{row[3]:>6.2f} | Stmt:{row[4]:>10.2f} | Calc:{row[5]:>10.2f} | Diff:{row[6]:>8.2f}")

            print()

    finally:
        db.close()

    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
