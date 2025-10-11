"""Debug format 2 balance calculation."""
import sys
sys.path.insert(0, '/home/ebran/Developer/projects/data_score_factors/fraud_detection')

from process_statements import extract_data_from_pdf

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/uploaded_pdfs/682c8f6fcefaa.pdf"

df, acc_number = extract_data_from_pdf(pdf_path)

print(f"Account: {acc_number}")
print(f"Total transactions: {len(df)}")
print(f"\nFirst 5 transactions:")
print(df.head()[['txn_date', 'amount', 'txn_direction', 'fee', 'balance']])
print(f"\nLast 5 transactions:")
print(df.tail()[['txn_date', 'amount', 'txn_direction', 'fee', 'balance']])

# Calculate totals
credits = df[df['txn_direction'].str.lower() == 'credit']['amount'].sum()
debits = df[df['txn_direction'].str.lower() == 'debit']['amount'].sum()
fees = df['fee'].sum()

print(f"\nSummary:")
print(f"Credits: {credits:,.0f}")
print(f"Debits: {debits:,.0f}")
print(f"Fees: {fees:,.0f}")

# First and last balance
print(f"\nFirst balance: {df.iloc[0]['balance']:,.0f}")
print(f"Last balance: {df.iloc[-1]['balance']:,.0f}")

# Try to calculate opening balance
first_balance = df.iloc[0]['balance']
first_amount = df.iloc[0]['amount']
first_fee = df.iloc[0]['fee']
first_direction = df.iloc[0]['txn_direction'].lower()

print(f"\nFirst transaction:")
print(f"  Balance after: {first_balance:,.0f}")
print(f"  Amount: {first_amount:,.0f}")
print(f"  Fee: {first_fee:,.0f}")
print(f"  Direction: {first_direction}")

if first_direction == 'credit':
    opening = first_balance - first_amount - first_fee
else:
    opening = first_balance + first_amount + first_fee

print(f"  Calculated opening: {opening:,.0f}")
print(f"\nCalculated closing: {opening + credits - debits:,.0f}")
