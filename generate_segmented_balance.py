"""
Generate balance analysis CSV with segmented calculation (restarting after commission disbursements)
"""
import pandas as pd
import numpy as np
from process_statements import extract_data_from_pdf

pdf_path = 'statements/682c8f6fcefaa.pdf'
df, acc_number = extract_data_from_pdf(pdf_path)

# Find commission disbursements
commission_mask = df['description'].str.contains('Commission', case=False, na=False) & \
                  df['description'].str.contains('Disbursement', case=False, na=False)
commission_indices = df[commission_mask].index.tolist()

print(f'Found {len(commission_indices)} commission disbursements at: {commission_indices}')

# Initialize calculated balance
df['calculated_balance'] = np.nan

# Process in segments
prev_end = -1

for comm_idx in commission_indices:
    segment_start = prev_end + 1
    segment_end = comm_idx

    segment_indices = list(range(segment_start, segment_end))

    if len(segment_indices) > 0:
        # Calculate for transactions before commission
        first_idx = segment_indices[0]
        opening = df.loc[first_idx, 'balance'] - df.loc[first_idx, 'amount']

        for idx in segment_indices:
            if idx == first_idx:
                df.loc[idx, 'calculated_balance'] = opening + df.loc[idx, 'amount']
            else:
                df.loc[idx, 'calculated_balance'] = df.loc[idx-1, 'calculated_balance'] + df.loc[idx, 'amount']

    # Skip commission row itself
    df.loc[comm_idx, 'calculated_balance'] = df.loc[comm_idx, 'balance']

    prev_end = comm_idx

# Handle final segment
if commission_indices:
    final_start = commission_indices[-1] + 1
else:
    final_start = 0

if final_start < len(df):
    opening = df.loc[final_start, 'balance'] - df.loc[final_start, 'amount']

    for idx in range(final_start, len(df)):
        if idx == final_start:
            df.loc[idx, 'calculated_balance'] = opening + df.loc[idx, 'amount']
        else:
            df.loc[idx, 'calculated_balance'] = df.loc[idx-1, 'calculated_balance'] + df.loc[idx, 'amount']

# Calculate differences
df['balance_diff'] = df['balance'] - df['calculated_balance']

# Select columns for output
output_df = df[['txn_date', 'txn_id', 'description', 'status', 'amount', 'fee',
                'balance', 'calculated_balance', 'balance_diff']].copy()

# Save full analysis
output_df.to_csv('results/format2_segmented_balance.csv', index=False)
print(f'Saved: results/format2_segmented_balance.csv')

# Statistics
print(f'\n=== Results ===')
print(f'Total transactions: {len(df)}')
print(f'Rows with zero diff: {(abs(df["balance_diff"]) < 0.01).sum()}')
print(f'Rows with non-zero diff: {(abs(df["balance_diff"]) >= 0.01).sum()}')
print(f'Max difference: {df["balance_diff"].abs().max():,.2f}')
