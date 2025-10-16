#!/usr/bin/env python3
"""
Compare three implicit fee strategies:
1. Always apply implicit fees (all statements)
2. Never apply implicit fees (all statements)
3. Use voting algorithm (current approach)

For each strategy, calculate:
- Balance match success rate
- Average balance_diff_changes
- Average balance_diff_change_ratio
- Closing balance accuracy
- Number of degradations vs improvements
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.processor import process_statement

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get from environment
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

# Create engine
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')
Session = sessionmaker(bind=engine)

def get_baseline_stats():
    """Get current stats (with voting algorithm - Round 3)"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_statements,
                SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) as success_count,
                AVG(balance_diff_changes) as avg_diff_changes,
                AVG(balance_diff_change_ratio) as avg_diff_ratio,
                AVG(ABS(s.calculated_closing_balance - s.last_balance)) as avg_closing_diff,
                SUM(uses_implicit_cashback = 1) as cashback_enabled_count,
                SUM(uses_implicit_ind02_commission = 1) as ind02_enabled_count
            FROM summary s
            JOIN metadata m ON s.run_id = m.run_id
            WHERE m.acc_prvdr_code = 'UATL'
            AND s.uses_implicit_cashback IS NOT NULL
        """))
        row = result.fetchone()

        return {
            'strategy': 'VOTING ALGORITHM (Current - 10:1 ratio)',
            'total': row[0],
            'success_count': row[1],
            'success_rate': row[1] / row[0] * 100 if row[0] > 0 else 0,
            'avg_diff_changes': float(row[2]) if row[2] else 0,
            'avg_diff_ratio': float(row[3]) if row[3] else 0,
            'avg_closing_diff': float(row[4]) if row[4] else 0,
            'cashback_enabled': row[5],
            'ind02_enabled': row[6]
        }

def test_sample_with_strategy(run_ids: list, force_cashback: bool = None, force_ind02: bool = None):
    """
    Test a sample of statements with a specific strategy.

    Args:
        run_ids: List of run_ids to test
        force_cashback: None = use voting, True = always enable, False = always disable
        force_ind02: None = use voting, True = always enable, False = always disable
    """
    import pandas as pd
    from app.services.processor import (
        detect_duplicates,
        detect_special_transactions,
        optimize_same_timestamp_transactions,
        calculate_running_balance,
        generate_summary
    )
    from app.services.balance_utils import (
        detect_uses_implicit_cashback,
        detect_uses_implicit_ind02_commission
    )
    from app.models import Metadata

    results = []
    db = Session()

    try:
        for i, run_id in enumerate(run_ids):
            if i % 100 == 0:
                print(f"Testing statement {i+1}/{len(run_ids)}...")

            # Get metadata
            metadata = db.query(Metadata).filter(Metadata.run_id == run_id).first()
            if not metadata:
                continue

            # Get transactions as DataFrame
            with engine.connect() as conn:
                df = pd.read_sql(text("""
                    SELECT *
                    FROM uatl_processed_statements
                    WHERE run_id = :run_id
                    ORDER BY txn_date ASC, txn_id ASC
                """), conn, params={'run_id': run_id})

            if df.empty:
                continue

            # Convert to list of dicts for detection
            txns = df.to_dict('records')

            # Determine flags based on strategy
            if force_cashback is None:
                uses_cashback = detect_uses_implicit_cashback(txns)
            else:
                uses_cashback = force_cashback

            if force_ind02 is None:
                uses_ind02 = detect_uses_implicit_ind02_commission(txns)
            else:
                uses_ind02 = force_ind02

            # Apply all preprocessing steps
            df = detect_duplicates(df)
            df = detect_special_transactions(df)
            df = optimize_same_timestamp_transactions(df, metadata.pdf_format, 'balance')

            # Calculate running balance with strategy flags
            df_processed = calculate_running_balance(
                df,
                metadata.pdf_format,
                'UATL',
                'balance',
                uses_implicit_cashback=uses_cashback,
                uses_implicit_ind02_commission=uses_ind02
            )

            # Generate summary
            summary = generate_summary(
                df_processed,
                metadata,
                run_id,
                'UATL',
                'balance',
                uses_implicit_cashback=uses_cashback,
                uses_implicit_ind02_commission=uses_ind02
            )

            results.append({
                'run_id': run_id,
                'balance_match': summary['balance_match'],
                'balance_diff_changes': summary['balance_diff_changes'],
                'balance_diff_change_ratio': summary['balance_diff_change_ratio'],
                'calculated_closing': summary['calculated_closing_balance'],
                'stated_closing': summary['last_balance'],
                'closing_diff': abs(summary['calculated_closing_balance'] - summary['last_balance']),
                'uses_cashback': uses_cashback,
                'uses_ind02': uses_ind02
            })

    finally:
        db.close()

    return results

def analyze_results(results, strategy_name):
    """Analyze results from a strategy"""
    total = len(results)
    success_count = sum(1 for r in results if r['balance_match'] == 'Success')
    avg_diff_changes = sum(r['balance_diff_changes'] for r in results) / total if total > 0 else 0
    avg_diff_ratio = sum(r['balance_diff_change_ratio'] for r in results) / total if total > 0 else 0
    avg_closing_diff = sum(r['closing_diff'] for r in results) / total if total > 0 else 0
    cashback_enabled = sum(1 for r in results if r['uses_cashback'])
    ind02_enabled = sum(1 for r in results if r['uses_ind02'])

    return {
        'strategy': strategy_name,
        'total': total,
        'success_count': success_count,
        'success_rate': success_count / total * 100 if total > 0 else 0,
        'avg_diff_changes': avg_diff_changes,
        'avg_diff_ratio': avg_diff_ratio,
        'avg_closing_diff': avg_closing_diff,
        'cashback_enabled': cashback_enabled,
        'ind02_enabled': ind02_enabled
    }

def compare_with_current(current_results, new_results, strategy_name):
    """Compare new strategy results with current (voting algorithm) results"""
    improvements = 0
    degradations = 0
    unchanged = 0

    improvement_details = []
    degradation_details = []

    # Create lookup dict for current results
    current_dict = {r['run_id']: r for r in current_results}

    for new_r in new_results:
        run_id = new_r['run_id']
        if run_id not in current_dict:
            continue

        curr_r = current_dict[run_id]

        # Compare balance_diff_changes (lower is better)
        diff_change = new_r['balance_diff_changes'] - curr_r['balance_diff_changes']

        if diff_change < 0:  # Improved
            improvements += 1
            improvement_details.append({
                'run_id': run_id,
                'diff_changes_old': curr_r['balance_diff_changes'],
                'diff_changes_new': new_r['balance_diff_changes'],
                'improvement': -diff_change
            })
        elif diff_change > 0:  # Degraded
            degradations += 1
            degradation_details.append({
                'run_id': run_id,
                'diff_changes_old': curr_r['balance_diff_changes'],
                'diff_changes_new': new_r['balance_diff_changes'],
                'degradation': diff_change
            })
        else:
            unchanged += 1

    return {
        'improvements': improvements,
        'degradations': degradations,
        'unchanged': unchanged,
        'improvement_details': improvement_details[:10],  # Top 10
        'degradation_details': degradation_details[:10]    # Top 10
    }

def main():
    print("=" * 80)
    print("IMPLICIT FEE STRATEGY COMPARISON")
    print("=" * 80)
    print()

    # Get baseline (current voting algorithm)
    print("Step 1: Getting baseline stats (Voting Algorithm - Round 3)...")
    baseline = get_baseline_stats()

    print(f"\nBaseline Stats:")
    print(f"  Strategy: {baseline['strategy']}")
    print(f"  Total Statements: {baseline['total']:,}")
    print(f"  Success Count: {baseline['success_count']:,} ({baseline['success_rate']:.2f}%)")
    print(f"  Avg Balance Diff Changes: {baseline['avg_diff_changes']:.2f}")
    print(f"  Avg Balance Diff Ratio: {baseline['avg_diff_ratio']:.6f}")
    print(f"  Avg Closing Balance Diff: {baseline['avg_closing_diff']:.2f}")
    print(f"  Cashback Enabled: {baseline['cashback_enabled']:,} ({baseline['cashback_enabled']/baseline['total']*100:.1f}%)")
    print(f"  IND02 Enabled: {baseline['ind02_enabled']:,} ({baseline['ind02_enabled']/baseline['total']*100:.1f}%)")

    # Get sample of statements for testing (use a representative sample)
    print("\n\nStep 2: Selecting sample statements for detailed comparison...")
    with engine.connect() as conn:
        # Get a stratified sample:
        # - 500 Success statements
        # - 500 Failed statements
        # - Mix of different balance_diff_changes values
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
            LIMIT 500
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
            LIMIT 500
        """))
        sample_run_ids.extend([row[0] for row in result])

    print(f"Selected {len(sample_run_ids)} statements for testing")

    # Get current results for sample
    print("\n\nStep 3: Getting current results for sample...")
    with engine.connect() as conn:
        placeholders = ','.join([':id' + str(i) for i in range(len(sample_run_ids))])
        params = {f'id{i}': run_id for i, run_id in enumerate(sample_run_ids)}

        result = conn.execute(text(f"""
            SELECT run_id, balance_match, balance_diff_changes, balance_diff_change_ratio,
                   calculated_closing_balance, last_balance,
                   uses_implicit_cashback, uses_implicit_ind02_commission
            FROM summary
            WHERE run_id IN ({placeholders})
        """), params)

        current_results = []
        for row in result:
            current_results.append({
                'run_id': row[0],
                'balance_match': row[1],
                'balance_diff_changes': row[2],
                'balance_diff_change_ratio': float(row[3]) if row[3] else 0,
                'calculated_closing': float(row[4]),
                'stated_closing': float(row[5]),
                'closing_diff': abs(float(row[4]) - float(row[5])),
                'uses_cashback': bool(row[6]),
                'uses_ind02': bool(row[7])
            })

    current_stats = analyze_results(current_results, "VOTING ALGORITHM (10:1)")

    # Strategy 1: Always enable implicit fees
    print("\n\nStep 4: Testing Strategy 1 - ALWAYS ENABLE implicit fees...")
    always_enable_results = test_sample_with_strategy(
        sample_run_ids,
        force_cashback=True,
        force_ind02=True
    )
    always_enable_stats = analyze_results(always_enable_results, "ALWAYS ENABLE")
    always_enable_comparison = compare_with_current(current_results, always_enable_results, "ALWAYS ENABLE")

    # Strategy 2: Always disable implicit fees
    print("\n\nStep 5: Testing Strategy 2 - ALWAYS DISABLE implicit fees...")
    always_disable_results = test_sample_with_strategy(
        sample_run_ids,
        force_cashback=False,
        force_ind02=False
    )
    always_disable_stats = analyze_results(always_disable_results, "ALWAYS DISABLE")
    always_disable_comparison = compare_with_current(current_results, always_disable_results, "ALWAYS DISABLE")

    # Strategy 3: Voting algorithm (current)
    # Already have the stats from current_stats

    # Print comparison table
    print("\n\n" + "=" * 80)
    print("RESULTS COMPARISON (Sample of 1000 statements)")
    print("=" * 80)
    print()

    strategies = [current_stats, always_enable_stats, always_disable_stats]

    print(f"{'Metric':<40} {'Voting':<15} {'Always Enable':<15} {'Always Disable':<15}")
    print("-" * 85)
    print(f"{'Success Count':<40} {current_stats['success_count']:<15} {always_enable_stats['success_count']:<15} {always_disable_stats['success_count']:<15}")
    print(f"{'Success Rate (%)':<40} {current_stats['success_rate']:<15.2f} {always_enable_stats['success_rate']:<15.2f} {always_disable_stats['success_rate']:<15.2f}")
    print(f"{'Avg Balance Diff Changes':<40} {current_stats['avg_diff_changes']:<15.2f} {always_enable_stats['avg_diff_changes']:<15.2f} {always_disable_stats['avg_diff_changes']:<15.2f}")
    print(f"{'Avg Balance Diff Ratio':<40} {current_stats['avg_diff_ratio']:<15.6f} {always_enable_stats['avg_diff_ratio']:<15.6f} {always_disable_stats['avg_diff_ratio']:<15.6f}")
    print(f"{'Avg Closing Balance Diff':<40} {current_stats['avg_closing_diff']:<15.2f} {always_enable_stats['avg_closing_diff']:<15.2f} {always_disable_stats['avg_closing_diff']:<15.2f}")
    print(f"{'Cashback Enabled Count':<40} {current_stats['cashback_enabled']:<15} {always_enable_stats['cashback_enabled']:<15} {always_disable_stats['cashback_enabled']:<15}")
    print(f"{'IND02 Enabled Count':<40} {current_stats['ind02_enabled']:<15} {always_enable_stats['ind02_enabled']:<15} {always_disable_stats['ind02_enabled']:<15}")

    print("\n\n" + "=" * 80)
    print("COMPARISON VS VOTING ALGORITHM (Current)")
    print("=" * 80)

    print(f"\nStrategy: ALWAYS ENABLE")
    print(f"  Improvements: {always_enable_comparison['improvements']} statements")
    print(f"  Degradations: {always_enable_comparison['degradations']} statements")
    print(f"  Unchanged: {always_enable_comparison['unchanged']} statements")
    print(f"  Net Impact: {always_enable_comparison['improvements'] - always_enable_comparison['degradations']:+d}")

    print(f"\nStrategy: ALWAYS DISABLE")
    print(f"  Improvements: {always_disable_comparison['improvements']} statements")
    print(f"  Degradations: {always_disable_comparison['degradations']} statements")
    print(f"  Unchanged: {always_disable_comparison['unchanged']} statements")
    print(f"  Net Impact: {always_disable_comparison['improvements'] - always_disable_comparison['degradations']:+d}")

    # Determine best strategy
    print("\n\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    # Best strategy is the one with:
    # 1. Highest success rate
    # 2. Lowest avg_diff_changes
    # 3. Lowest avg_closing_diff

    scores = {
        'Voting': 0,
        'Always Enable': 0,
        'Always Disable': 0
    }

    # Success rate (higher is better)
    max_success = max(s['success_rate'] for s in strategies)
    for s in strategies:
        if s['success_rate'] == max_success:
            scores[s['strategy'].split(' ')[0] if s['strategy'].startswith('ALWAYS') else 'Voting'] += 1

    # Avg diff changes (lower is better)
    min_diff_changes = min(s['avg_diff_changes'] for s in strategies)
    for s in strategies:
        if s['avg_diff_changes'] == min_diff_changes:
            scores[s['strategy'].split(' ')[0] if s['strategy'].startswith('ALWAYS') else 'Voting'] += 1

    # Avg closing diff (lower is better)
    min_closing_diff = min(s['avg_closing_diff'] for s in strategies)
    for s in strategies:
        if s['avg_closing_diff'] == min_closing_diff:
            scores[s['strategy'].split(' ')[0] if s['strategy'].startswith('ALWAYS') else 'Voting'] += 1

    print(f"\nScores (higher is better):")
    for strategy, score in sorted(scores.items(), key=lambda x: -x[1]):
        print(f"  {strategy}: {score}/3")

    best_strategy = max(scores.items(), key=lambda x: x[1])[0]
    print(f"\n✓ RECOMMENDED STRATEGY: {best_strategy}")

    # Show why
    best_stats = next(s for s in strategies if best_strategy.lower() in s['strategy'].lower())
    print(f"\nReason:")
    print(f"  - Success Rate: {best_stats['success_rate']:.2f}%")
    print(f"  - Avg Balance Diff Changes: {best_stats['avg_diff_changes']:.2f}")
    print(f"  - Avg Closing Balance Diff: {best_stats['avg_closing_diff']:.2f}")

if __name__ == '__main__':
    main()
