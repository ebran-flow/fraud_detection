#!/usr/bin/env python3
"""
Test all three strategies on a sample of statements and compare actual results.

For each statement, reprocess with:
1. Strategy A: Always disable implicit fees
2. Strategy B: Always enable implicit fees
3. Strategy C: Use voting algorithm (current)

Compare which produces the best balance_match and balance_diff_changes.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.processor import process_statement

# Get from environment
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

# Create engine
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')
Session = sessionmaker(bind=engine)

def force_reprocess_with_flags(db, run_id, force_cashback, force_ind02):
    """
    Temporarily override detection to force specific flags, then reprocess.
    Returns the summary results.
    """
    import app.services.balance_utils as balance_utils

    # Save original functions
    original_detect_cashback = balance_utils.detect_uses_implicit_cashback
    original_detect_ind02 = balance_utils.detect_uses_implicit_ind02_commission

    try:
        # Override detection functions
        balance_utils.detect_uses_implicit_cashback = lambda txns: force_cashback
        balance_utils.detect_uses_implicit_ind02_commission = lambda txns: force_ind02

        # Delete existing summary
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM uatl_processed_statements WHERE run_id = :run_id"), {'run_id': run_id})
            conn.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {'run_id': run_id})
            conn.commit()

        # Reprocess
        result = process_statement(db, run_id)

        # Get summary
        with engine.connect() as conn:
            summary = conn.execute(text("""
                SELECT balance_match, balance_diff_changes, balance_diff_change_ratio,
                       calculated_closing_balance, last_balance
                FROM summary WHERE run_id = :run_id
            """), {'run_id': run_id}).fetchone()

            if summary:
                return {
                    'balance_match': summary[0],
                    'balance_diff_changes': summary[1],
                    'balance_diff_change_ratio': float(summary[2]),
                    'calculated_closing': float(summary[3]),
                    'stated_closing': float(summary[4]),
                    'closing_diff': abs(float(summary[3]) - float(summary[4]))
                }

        return None

    finally:
        # Restore original functions
        balance_utils.detect_uses_implicit_cashback = original_detect_cashback
        balance_utils.detect_uses_implicit_ind02_commission = original_detect_ind02

def main():
    print("=" * 80)
    print("STRATEGY COMPARISON: Testing All 3 Approaches on Sample")
    print("=" * 80)
    print()

    # Select a diverse sample of statements
    print("Step 1: Selecting sample statements...")
    with engine.connect() as conn:
        # Get 50 Success and 50 Failed statements
        sample_run_ids = []

        # Success statements
        result = conn.execute(text("""
            SELECT s.run_id
            FROM summary s
            JOIN metadata m ON s.run_id = m.run_id
            WHERE m.acc_prvdr_code = 'UATL'
            AND s.uses_implicit_cashback IS NOT NULL
            AND s.balance_match = 'Success'
            ORDER BY RAND()
            LIMIT 50
        """))
        sample_run_ids.extend([row[0] for row in result])

        # Failed statements
        result = conn.execute(text("""
            SELECT s.run_id
            FROM summary s
            JOIN metadata m ON s.run_id = m.run_id
            WHERE m.acc_prvdr_code = 'UATL'
            AND s.uses_implicit_cashback IS NOT NULL
            AND s.balance_match = 'Failed'
            ORDER BY RAND()
            LIMIT 50
        """))
        sample_run_ids.extend([row[0] for row in result])

    print(f"Selected {len(sample_run_ids)} statements")

    # Test each strategy
    results = {
        'always_disabled': [],
        'always_enabled': [],
        'voting': []
    }

    db = Session()

    try:
        for i, run_id in enumerate(sample_run_ids):
            print(f"\nTesting statement {i+1}/{len(sample_run_ids)}: {run_id}")

            # Strategy A: Always Disable
            print("  Testing: Always Disable...", end='', flush=True)
            result_disabled = force_reprocess_with_flags(db, run_id, False, False)
            if result_disabled:
                results['always_disabled'].append({
                    'run_id': run_id,
                    **result_disabled
                })
                print(f" {result_disabled['balance_match']}, diff_changes={result_disabled['balance_diff_changes']}")
            else:
                print(" FAILED")

            # Strategy B: Always Enable
            print("  Testing: Always Enable...", end='', flush=True)
            result_enabled = force_reprocess_with_flags(db, run_id, True, True)
            if result_enabled:
                results['always_enabled'].append({
                    'run_id': run_id,
                    **result_enabled
                })
                print(f" {result_enabled['balance_match']}, diff_changes={result_enabled['balance_diff_changes']}")
            else:
                print(" FAILED")

            # Strategy C: Voting (current)
            print("  Testing: Voting Algorithm...", end='', flush=True)
            # Delete and reprocess with voting
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM uatl_processed_statements WHERE run_id = :run_id"), {'run_id': run_id})
                conn.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {'run_id': run_id})
                conn.commit()

            process_statement(db, run_id)

            with engine.connect() as conn:
                summary = conn.execute(text("""
                    SELECT balance_match, balance_diff_changes, balance_diff_change_ratio,
                           calculated_closing_balance, last_balance
                    FROM summary WHERE run_id = :run_id
                """), {'run_id': run_id}).fetchone()

                if summary:
                    result_voting = {
                        'run_id': run_id,
                        'balance_match': summary[0],
                        'balance_diff_changes': summary[1],
                        'balance_diff_change_ratio': float(summary[2]),
                        'calculated_closing': float(summary[3]),
                        'stated_closing': float(summary[4]),
                        'closing_diff': abs(float(summary[3]) - float(summary[4]))
                    }
                    results['voting'].append(result_voting)
                    print(f" {result_voting['balance_match']}, diff_changes={result_voting['balance_diff_changes']}")
                else:
                    print(" FAILED")

    finally:
        db.close()

    # Analyze results
    print("\n\n" + "=" * 80)
    print("RESULTS COMPARISON")
    print("=" * 80)

    def analyze_strategy(name, data):
        total = len(data)
        success_count = sum(1 for r in data if r['balance_match'] == 'Success')
        avg_diff_changes = sum(r['balance_diff_changes'] for r in data) / total if total > 0 else 0
        avg_diff_ratio = sum(r['balance_diff_change_ratio'] for r in data) / total if total > 0 else 0
        avg_closing_diff = sum(r['closing_diff'] for r in data) / total if total > 0 else 0

        return {
            'name': name,
            'total': total,
            'success_count': success_count,
            'success_rate': success_count / total * 100 if total > 0 else 0,
            'avg_diff_changes': avg_diff_changes,
            'avg_diff_ratio': avg_diff_ratio,
            'avg_closing_diff': avg_closing_diff
        }

    stats = {
        'always_disabled': analyze_strategy('Always Disable', results['always_disabled']),
        'always_enabled': analyze_strategy('Always Enable', results['always_enabled']),
        'voting': analyze_strategy('Voting Algorithm', results['voting'])
    }

    # Print comparison table
    print(f"\n{'Metric':<30} {'Always Disable':<18} {'Always Enable':<18} {'Voting':<18}")
    print("-" * 90)
    print(f"{'Total Statements':<30} {stats['always_disabled']['total']:<18} {stats['always_enabled']['total']:<18} {stats['voting']['total']:<18}")
    print(f"{'Success Count':<30} {stats['always_disabled']['success_count']:<18} {stats['always_enabled']['success_count']:<18} {stats['voting']['success_count']:<18}")
    print(f"{'Success Rate (%)':<30} {stats['always_disabled']['success_rate']:<18.2f} {stats['always_enabled']['success_rate']:<18.2f} {stats['voting']['success_rate']:<18.2f}")
    print(f"{'Avg Diff Changes':<30} {stats['always_disabled']['avg_diff_changes']:<18.2f} {stats['always_enabled']['avg_diff_changes']:<18.2f} {stats['voting']['avg_diff_changes']:<18.2f}")
    print(f"{'Avg Diff Ratio':<30} {stats['always_disabled']['avg_diff_ratio']:<18.6f} {stats['always_enabled']['avg_diff_ratio']:<18.6f} {stats['voting']['avg_diff_ratio']:<18.6f}")
    print(f"{'Avg Closing Diff':<30} {stats['always_disabled']['avg_closing_diff']:<18.2f} {stats['always_enabled']['avg_closing_diff']:<18.2f} {stats['voting']['avg_closing_diff']:<18.2f}")

    # Determine winner for each metric
    print("\n" + "=" * 80)
    print("WINNER BY METRIC")
    print("=" * 80)

    # Success rate (higher is better)
    max_success = max(s['success_rate'] for s in stats.values())
    winner_success = [name for name, s in stats.items() if s['success_rate'] == max_success][0]
    print(f"\n✓ Best Success Rate: {winner_success.replace('_', ' ').title()} ({max_success:.2f}%)")

    # Avg diff changes (lower is better)
    min_diff_changes = min(s['avg_diff_changes'] for s in stats.values())
    winner_diff = [name for name, s in stats.items() if s['avg_diff_changes'] == min_diff_changes][0]
    print(f"✓ Lowest Avg Diff Changes: {winner_diff.replace('_', ' ').title()} ({min_diff_changes:.2f})")

    # Avg closing diff (lower is better)
    min_closing = min(s['avg_closing_diff'] for s in stats.values())
    winner_closing = [name for name, s in stats.items() if s['avg_closing_diff'] == min_closing][0]
    print(f"✓ Lowest Avg Closing Diff: {winner_closing.replace('_', ' ').title()} ({min_closing:.2f})")

    # Overall score
    scores = {'always_disabled': 0, 'always_enabled': 0, 'voting': 0}
    scores[winner_success] += 1
    scores[winner_diff] += 1
    scores[winner_closing] += 1

    print(f"\n{'Strategy':<30} {'Score (out of 3)':<20}")
    print("-" * 50)
    for name, score in sorted(scores.items(), key=lambda x: -x[1]):
        print(f"{name.replace('_', ' ').title():<30} {score:<20}")

    overall_winner = max(scores.items(), key=lambda x: x[1])[0]
    print(f"\n\n🏆 OVERALL WINNER: {overall_winner.replace('_', ' ').upper()}")

    # Statement-by-statement comparison
    print("\n\n" + "=" * 80)
    print("STATEMENT-BY-STATEMENT WIN/LOSS")
    print("=" * 80)

    wins = {'always_disabled': 0, 'always_enabled': 0, 'voting': 0, 'tie': 0}

    for i in range(len(results['always_disabled'])):
        run_id = results['always_disabled'][i]['run_id']
        diffs = {
            'always_disabled': results['always_disabled'][i]['balance_diff_changes'],
            'always_enabled': results['always_enabled'][i]['balance_diff_changes'],
            'voting': results['voting'][i]['balance_diff_changes']
        }

        min_diff = min(diffs.values())
        winners = [k for k, v in diffs.items() if v == min_diff]

        if len(winners) == 1:
            wins[winners[0]] += 1
        else:
            wins['tie'] += 1

    print(f"\nWins (lowest balance_diff_changes):")
    print(f"  Always Disable: {wins['always_disabled']}")
    print(f"  Always Enable: {wins['always_enabled']}")
    print(f"  Voting: {wins['voting']}")
    print(f"  Tie: {wins['tie']}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
