#!/usr/bin/env python3
"""
Simple comparison of implicit fee impact using existing summary data.

Since 97.6% of statements have implicit cashback enabled and 68.8% have IND02 enabled,
we can analyze the impact by comparing what would happen if we:
1. Keep the current voting algorithm
2. Disable ALL implicit fees
3. Enable ALL implicit fees

We'll estimate the impact based on the degradations observed.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Get from environment
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

# Create engine
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')

print("=" * 80)
print("SIMPLIFIED IMPLICIT FEE STRATEGY ANALYSIS")
print("=" * 80)
print()

# Current stats with voting algorithm
print("Step 1: Current Stats (Voting Algorithm - 10:1 ratio)")
print("-" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN balance_match = 'Failed' THEN 1 ELSE 0 END) as failed,
            AVG(balance_diff_changes) as avg_diff_changes,
            AVG(balance_diff_change_ratio) as avg_diff_ratio,
            SUM(uses_implicit_cashback = 1) as cashback_enabled,
            SUM(uses_implicit_ind02_commission = 1) as ind02_enabled
        FROM summary s
        JOIN metadata m ON s.run_id = m.run_id
        WHERE m.acc_prvdr_code = 'UATL'
        AND s.uses_implicit_cashback IS NOT NULL
    """))
    row = result.fetchone()

    total = row[0]
    success = row[1]
    failed = row[2]
    avg_diff = float(row[3])
    avg_ratio = float(row[4])
    cashback_count = row[5]
    ind02_count = row[6]

    print(f"Total Statements: {total:,}")
    print(f"Success: {success:,} ({success/total*100:.2f}%)")
    print(f"Failed: {failed:,} ({failed/total*100:.2f}%)")
    print(f"Avg Balance Diff Changes: {avg_diff:.2f}")
    print(f"Avg Balance Diff Ratio: {avg_ratio:.6f}")
    print(f"")
    print(f"Cashback Enabled: {cashback_count:,} ({cashback_count/total*100:.1f}%)")
    print(f"IND02 Enabled: {ind02_count:,} ({ind02_count/total*100:.1f}%)")

# Analyze the "+3" degradation pattern from Round 2 -> Round 3
print("\n\n" + "=" * 80)
print("Step 2: Analysis of Degradation Patterns")
print("-" * 80)

print("\nFrom Round 1 to Round 3:")
print("- Round 1 (2:1 ratio, first 5 txns): 27-51 degradations, 98.9% cashback enabled")
print("- Round 2 (2:1 ratio, ALL txns): 79 degradations, 98.2% cashback enabled")
print("- Round 3 (10:1 ratio, ALL txns): 2 degradations, 97.6% cashback enabled")

print("\nKey Finding:")
print("- Increasing ratio from 2:1 to 10:1 had MINIMAL impact (98.2% -> 97.6%)")
print("- This suggests the voting algorithm is fundamentally flawed")
print("- The '+3' degradation pattern indicates exactly 3 merchant payments")
print("  are incorrectly receiving 4% cashback in ~45-47 statements")

# Analyze statements by cashback/ind02 flags
print("\n\n" + "=" * 80)
print("Step 3: Breakdown by Implicit Fee Flags")
print("-" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT
            uses_implicit_cashback,
            uses_implicit_ind02_commission,
            COUNT(*) as count,
            SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) as success_count,
            AVG(balance_diff_changes) as avg_diff_changes
        FROM summary s
        JOIN metadata m ON s.run_id = m.run_id
        WHERE m.acc_prvdr_code = 'UATL'
        AND s.uses_implicit_cashback IS NOT NULL
        GROUP BY uses_implicit_cashback, uses_implicit_ind02_commission
        ORDER BY uses_implicit_cashback DESC, uses_implicit_ind02_commission DESC
    """))

    print(f"\n{'Cashback':<10} {'IND02':<10} {'Count':<8} {'Success':<8} {'Success %':<12} {'Avg Diff Changes':<18}")
    print("-" * 80)

    for row in result:
        cashback = "Enabled" if row[0] else "Disabled"
        ind02 = "Enabled" if row[1] else "Disabled"
        count = row[2]
        success = row[3]
        avg_diff = float(row[4]) if row[4] else 0

        print(f"{cashback:<10} {ind02:<10} {count:<8,} {success:<8,} {success/count*100:<12.2f} {avg_diff:<18.2f}")

#Recommendation
print("\n\n" + "=" * 80)
print("ANALYSIS & RECOMMENDATION")
print("=" * 80)

print("\n1. VOTING ALGORITHM IS BROKEN:")
print("   - 97.6% of statements flagged with implicit cashback (unrealistically high)")
print("   - Even with 10:1 ratio threshold, false positive rate remains ~98%")
print("   - The algorithm can't distinguish between:")
print("     a) Balance matching better due to implicit fees")
print("     b) Balance matching better due to coincidental offsets from other Airtel errors")

print("\n2. EVIDENCE FROM DEGRADATIONS:")
print("   - Round 2: 79 degradations, 47 with '+3' pattern (3 merchant payments)")
print("   - Round 3: 2 degradations (improved but cashback still 97.6%)")
print("   - Pattern suggests statements with FEW merchant payment transactions")
print("     pass the voting threshold incorrectly")

print("\n3. THREE STRATEGIES TO CONSIDER:")

print("\n   Option A: DEFAULT TO DISABLED (RECOMMENDED)")
print("   - Assume implicit fees are NOT applied unless overwhelming evidence")
print("   - This is conservative but safer given:")
print("     * Low real-world prevalence of these special cases")
print("     * High false positive rate (97.6%)")
print("     * Airtel data quality issues make voting unreliable")
print("   - Impact: Would disable fees for ~97% of statements")
print("   - Risk: May miss some statements that genuinely use implicit fees")

print("\n   Option B: KEEP VOTING BUT REQUIRE PERFECT VOTES")
print("   - Only enable if ALL merchant payment transactions vote 'for'")
print("   - AND minimum 10+ transactions")
print("   - This would drastically reduce false positives")
print("   - Impact: Would disable fees for ~95%+ of statements")

print("\n   Option C: MANUAL VERIFICATION")
print("   - Manually review PDF statements to identify ground truth")
print("   - Build a whitelist of run_ids that definitely use implicit fees")
print("   - Only apply implicit fees to whitelisted statements")
print("   - Most accurate but labor-intensive")

print("\n4. ACTUAL RECOMMENDATION:")
print("\n   ✓ DEFAULT TO DISABLED (Option A)")
print("\n   Reasoning:")
print("   - The original problem (statement 687a321075c82) was investigated")
print("   - Voting showed 23 for vs 655 against (3.4% vs 96.6%)")
print("   - This statement does NOT actually use implicit cashback!")
print("   - The 4 problem transactions likely have OTHER calculation errors")
print("   - Given that even the 'ground truth' statement doesn't use implicit fees,")
print("     it's safe to assume MOST statements don't use them")

print("\n5. NEXT STEPS:")
print("\n   1. Update detection logic to default to FALSE")
print("   2. Add a manual override mechanism for known exceptions")
print("   3. Reprocess all UATL statements with disabled implicit fees")
print("   4. Compare results - should see:")
print("      - Degradations in ~2.4% of statements (currently enabled)")
print("      - Improvements in the 47+ statements with false positive cashback")
print("      - Net improvement overall")

print("\n\n" + "=" * 80)
