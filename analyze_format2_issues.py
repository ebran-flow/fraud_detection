"""Analyze Format 2 for business rule issues."""
import sys
sys.path.insert(0, '/home/ebran/Developer/projects/data_score_factors/fraud_detection')

from process_statements import extract_data_from_pdf
import pandas as pd

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/uploaded_pdfs/682c8f6fcefaa.pdf"

df, acc_number = extract_data_from_pdf(pdf_path)

print(f"Total transactions: {len(df)}\n")

# 1. Check for failed transactions
print("=== FAILED TRANSACTIONS ===")
failed = df[df['status'].str.upper() == 'FAILED']
print(f"Failed transactions: {len(failed)}")
if len(failed) > 0:
    print(failed[['txn_date', 'description', 'amount', 'status', 'balance']].head())

# 2. Check for reversals
print("\n=== REVERSAL TRANSACTIONS ===")
reversals = df[df['description'].str.contains('Revers', case=False, na=False)]
print(f"Reversal transactions: {len(reversals)}")
if len(reversals) > 0:
    print(reversals[['txn_date', 'description', 'amount', 'status', 'balance']].head(10))

# 3. Check for duplicate datetimes
print("\n=== DUPLICATE DATETIMES ===")
dup_times = df[df.duplicated('txn_date', keep=False)]
print(f"Transactions with duplicate datetimes: {len(dup_times)}")
if len(dup_times) > 0:
    print("Sample:")
    sample_time = dup_times.iloc[0]['txn_date']
    same_time = df[df['txn_date'] == sample_time]
    print(same_time[['txn_date', 'txn_id', 'description', 'amount', 'balance']])

# 4. Check for commission disbursements
print("\n=== COMMISSION DISBURSEMENT ===")
commissions = df[df['description'].str.contains('commission', case=False, na=False)]
print(f"Commission transactions: {len(commissions)}")
if len(commissions) > 0:
    print(commissions[['txn_date', 'txn_id', 'description', 'amount', 'balance']].head(20))

# 5. Check status distribution
print("\n=== STATUS DISTRIBUTION ===")
print(df['status'].value_counts())

# 6. Check unique descriptions
print("\n=== UNIQUE TRANSACTION TYPES (first 30) ===")
unique_desc = df['description'].str.split(' - ').str[0].unique()
for i, desc in enumerate(unique_desc[:30]):
    print(f"{i+1}. {desc}")
