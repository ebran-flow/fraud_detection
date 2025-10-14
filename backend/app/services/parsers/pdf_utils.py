"""
PDF Parsing Utilities for Airtel Money Statements
Extracted from process_statements.py for use in parsers
"""
import re
import logging
import pandas as pd
import pdfplumber
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Expected date formats (use %I for 12-hour format with AM/PM)
EXPECTED_DT_FORMATS = [
    '%d-%m-%y %I:%M %p',  # Format 1: 31-08-25 11:14 PM
    '%d-%m-%y %H:%M',      # Format 1: 31-08-25 23:14
    '%Y-%m-%d\n%H:%M:%S',  # Format 2: 2025-02-01\n07:16:11
    '%Y-%m-%d %H:%M:%S'    # Format 2: 2025-02-01 07:16:11
]


def is_header_row(row: List[str]) -> bool:
    """
    Detect if a row is a header row (indicates manipulation).

    Header rows contain column names like:
    - "Date", "Transaction ID", "Transaction Type", "Description", etc.
    - "Transation ID" (typo in Format 2)

    Returns:
        True if this is a header row that should be skipped
    """
    if not row or len(row) < 3:
        return False

    # Convert row to string for checking
    row_str = ' '.join([str(cell) for cell in row if cell]).lower()

    # Header keywords
    header_keywords = [
        'transaction id',
        'transation id',  # Airtel's typo
        'transaction type',
        'transaction date',
        'credit/debit',
        'transaction amount',
    ]

    # Check if row contains multiple header keywords
    keyword_count = sum(1 for keyword in header_keywords if keyword in row_str)

    # If 2 or more header keywords are present, it's likely a header row
    if keyword_count >= 2:
        return True

    # Additional checks for specific column values
    # Check if any cell contains header-specific values
    for cell in row:
        cell_str = str(cell).strip().lower()
        if cell_str in ['date', 'description', 'status', 'amount', 'fee', 'balance',
                        'from', 'to', 'credit/debit', 'transaction amount']:
            # Single exact match of column name indicates header
            return True

    return False


def parse_date_string(date_str: str, formats: List[str]) -> Optional[datetime]:
    """Parse date string using multiple formats."""
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def detect_pdf_format(page) -> int:
    """Detect which Airtel format the PDF uses."""
    extracted_text = page.extract_text()

    # Format 2 has "USER STATEMENT" as title
    if 'USER STATEMENT' in extracted_text:
        return 2
    # Format 1 has "AIRTEL MONEY STATEMENT"
    elif 'AIRTEL MONEY STATEMENT' in extracted_text:
        return 1

    # Fallback: check table structure
    tables = page.extract_tables()
    if tables and len(tables[0]) > 0:
        header = tables[0][0]
        # Format 2 has 'Transation ID' (typo in their PDF)
        if 'Transation ID' in header or 'Transaction Type' in header:
            return 2
        # Format 1 has 'Credit/Debit'
        elif 'Credit/Debit' in header or 'Transaction Amount' in header:
            return 1

    return 1  # Default to format 1


def extract_account_number(page, pdf_format: int = 1) -> Optional[str]:
    """Extract account number from PDF page."""
    extracted_text = page.extract_text()

    if pdf_format == 2:
        # Format 2: "Mobile Number : 256706015809" (with country code)
        # Extract last 9 digits
        pattern = re.compile(r'Mobile Number\s*:\s*(?:256)?(\d{9})', re.I)
        match = pattern.search(extracted_text)
        if match:
            return match.group(1)

    # Format 1: "Mobile Number: 752902485"
    acc_number_pattern = re.compile(r'Mobile Number\s*:.*?(\b\d{9}\b)', re.S | re.I)
    acc_number_match = acc_number_pattern.search(extracted_text)

    if acc_number_match:
        return acc_number_match.group(1)
    else:
        # Alternative pattern - find any 9-digit number
        acc_number_pattern = re.compile(r'(\b\d{9}\b)')
        matches = acc_number_pattern.findall(extracted_text)
        if matches:
            return matches[0]

    logger.warning("Account number not found in statement")
    return None


def extract_requestor_email(page, pdf_format: int = 1) -> Optional[str]:
    """
    Extract requestor email address from PDF page (Airtel format 1 only).
    The email is typically under 'Email Address:' section, after Customer Name and Mobile Number.
    """
    if pdf_format != 1:
        # Only format 1 has requestor email
        return None

    extracted_text = page.extract_text()

    # Pattern to extract email address (case-insensitive)
    # Look for "Email Address:" followed by the email
    email_pattern = re.compile(r'Email\s+Address\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.I)
    match = email_pattern.search(extracted_text)

    if match:
        return match.group(1)

    # Alternative: search for any email pattern in the header section
    # (in case the label format is different)
    general_email_pattern = re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b')
    matches = general_email_pattern.findall(extracted_text)

    if matches:
        # Return the first email found (typically the requestor)
        return matches[0]

    logger.debug("Requestor email not found in statement")
    return None


def extract_customer_name(page, pdf_format: int = 1) -> Optional[str]:
    """
    Extract customer name from PDF page (Airtel format 1 only).
    """
    if pdf_format != 1:
        return None

    extracted_text = page.extract_text()

    # Pattern: "Customer Name:" followed by the name
    pattern = re.compile(r'Customer\s+Name\s*:\s*(.+?)(?:\n|Mobile Number)', re.I | re.S)
    match = pattern.search(extracted_text)

    if match:
        name = match.group(1).strip()
        # Clean up any extra whitespace
        name = re.sub(r'\s+', ' ', name)
        return name

    logger.debug("Customer name not found in statement")
    return None


def extract_mobile_number(page, pdf_format: int = 1) -> Optional[str]:
    """
    Extract mobile number from PDF page (Airtel format 1 only).
    This extracts from the header section, not the account number field.
    """
    if pdf_format != 1:
        return None

    extracted_text = page.extract_text()

    # Pattern: "Mobile Number:" followed by the number
    pattern = re.compile(r'Mobile\s+Number\s*:\s*(\d+)', re.I)
    match = pattern.search(extracted_text)

    if match:
        return match.group(1).strip()

    logger.debug("Mobile number not found in statement header")
    return None


def extract_statement_period(page, pdf_format: int = 1) -> Optional[str]:
    """
    Extract statement period from PDF page (Airtel format 1 only).
    Example: "01-Sep-2025 to 30-Sep-2025"
    """
    if pdf_format != 1:
        return None

    extracted_text = page.extract_text()

    # Pattern: "Statement Period:" followed by the date range
    pattern = re.compile(r'Statement\s+Period\s*:\s*(.+?)(?:\n|Request Date)', re.I | re.S)
    match = pattern.search(extracted_text)

    if match:
        period = match.group(1).strip()
        # Clean up any extra whitespace or newlines
        period = re.sub(r'\s+', ' ', period)
        return period

    logger.debug("Statement period not found in statement")
    return None


def extract_request_date(page, pdf_format: int = 1) -> Optional[datetime]:
    """
    Extract request date from PDF page (Airtel format 1 only).
    Returns datetime object.
    """
    if pdf_format != 1:
        return None

    extracted_text = page.extract_text()

    # Pattern: "Request Date:" followed by the date
    pattern = re.compile(r'Request\s+Date\s*:\s*(.+?)(?:\n|$)', re.I)
    match = pattern.search(extracted_text)

    if match:
        date_str = match.group(1).strip()
        # Clean up
        date_str = re.sub(r'\s+', ' ', date_str)

        # Try to parse the date - common formats for request date
        date_formats = [
            '%d-%b-%Y',      # 01-Sep-2025
            '%d-%m-%Y',      # 01-09-2025
            '%Y-%m-%d',      # 2025-09-01
            '%d/%m/%Y',      # 01/09/2025
            '%d %B %Y',      # 01 September 2025
            '%d %b %Y',      # 01 Sep 2025
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse request date: {date_str}")
        return None

    logger.debug("Request date not found in statement")
    return None


def is_valid_date(value: Any) -> bool:
    """Check if a value is a valid date."""
    if not value:
        return False
    try:
        parsed_date = parse_date_string(str(value).strip(), EXPECTED_DT_FORMATS)
        return parsed_date is not None
    except Exception:
        return False


def clean_dataframe(df: pd.DataFrame, pdf_format: int = 1) -> Tuple[pd.DataFrame, int]:
    """
    Clean and convert DataFrame datatypes.
    - Parses dates
    - Converts numeric columns (amount, fee, balance)
    - Cleans text columns and removes newlines from descriptions

    Returns:
        Tuple[pd.DataFrame, int]: Cleaned dataframe and count of quality issues found
    """
    # Parse dates
    df['txn_date'] = df['txn_date'].apply(lambda x: parse_date_string(str(x).strip(), EXPECTED_DT_FORMATS))

    # Clean numeric columns
    # For Format 2, keep the sign in amounts; for Format 1, strip it
    # Clean amount column with quality issue tracking
    df['amount'] = df['amount'].astype(str).str.replace(',', '').str.strip()

    # Replace empty strings with '0' before further processing
    df['amount'] = df['amount'].replace(['', 'nan', 'None'], '0')

    # Store raw amount before cleaning (for audit trail)
    df['amount_raw'] = df['amount'].copy()

    # Clean up malformed signs (like -+1500000 or +-1500000)
    # Keep only the first sign if multiple signs exist
    df['amount'] = df['amount'].str.replace(r'^([+-])([+-]+)', r'\1', regex=True)

    # Use regex to extract valid numeric values
    if pdf_format == 1:
        # Format 1: Extract unsigned number
        df['amount'] = df['amount'].str.extract(r'^([+\-]?)(\d+(?:\.\d+)?)', expand=False)[1]
    else:
        # Format 2: Extract signed number (keep the sign)
        df['amount'] = df['amount'].str.extract(r'^([+-]?\d+(?:\.\d+)?)', expand=False)

    # Check for failed extractions before conversion
    failed_extractions = df[df['amount'].isna()]
    if not failed_extractions.empty:
        logger.error(f"Failed to extract amount for {len(failed_extractions)} rows")
        for idx, row in failed_extractions.iterrows():
            logger.error(f"  Row {idx}: amount_raw='{row['amount_raw']}', txn_id={row.get('txn_id', 'N/A')}, description={row.get('description', 'N/A')}")
        raise ValueError(f"Amount extraction failed for {len(failed_extractions)} transactions. Check logs for details.")

    # Mark rows with amount quality issues
    df['has_amount_quality_issue'] = (df['amount_raw'] != df['amount']) & df['amount'].notna()

    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    df['fee'] = df['fee'].astype(str).str.replace(',', '').str.strip()

    # Store raw fee and balance before cleaning (for detecting overlap issues)
    df['fee_raw'] = df['fee'].copy()
    df['balance'] = df['balance'].astype(str).str.replace(',', '').str.strip()

    # Replace empty strings with '0' before further processing
    df['balance'] = df['balance'].replace(['', 'nan', 'None'], '0')

    # Store raw balance before cleaning (for audit trail)
    df['balance_raw'] = df['balance'].copy()

    # Detect and fix overlapping fee/balance columns
    # Pattern: fee contains very large number (>1M) AND balance starts with dot
    # Example: fee='8502200500' balance='.02052102.03' should be fee='0' balance='252102.03'
    overlap_mask = (
        (pd.to_numeric(df['fee'], errors='coerce') > 1000000) &
        (df['balance'].str.startswith('.'))
    )

    if overlap_mask.any():
        logger.warning(f"Detected {overlap_mask.sum()} rows with overlapping fee/balance columns")
        for idx in df[overlap_mask].index:
            fee_val = df.at[idx, 'fee']
            balance_val = df.at[idx, 'balance']

            # Reconstruct the correct balance from fee + balance overlap
            # fee='8502200500' + balance='.02052102.03' = '8502200500.02052102.03'
            # We need to extract the correct balance by finding the pattern
            combined = fee_val + balance_val

            # Try to extract a reasonable balance (between 0 and 100M typically)
            # Look for pattern: extract last valid amount from combined string
            balance_match = re.search(r'(\d{1,9}\.?\d{0,2})$', combined)
            if balance_match:
                corrected_balance = balance_match.group(1)
                df.at[idx, 'balance'] = corrected_balance
                df.at[idx, 'fee'] = '0'
                df.at[idx, 'has_quality_issue'] = 1
                logger.warning(f"  Row {idx}: Corrected overlap - fee_raw='{fee_val}', balance_raw='{balance_val}' -> fee='0', balance='{corrected_balance}'")

    df['fee'] = pd.to_numeric(df['fee'], errors='coerce').fillna(0)

    # Use regex to extract {sign(if applicable)}_{amount(numbers)} and remove the rest
    # Pattern: optional sign [+-]?, followed by digits with optional decimal
    df['balance'] = df['balance'].str.extract(r'^([+-]?\d+(?:\.\d+)?)', expand=False)

    # Mark rows with balance quality issues
    df['has_balance_quality_issue'] = (df['balance_raw'] != df['balance']) & df['balance'].notna()

    # Combined quality issue flag (either amount or balance has issues)
    df['has_quality_issue'] = df['has_amount_quality_issue'] | df['has_balance_quality_issue']

    # Count quality issues (rows with either amount or balance issues)
    quality_issues_count = int(df['has_quality_issue'].sum())

    df['balance'] = pd.to_numeric(df['balance'], errors='coerce')

    # Clean text columns
    df['description'] = df['description'].astype(str).str.strip()
    # Remove newlines from description to ensure consistent pattern matching
    df['description'] = df['description'].str.replace('\r\n', ' ', regex=False)
    df['description'] = df['description'].str.replace('\n', ' ', regex=False)
    df['description'] = df['description'].str.replace('\r', ' ', regex=False)
    # Clean up multiple spaces
    df['description'] = df['description'].str.replace(r'\s+', ' ', regex=True)
    df['description'] = df['description'].str.strip()

    df['txn_direction'] = df['txn_direction'].astype(str).str.strip()
    df['status'] = df['status'].astype(str).str.strip()
    df['txn_id'] = df['txn_id'].astype(str).str.strip()

    return df, quality_issues_count


def apply_format2_business_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply business rules for Format 2 Airtel statements:
    1. Filter out FAILED and ROLLBACKED transactions
    2. Handle reversal transactions
    3. Deduplicate commission disbursements
    4. Mark balance restart points
    5. Ensure stable sort for transactions with same datetime
    """
    if df.empty:
        return df

    initial_count = len(df)
    logger.info(f"Applying Format 2 business rules. Initial transactions: {initial_count}")

    # 1. Filter out FAILED and ROLLBACKED transactions
    df = df[~df['status'].str.upper().isin(['FAILED', 'ROLLBACKED'])].copy()
    filtered_count = initial_count - len(df)
    if filtered_count > 0:
        logger.info(f"Filtered out {filtered_count} FAILED/ROLLBACKED transactions")

    # 2. Identify reversal transactions (keep them, but log for tracking)
    reversals = df[df['description'].str.contains('Reversal', case=False, na=False)]
    if len(reversals) > 0:
        logger.info(f"Found {len(reversals)} reversal transactions (keeping them)")

    # 3. Deduplicate commission disbursements
    commission_mask = df['description'].str.contains('Commission', case=False, na=False)
    if commission_mask.any():
        commissions = df[commission_mask]
        dup_commissions = commissions[commissions.duplicated(subset=['txn_date', 'amount', 'balance'], keep='first')]
        if len(dup_commissions) > 0:
            logger.info(f"Found {len(dup_commissions)} duplicate commission disbursements")
            df = df[~df.index.isin(dup_commissions.index)]

    # 4. Mark balance restart points
    df['_balance_restart'] = False

    commission_disbursement_mask = (
        df['description'].str.contains('Commission', case=False, na=False) &
        df['description'].str.contains('Disbursement', case=False, na=False)
    )
    df.loc[commission_disbursement_mask, '_balance_restart'] = True
    commission_restart_count = commission_disbursement_mask.sum()

    dealloc_mask = df['description'].str.contains('Deallocation', case=False, na=False)
    df.loc[dealloc_mask, '_balance_restart'] = True
    dealloc_restart_count = dealloc_mask.sum()

    rollback_mask = df['description'].str.contains('RollBack', case=False, na=False)
    df.loc[rollback_mask, '_balance_restart'] = True
    rollback_restart_count = rollback_mask.sum()

    reversal_mask = df['description'].str.contains('Transaction Reversal', case=False, na=False)
    df.loc[reversal_mask, '_balance_restart'] = True
    reversal_restart_count = reversal_mask.sum()

    total_restart = df['_balance_restart'].sum()
    if total_restart > 0:
        logger.info(f"Marked {total_restart} balance restart points")

    # 5. Sort by date and amount sign
    def get_sort_key(row):
        if row['amount'] < 0:
            amount_sign = -1
        else:
            amount_sign = 1
        return (row['txn_date'], amount_sign, row['balance'])

    df['_sort_key'] = df.apply(lambda row: get_sort_key(row), axis=1)
    df = df.sort_values('_sort_key').reset_index(drop=True)
    df = df.drop(columns=['_sort_key'])

    df['_sequence'] = df.groupby('txn_date').cumcount()

    final_count = len(df)
    logger.info(f"After business rules: {final_count} transactions")

    return df


def _calculate_segmented_balance(df: pd.DataFrame, initial_opening_balance: float) -> float:
    """
    Calculate balance using segmented approach for Format 2 statements.
    Restarts balance calculation after Commission Disbursements, etc.
    """
    if df.empty:
        return 0

    restart_indices = df[df['_balance_restart']].index.tolist()

    if not restart_indices:
        return initial_opening_balance + df['amount'].sum()

    segments = []
    prev_end = -1

    for restart_idx in restart_indices:
        segment_start = prev_end + 1
        segment_end = restart_idx - 1

        if segment_end >= segment_start:
            segments.append((segment_start, segment_end, False))

        segments.append((restart_idx, restart_idx, True))
        prev_end = restart_idx

    if prev_end < len(df) - 1:
        segments.append((prev_end + 1, len(df) - 1, False))

    calculated_balance = initial_opening_balance

    for seg_start, seg_end, is_restart in segments:
        if is_restart:
            calculated_balance = df.iloc[seg_end]['balance']
        else:
            segment_amounts = df.iloc[seg_start:seg_end+1]['amount'].sum()
            calculated_balance = calculated_balance + segment_amounts

    return calculated_balance


def extract_data_from_pdf(pdf_path: str) -> Tuple[pd.DataFrame, Optional[str], int, int]:
    """
    Extract raw tabular data from Airtel PDF statement (handles both formats).

    Returns:
        pd.DataFrame: Raw transaction data with proper datatypes
        str: Account number from statement
        int: Count of rows with quality issues (balance data cleaning)
        int: Count of header rows found in data (manipulation indicator)
    """
    logger.info(f"Processing PDF: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages

            # Detect PDF format
            pdf_format = detect_pdf_format(pages[0])
            logger.info(f"Detected PDF format: {pdf_format}")

            # Extract account number
            acc_number = extract_account_number(pages[0], pdf_format)

            # Extract transaction tables
            all_rows = []
            header_rows_found = 0  # Track header rows (manipulation indicator)

            if pdf_format == 1:
                header = ['txn_id', 'txn_date', 'description', 'status',
                         'amount', 'txn_direction', 'fee', 'balance']

                for page in pages:
                    tables = page.extract_tables()
                    for table in tables:
                        all_rows.extend(table)

                # Filter out header rows and invalid rows
                valid_rows = []
                for row in all_rows:
                    if is_header_row(row):
                        header_rows_found += 1
                        logger.warning(f"Header row found in data (manipulation): {row[:3]}...")
                    elif len(row) >= 8 and is_valid_date(row[1]):
                        valid_rows.append(row)

            elif pdf_format == 2:
                for page in pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table[1:]:
                            # Check for header rows BEFORE date validation
                            if is_header_row(row):
                                header_rows_found += 1
                                logger.warning(f"Header row found in data (manipulation): {row[:3]}...")
                                continue

                            # Skip rows that don't meet basic requirements
                            if len(row) < 10:
                                continue

                            # Additional check: if amount column contains 'Amount', it's a header
                            if len(row) >= 8 and str(row[7]).strip().lower() == 'amount':
                                header_rows_found += 1
                                logger.warning(f"Header row found in data (amount='Amount'): {row[:3]}...")
                                continue

                            if is_valid_date(row[0]):
                                txn_date = row[0]
                                txn_id = row[1]
                                description = f"{row[2]} - {row[3]}"
                                status = row[6]
                                amount = row[7]
                                fee = row[8]
                                balance = row[9]

                                if amount and str(amount).strip():
                                    if str(amount).strip().startswith('+'):
                                        txn_direction = 'Credit'
                                    elif str(amount).strip().startswith('-'):
                                        txn_direction = 'Debit'
                                    else:
                                        txn_direction = 'Unknown'
                                else:
                                    txn_direction = 'Unknown'

                                amount_signed = str(amount).strip()

                                all_rows.append([txn_id, txn_date, description, status,
                                               amount_signed, txn_direction, fee, balance])

                header = ['txn_id', 'txn_date', 'description', 'status',
                         'amount', 'txn_direction', 'fee', 'balance']
                valid_rows = all_rows

            else:
                return pd.DataFrame(), acc_number, 0, 0

            if not valid_rows:
                logger.warning(f"No valid transaction rows found in {pdf_path}")
                return pd.DataFrame(), acc_number, 0, header_rows_found

            # Create DataFrame
            df = pd.DataFrame(valid_rows, columns=header)
            df['pdf_format'] = pdf_format

            # Clean and convert datatypes
            df, quality_issues_count = clean_dataframe(df, pdf_format=pdf_format)

            # Apply Format 2 business rules if applicable
            if pdf_format == 2:
                df = apply_format2_business_rules(df)
                if '_sequence' in df.columns:
                    df = df.drop(columns=['_sequence'])

            logger.info(f"Found {quality_issues_count} rows with balance quality issues")
            if header_rows_found > 0:
                logger.warning(f"Found {header_rows_found} header rows in transaction data (MANIPULATION INDICATOR)")
            return df, acc_number, quality_issues_count, header_rows_found

    except Exception as e:
        logger.error(f"Error extracting data from {pdf_path}: {e}")
        raise


def compute_balance_summary(df: pd.DataFrame, account_number: str, file_name: str) -> Dict[str, Any]:
    """
    Calculate balance summary and verify against statement.

    Returns:
        dict: Summary with balance verification
    """
    if df.empty:
        logger.warning(f"Empty dataframe for {file_name}")
        return {
            'account_number': account_number,
            'file_name': file_name,
            'balance_match': 'Failed',
            'opening_balance': 0,
            'credits': 0,
            'debits': 0,
            'fees': 0,
            'charges': 0,
            'calculated_closing_balance': 0,
            'stmt_closing_balance': 0,
            'error': 'No transactions found'
        }

    try:
        # Sort by transaction date and balance
        df['_sort_priority'] = df.apply(lambda row: (row['txn_date'], -1 if row['amount'] < 0 else 1, row['balance']), axis=1)
        df = df.sort_values('_sort_priority').reset_index(drop=True)
        df = df.drop(columns=['_sort_priority'])

        # Detect format
        pdf_format = df.iloc[0].get('pdf_format', 1)

        # Calculate opening balance
        first_balance = df.iloc[0]['balance']
        first_amount = df.iloc[0]['amount']
        first_fee = df.iloc[0]['fee']

        if pdf_format == 2:
            opening_balance = first_balance - first_amount

            total_signed_amounts = df['amount'].sum()
            fees = df['fee'].sum()
            charges = 0

            credits = df[df['amount'] > 0]['amount'].sum()
            debits = abs(df[df['amount'] < 0]['amount'].sum())

            if '_balance_restart' in df.columns and df['_balance_restart'].any():
                calculated_closing_balance = _calculate_segmented_balance(df, opening_balance)
            else:
                calculated_closing_balance = opening_balance + total_signed_amounts

        else:
            # Format 1
            first_direction = df.iloc[0]['txn_direction'].lower()

            if first_direction == 'credit':
                opening_balance = first_balance - first_amount - first_fee
            else:
                opening_balance = first_balance + first_amount + first_fee

            credits = df[df['txn_direction'].str.lower() == 'credit']['amount'].sum()
            debits = df[df['txn_direction'].str.lower() == 'debit']['amount'].sum()
            fees = df['fee'].sum()
            charges = 0

            if fees > 0:
                calc_with_fees = opening_balance + credits - debits - fees
                diff_with_fees = abs(calc_with_fees - df.iloc[-1]['balance'])

                calc_without_fees = opening_balance + credits - debits
                diff_without_fees = abs(calc_without_fees - df.iloc[-1]['balance'])

                if diff_with_fees < diff_without_fees:
                    calculated_closing_balance = calc_with_fees
                else:
                    calculated_closing_balance = calc_without_fees
            else:
                calculated_closing_balance = opening_balance + credits - debits

        closing_balance_from_stmt = df.iloc[-1]['balance']

        balance_diff = abs(calculated_closing_balance - closing_balance_from_stmt)
        balance_match = "Success" if balance_diff < 0.01 else "Failed"

        return {
            'account_number': account_number,
            'file_name': file_name,
            'balance_match': balance_match,
            'opening_balance': opening_balance,
            'credits': credits,
            'debits': debits,
            'fees': fees,
            'charges': charges,
            'calculated_closing_balance': calculated_closing_balance,
            'stmt_closing_balance': closing_balance_from_stmt,
            'balance_diff': balance_diff
        }

    except Exception as e:
        logger.error(f"Error computing balance summary: {e}")
        return {
            'account_number': account_number,
            'file_name': file_name,
            'balance_match': 'Failed',
            'error': str(e)
        }
