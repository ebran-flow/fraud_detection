#!/usr/bin/env python3
"""Quick test to verify the fix for same-timestamp transactions."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_statements import extract_data_from_pdf, calculate_running_balance

pdf_path = '/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL_extracted/68b5699446f1e.pdf'

print("Processing PDF...")
df, acc = extract_data_from_pdf(pdf_path)

print(f"Extracted {len(df)} transactions")

print("\nCalculating running balance...")
df_balanced = calculate_running_balance(df)

# Find the problematic transactions
problem_txns = df_balanced[df_balanced['txn_id'].isin(['124516913567', '124516830980'])]

print('\nProblem transactions after fix:')
print(problem_txns[['txn_id', 'txn_date', 'balance', 'calculated_running_balance', 'balance_diff', 'balance_diff_change_count']].to_string(index=False))

# Check balance_diff_change_count max
max_changes = df_balanced['balance_diff_change_count'].max()
print(f'\nMax balance_diff_change_count: {max_changes}')

# Save the fixed detailed sheet
output_path = '/home/ebran/Developer/projects/data_score_factors/fraud_detection/detailed_sheets/68b5699446f1e_detailed.csv'
df_balanced.to_csv(output_path, index=False)
print(f'\nSaved to {output_path}')
