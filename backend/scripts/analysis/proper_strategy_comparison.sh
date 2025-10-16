#!/bin/bash
# Proper A/B/C comparison of implicit fee strategies
# Tests the SAME statements with all three strategies and compares metrics

set -e

source .env

echo "================================================================================"
echo "PROPER STRATEGY COMPARISON"
echo "================================================================================"
echo ""
echo "Performance Metrics:"
echo "1. Balance Match Success Rate (higher is better)"
echo "2. Avg Balance Diff Changes (lower is better)"
echo "3. Avg Balance Diff Change Ratio (lower is better)"
echo ""
echo "================================================================================"
echo ""

# Get baseline stats from Round 3 (Voting Algorithm - 10:1 ratio)
echo "BASELINE: Round 3 (Voting Algorithm - 10:1 ratio)"
echo "--------------------------------------------------------------------------------"

mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT
    'Voting (10:1)' as strategy,
    COUNT(*) as total_statements,
    SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) as success_count,
    ROUND(SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as success_rate_pct,
    ROUND(AVG(balance_diff_changes), 2) as avg_diff_changes,
    ROUND(AVG(balance_diff_change_ratio), 6) as avg_diff_ratio,
    SUM(uses_implicit_cashback = 1) as cashback_enabled_count,
    SUM(uses_implicit_ind02_commission = 1) as ind02_enabled_count
FROM summary s
JOIN metadata m ON s.run_id = m.run_id
WHERE m.acc_prvdr_code = 'UATL'
AND s.uses_implicit_cashback IS NOT NULL;
" 2>/dev/null

echo ""
echo ""
echo "================================================================================"
echo "QUESTION: What would happen with different strategies?"
echo "================================================================================"
echo ""
echo "To answer this, we need to:"
echo "1. Select a representative sample of statements"
echo "2. Reprocess each with Strategy A (voting), B (always disable), C (always enable)"
echo "3. Compare success rates and diff changes for THE SAME statements"
echo ""
echo "However, this requires:"
echo "- Modifying the detection functions to force enable/disable"
echo "- Reprocessing thousands of statements 3 times"
echo "- Several hours of compute time"
echo ""
echo "================================================================================"
echo "ALTERNATIVE: Analyze what we know from degradations"
echo "================================================================================"
echo ""

# Analyze degradations from Round 2 (many false positives)
echo "Evidence from Round 2 → Round 3 degradations:"
echo ""
echo "Round 2 had 79 degradations (2:1 ratio, 98.2% cashback enabled)"
echo "Round 3 had 2 degradations (10:1 ratio, 97.6% cashback enabled)"
echo ""
echo "This suggests:"
echo "- Stricter voting thresholds reduce false positives"
echo "- But even 10:1 ratio still enables cashback for 97.6% of statements"
echo "- Expected real-world prevalence should be ~5-10% based on business logic"
echo ""

# Show the breakdown by flags
echo ""
echo "Current breakdown by implicit fee flags:"
echo "--------------------------------------------------------------------------------"

mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT
    CASE WHEN uses_implicit_cashback = 1 THEN 'Enabled' ELSE 'Disabled' END as cashback,
    CASE WHEN uses_implicit_ind02_commission = 1 THEN 'Enabled' ELSE 'Disabled' END as ind02,
    COUNT(*) as count,
    SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) as success,
    ROUND(SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as success_pct,
    ROUND(AVG(balance_diff_changes), 2) as avg_diff_changes,
    ROUND(AVG(balance_diff_change_ratio), 6) as avg_diff_ratio
FROM summary s
JOIN metadata m ON s.run_id = m.run_id
WHERE m.acc_prvdr_code = 'UATL'
AND s.uses_implicit_cashback IS NOT NULL
GROUP BY uses_implicit_cashback, uses_implicit_ind02_commission
ORDER BY uses_implicit_cashback DESC, uses_implicit_ind02_commission DESC;
" 2>/dev/null

echo ""
echo ""
echo "⚠️  WARNING: The breakdown above shows CORRELATION, not CAUSATION!"
echo ""
echo "The voting algorithm CHOSE which statements get cashback enabled/disabled."
echo "High success rate for disabled cashback might mean the algorithm correctly"
echo "identified those statements, NOT that disabling cashback universally is better."
echo ""
echo "================================================================================"
echo "RECOMMENDATION"
echo "================================================================================"
echo ""
echo "Based on the evidence we have:"
echo ""
echo "1. The voting algorithm enables cashback for 97.6% of statements"
echo "   - This is unrealistically high for a special-case business rule"
echo "   - Expected prevalence should be much lower (~5-10%)"
echo ""
echo "2. Statement 687a321075c82 (original problem case) analysis:"
echo "   - 23 votes FOR cashback (3.4%)"
echo "   - 655 votes AGAINST cashback (96.6%)"
echo "   - Conclusion: Does NOT use implicit cashback"
echo "   - The 4 problem transactions have OTHER calculation errors"
echo ""
echo "3. Degradation analysis shows:"
echo "   - 45-47 statements in Round 2 had '+3' pattern (3 merchant payments"
echo "     incorrectly receiving cashback)"
echo "   - This is a false positive pattern"
echo ""
echo "NEXT STEP OPTIONS:"
echo ""
echo "Option 1: Default to DISABLED and test"
echo "  - Change detection to return False by default"
echo "  - Reprocess all statements (Round 4)"
echo "  - Compare Round 4 vs Round 3 metrics"
echo "  - Pros: Simple, fast to test"
echo "  - Cons: May degrade some statements that genuinely need implicit fees"
echo ""
echo "Option 2: Do proper A/B/C testing on a sample"
echo "  - Select 1000 representative statements"
echo "  - Reprocess with all 3 strategies"
echo "  - Compare metrics directly"
echo "  - Pros: Definitive answer"
echo "  - Cons: Requires code changes + hours of compute time"
echo ""
echo "Option 3: Manual verification"
echo "  - Review PDF statements manually to identify ground truth"
echo "  - Create whitelist of run_ids that actually use implicit fees"
echo "  - Apply implicit fees only to whitelisted statements"
echo "  - Pros: Most accurate"
echo "  - Cons: Very labor-intensive"
echo ""
echo "================================================================================"
