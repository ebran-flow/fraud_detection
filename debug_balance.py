"""Debug balance calculation."""
import pdfplumber
import pandas as pd
from datetime import datetime

EXPECTED_DT_FORMATS = ['%d-%m-%y %H:%M %p', '%d-%m-%y %H:%M']

def parse_date_string(date_str, formats):
    """Parse date string using multiple formats."""
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None

def is_valid_date(value):
    """Check if a value is a valid date."""
    if not value:
        return False
    try:
        parsed_date = parse_date_string(str(value).strip(), EXPECTED_DT_FORMATS)
        return parsed_date is not None
    except Exception:
        return False

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/statements/68babf7f23139.pdf"

with pdfplumber.open(pdf_path) as pdf:
    pages = pdf.pages
    all_rows = []
    header = ['txn_id', 'txn_date', 'description', 'status', 'amount', 'txn_direction', 'fee', 'balance']

    for page in pages:
        tables = page.extract_tables()
        for table in tables:
            all_rows.extend(table)

    valid_rows = [row for row in all_rows if len(row) >= 8 and is_valid_date(row[1])]

    print(f"Total valid rows: {len(valid_rows)}")
    print("\n=== First 3 transactions ===")
    for i, row in enumerate(valid_rows[:3]):
        print(f"{i}: {row}")

    print("\n=== Last 3 transactions ===")
    for i, row in enumerate(valid_rows[-3:]):
        print(f"{len(valid_rows) - 3 + i}: {row}")

    df = pd.DataFrame(valid_rows, columns=header)

    # Clean data
    df['txn_date'] = df['txn_date'].apply(lambda x: parse_date_string(str(x).strip(), EXPECTED_DT_FORMATS))
    df['amount'] = df['amount'].astype(str).str.replace(',', '').str.strip()
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df['fee'] = df['fee'].astype(str).str.replace(',', '').str.strip()
    df['fee'] = pd.to_numeric(df['fee'], errors='coerce').fillna(0)
    df['balance'] = df['balance'].astype(str).str.replace(',', '').str.strip()
    df['balance'] = pd.to_numeric(df['balance'], errors='coerce')

    df = df.sort_values('txn_date').reset_index(drop=True)

    print("\n=== After sorting by date ===")
    print(f"First 3 rows:")
    print(df[['txn_date', 'amount', 'txn_direction', 'balance']].head(3))
    print(f"\nLast 3 rows:")
    print(df[['txn_date', 'amount', 'txn_direction', 'balance']].tail(3))

    first_balance = df.iloc[0]['balance']
    first_amount = df.iloc[0]['amount']
    first_fee = df.iloc[0]['fee']
    first_direction = df.iloc[0]['txn_direction'].lower()

    if first_direction == 'credit':
        opening_balance = first_balance - first_amount - first_fee
    else:
        opening_balance = first_balance + first_amount + first_fee

    credits = df[df['txn_direction'].str.lower() == 'credit']['amount'].sum()
    debits = df[df['txn_direction'].str.lower() == 'debit']['amount'].sum()

    closing_balance_from_stmt = df.iloc[-1]['balance']
    calculated_closing_balance = opening_balance + credits - debits

    print(f"\n=== Calculation Summary ===")
    print(f"Opening balance: {opening_balance}")
    print(f"Total credits: {credits}")
    print(f"Total debits: {debits}")
    print(f"Calculated closing: {calculated_closing_balance}")
    print(f"Statement closing: {closing_balance_from_stmt}")
    print(f"Match: {abs(calculated_closing_balance - closing_balance_from_stmt) < 0.01}")
