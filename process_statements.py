"""
Automated parsing, validation, and summary generation for Airtel statements.
"""
import os
import re
import pandas as pd
import pdfplumber
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
STATEMENTS_PATH = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/statements/"
MAPPER_PATH = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/mapper.csv"
OUTPUT_PATH = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/results/balance_summary.csv"

# Expected date formats (use %I for 12-hour format with AM/PM)
EXPECTED_DT_FORMATS = [
    '%d-%m-%y %I:%M %p',  # Format 1: 31-08-25 11:14 PM
    '%d-%m-%y %H:%M',      # Format 1: 31-08-25 23:14
    '%Y-%m-%d\n%H:%M:%S',  # Format 2: 2025-02-01\n07:16:11
    '%Y-%m-%d %H:%M:%S'    # Format 2: 2025-02-01 07:16:11
]


def parse_date_string(date_str, formats):
    """Parse date string using multiple formats."""
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def detect_pdf_format(page):
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


def extract_account_number(page, pdf_format=1):
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


def extract_data_from_pdf(pdf_path):
    """
    Extract raw tabular data from Airtel PDF statement (handles both formats).

    Returns:
        pd.DataFrame: Raw transaction data with proper datatypes
        str: Account number from statement
    """
    logger.info(f"Processing PDF: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages

            # Detect PDF format
            pdf_format = detect_pdf_format(pages[0])
            logger.info(f"Detected PDF format: {pdf_format}")

            # Extract account number from first page
            acc_number = extract_account_number(pages[0], pdf_format)

            # Extract transaction tables from all pages
            all_rows = []

            if pdf_format == 1:
                # Format 1: Transaction ID, Transaction Date, Description, Status, Transaction Amount, Credit/Debit, Fee, Balance
                header = ['txn_id', 'txn_date', 'description', 'status',
                         'amount', 'txn_direction', 'fee', 'balance']

                for page in pages:
                    tables = page.extract_tables()
                    for table in tables:
                        all_rows.extend(table)

                # Filter valid transaction rows (those with valid dates)
                valid_rows = [row for row in all_rows if len(row) >= 8 and is_valid_date(row[1])]

            elif pdf_format == 2:
                # Format 2: Date, Transaction ID, Transaction Type, Description, From, To, Status, Amount, Fee, Balance
                # Map to standard format: txn_id, txn_date, description, status, amount, txn_direction, fee, balance
                # Note: Amount is SIGNED in Format 2 (+credit, -debit)
                for page in pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table[1:]:  # Skip header row
                            if len(row) >= 10 and is_valid_date(row[0]):
                                # Map format 2 columns to standard format
                                # Row structure: [Date, TxnID, TxnType, Description, From, To, Status, Amount, Fee, Balance]
                                txn_date = row[0]  # Date
                                txn_id = row[1]  # Transaction ID
                                description = f"{row[2]} - {row[3]}"  # Transaction Type + Description
                                status = row[6]  # Status
                                amount = row[7]  # Amount (with sign: +credit, -debit)
                                fee = row[8]  # Fee
                                balance = row[9]  # Balance

                                # Determine direction from amount sign
                                if amount and str(amount).strip():
                                    if str(amount).strip().startswith('+'):
                                        txn_direction = 'Credit'
                                    elif str(amount).strip().startswith('-'):
                                        txn_direction = 'Debit'
                                    else:
                                        txn_direction = 'Unknown'
                                else:
                                    txn_direction = 'Unknown'

                                # Keep the signed amount for Format 2 (don't strip sign)
                                amount_signed = str(amount).strip()

                                all_rows.append([txn_id, txn_date, description, status,
                                               amount_signed, txn_direction, fee, balance])

                header = ['txn_id', 'txn_date', 'description', 'status',
                         'amount', 'txn_direction', 'fee', 'balance']
                valid_rows = all_rows

            else:
                return pd.DataFrame(), acc_number

            if not valid_rows:
                logger.warning(f"No valid transaction rows found in {pdf_path}")
                return pd.DataFrame(), acc_number

            # Create DataFrame
            df = pd.DataFrame(valid_rows, columns=header)

            # Add format column for downstream processing
            df['pdf_format'] = pdf_format

            # Clean and convert datatypes
            df = clean_dataframe(df, pdf_format=pdf_format)

            # Apply Format 2 business rules if applicable
            if pdf_format == 2:
                df = apply_format2_business_rules(df)
                # Remove the sequence column before returning
                if '_sequence' in df.columns:
                    df = df.drop(columns=['_sequence'])

            return df, acc_number

    except Exception as e:
        logger.error(f"Error extracting data from {pdf_path}: {e}")
        raise


def is_valid_date(value):
    """Check if a value is a valid date."""
    if not value:
        return False
    try:
        parsed_date = parse_date_string(str(value).strip(), EXPECTED_DT_FORMATS)
        return parsed_date is not None
    except Exception:
        return False


def apply_format2_business_rules(df):
    """
    Apply business rules for Format 2 Airtel statements:
    1. Filter out FAILED and ROLLBACKED transactions
    2. Handle reversal transactions
    3. Deduplicate commission disbursements
    4. Mark balance restart points (Commission Disbursements, Deallocation Transfers, Rollbacks, Transaction Reversals)
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

    # 4. Mark balance restart points for segmented calculation
    # These transactions cause balance recalculation to restart from the statement balance
    df['_balance_restart'] = False

    # Commission disbursements restart balance calculation
    # Use regex with DOTALL flag to match across newlines
    commission_disbursement_mask = (
        df['description'].str.contains('Commission', case=False, na=False) &
        df['description'].str.contains('Disbursement', case=False, na=False)
    )
    df.loc[commission_disbursement_mask, '_balance_restart'] = True
    commission_restart_count = commission_disbursement_mask.sum()

    # Deallocation transfers restart balance calculation
    dealloc_mask = df['description'].str.contains('Deallocation', case=False, na=False)
    df.loc[dealloc_mask, '_balance_restart'] = True
    dealloc_restart_count = dealloc_mask.sum()

    # Rollback transactions restart balance calculation
    rollback_mask = df['description'].str.contains('RollBack', case=False, na=False)
    df.loc[rollback_mask, '_balance_restart'] = True
    rollback_restart_count = rollback_mask.sum()

    # Transaction Reversal restart balance calculation
    reversal_mask = df['description'].str.contains('Transaction Reversal', case=False, na=False)
    df.loc[reversal_mask, '_balance_restart'] = True
    reversal_restart_count = reversal_mask.sum()

    total_restart = df['_balance_restart'].sum()
    if total_restart > 0:
        logger.info(f"Marked {total_restart} balance restart points: {commission_restart_count} commissions, {dealloc_restart_count} deallocations, {rollback_restart_count} rollbacks, {reversal_restart_count} reversals")

    # 5. Sort by date and determine correct order for same-timestamp transactions
    # For same timestamp, use balance to infer order:
    # - For credits: lower balance came first (balance increases)
    # - For debits: higher balance came first (balance decreases)
    # - For mixed credit/debit: sort by amount sign (debits first, then credits)

    # Add a sorting key that handles this logic
    # For Format 2: amount is signed (negative=debit, positive=credit)
    # For same timestamp, sort by: (txn_date, amount_sign, balance)
    # This ensures debits come before credits, and within each type, chronological order is preserved

    def get_sort_key(row):
        # Amount sign: -1 for debit (process first), +1 for credit (process second)
        if row['amount'] < 0:  # Debit (Format 2) or checking txn_direction
            amount_sign = -1
        else:
            amount_sign = 1
        return (row['txn_date'], amount_sign, row['balance'])

    # Sort by the compound key
    df['_sort_key'] = df.apply(lambda row: get_sort_key(row), axis=1)
    df = df.sort_values('_sort_key').reset_index(drop=True)
    df = df.drop(columns=['_sort_key'])

    df['_sequence'] = df.groupby('txn_date').cumcount()

    final_count = len(df)
    logger.info(f"After business rules: {final_count} transactions (removed {initial_count - final_count} total)")

    return df


def clean_dataframe(df, pdf_format=1):
    """
    Clean and convert DataFrame datatypes.
    - Parses dates
    - Converts numeric columns (amount, fee, balance)
    - Cleans text columns and removes newlines from descriptions
    """
    # Parse dates
    df['txn_date'] = df['txn_date'].apply(lambda x: parse_date_string(str(x).strip(), EXPECTED_DT_FORMATS))

    # Clean numeric columns
    # For Format 2, keep the sign in amounts; for Format 1, strip it
    df['amount'] = df['amount'].astype(str).str.replace(',', '').str.strip()
    if pdf_format == 1:
        # Format 1: Remove any sign prefixes
        df['amount'] = df['amount'].str.lstrip('+-')
    # Format 2: Keep the sign (already handled above by just removing commas)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    df['fee'] = df['fee'].astype(str).str.replace(',', '').str.strip()
    df['fee'] = pd.to_numeric(df['fee'], errors='coerce').fillna(0)

    df['balance'] = df['balance'].astype(str).str.replace(',', '').str.strip()
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

    return df


def _calculate_segmented_balance(df, initial_opening_balance):
    """
    Calculate balance using segmented approach for Format 2 statements.
    Restarts balance calculation after Commission Disbursements, Deallocation Transfers, Rollbacks, and Transaction Reversals.

    Args:
        df: DataFrame with transactions (must have '_balance_restart' column)
        initial_opening_balance: Opening balance for the first segment

    Returns:
        float: Calculated closing balance
    """
    if df.empty:
        return 0

    # Find all restart points
    restart_indices = df[df['_balance_restart']].index.tolist()

    if not restart_indices:
        # No restart points, use simple calculation
        return initial_opening_balance + df['amount'].sum()

    # Process in segments
    segments = []
    prev_end = -1

    for restart_idx in restart_indices:
        # Segment before restart point
        segment_start = prev_end + 1
        segment_end = restart_idx - 1

        if segment_end >= segment_start:
            segments.append((segment_start, segment_end, False))  # Normal segment

        # The restart transaction itself
        segments.append((restart_idx, restart_idx, True))  # Restart point

        prev_end = restart_idx

    # Final segment after last restart
    if prev_end < len(df) - 1:
        segments.append((prev_end + 1, len(df) - 1, False))

    # Calculate balance for each segment
    calculated_balance = initial_opening_balance

    for seg_start, seg_end, is_restart in segments:
        if is_restart:
            # For restart points, trust the statement balance
            # The balance shown in the statement is the correct balance after this transaction
            calculated_balance = df.iloc[seg_end]['balance']
        else:
            # For normal segments, calculate: previous_balance + sum(amounts)
            segment_amounts = df.iloc[seg_start:seg_end+1]['amount'].sum()
            calculated_balance = calculated_balance + segment_amounts

    return calculated_balance


def compute_balance_summary(df, account_number, file_name):
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
        # Sort by transaction date and balance (with direction consideration)
        # For same timestamp: debits first (higher balance), then credits (lower balance)
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
            # Format 2: Amount is signed (+credit, -debit)
            # Fees are already included in the signed amounts, not deducted separately
            # Opening = Current Balance - Signed Amount
            opening_balance = first_balance - first_amount

            # Calculate totals - amounts are already signed and include fees
            total_signed_amounts = df['amount'].sum()
            fees = df['fee'].sum()  # For reporting only
            charges = 0

            # For reporting purposes, separate credits and debits
            credits = df[df['amount'] > 0]['amount'].sum()  # Positive amounts
            debits = abs(df[df['amount'] < 0]['amount'].sum())  # Negative amounts (absolute value)

            # Check if we need segmented calculation (for balance restart points)
            if '_balance_restart' in df.columns and df['_balance_restart'].any():
                # Segmented calculation: restart balance calculation after certain transactions
                # (Commission Disbursements, Deallocation Transfers, Rollbacks, Transaction Reversals)
                calculated_closing_balance = _calculate_segmented_balance(df, opening_balance)
            else:
                # Simple calculation: Opening + Sum(Signed Amounts)
                calculated_closing_balance = opening_balance + total_signed_amounts

        else:
            # Format 1: Amount is unsigned, direction in separate column
            first_direction = df.iloc[0]['txn_direction'].lower()

            if first_direction == 'credit':
                opening_balance = first_balance - first_amount - first_fee
            else:
                opening_balance = first_balance + first_amount + first_fee

            # Calculate totals
            credits = df[df['txn_direction'].str.lower() == 'credit']['amount'].sum()
            debits = df[df['txn_direction'].str.lower() == 'debit']['amount'].sum()
            fees = df['fee'].sum()
            charges = 0

            # Calculate expected closing balance
            # Try both with and without fees to see which matches better
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

        # Get closing balance from last transaction
        closing_balance_from_stmt = df.iloc[-1]['balance']

        # Verify balance (allow small floating point differences)
        balance_diff = abs(calculated_closing_balance - closing_balance_from_stmt)
        balance_match = "Success" if balance_diff < 0.01 else "Failed"

        if balance_match == "Failed":
            logger.warning(f"Balance mismatch for {file_name}: Expected {calculated_closing_balance}, Got {closing_balance_from_stmt}")

        return {
            'account_number': account_number,
            'file_name': file_name,
            'balance_match': balance_match,
            'opening_balance': round(opening_balance, 2),
            'credits': round(credits, 2),
            'debits': round(debits, 2),
            'fees': round(fees, 2),
            'charges': round(charges, 2),
            'calculated_closing_balance': round(calculated_closing_balance, 2),
            'stmt_closing_balance': round(closing_balance_from_stmt, 2),
            'error': ''
        }

    except Exception as e:
        logger.error(f"Error computing balance summary for {file_name}: {e}")
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
            'error': str(e)
        }


def calculate_running_balance(df):
    """
    Calculate row-by-row running balance for all transactions.
    This is the single source of truth for transaction-level balance calculation.

    Special transaction handling:
    - Deallocation/Rollback/Reversal/Failed: Keep previous running balance (no add/subtract)
    - Commission Disbursement: Add to balance for debit, subtract for credit (won't match statement)
    - Duplicates: Keep previous running balance

    Args:
        df: DataFrame with transactions from extract_data_from_pdf

    Returns:
        pd.DataFrame: DataFrame with additional columns:
            - calculated_running_balance: Running balance for each row
            - balance_diff: Difference between statement and calculated balance
            - is_duplicate: Flag for duplicate transactions
            - is_special_txn: Flag for special transactions
            - special_txn_type: Type of special transaction
    """
    import numpy as np

    if df.empty:
        return df

    # Make a copy to avoid modifying the original
    df = df.copy()

    # First, sort by timestamp and balance descending as initial ordering
    df = df.sort_values(['txn_date', 'balance'], ascending=[True, False]).reset_index(drop=True)

    # Detect format first (needed for optimization)
    amounts_are_signed = (df['amount'] < 0).any()

    # Now, optimize same-timestamp groups by testing different orderings
    def optimize_same_timestamp_group(group_df, prev_running_balance, amounts_are_signed):
        """
        For same-timestamp transactions, find the ordering that produces
        the correct balance progression by testing permutations.
        Uses the PREVIOUS running balance as the starting point.
        """
        from itertools import permutations

        if len(group_df) <= 1:
            return group_df

        # For groups > 6, use descending balance order (too many permutations)
        if len(group_df) > 6:
            return group_df.sort_values('balance', ascending=False).reset_index(drop=True)

        # Try all permutations and find the one where balances match
        best_order = None
        best_score = -1

        indices = list(range(len(group_df)))

        for perm in permutations(indices):
            test_df = group_df.iloc[list(perm)].reset_index(drop=True)
            score = 0

            # Start with the PREVIOUS running balance (before this group)
            running_bal = prev_running_balance

            for i in range(len(test_df)):
                row = test_df.iloc[i]

                # Apply transaction to get expected balance
                if amounts_are_signed:
                    expected_bal = running_bal + row['amount']
                else:
                    if row['txn_direction'].lower() == 'credit':
                        expected_bal = running_bal + row['amount'] - row['fee']
                    else:
                        expected_bal = running_bal - row['amount'] - row['fee']

                # Check if it matches the row's statement balance
                if abs(expected_bal - row['balance']) < 0.01:
                    score += 1

                # Update running balance to this row's statement balance for next iteration
                running_bal = row['balance']

            if score > best_score:
                best_score = score
                best_order = test_df

        return best_order if best_order is not None else group_df

    # Group by timestamp and optimize each group
    optimized_groups = []
    prev_running_balance = 0  # Will be updated as we process

    for txn_date, group in df.groupby('txn_date', sort=False):
        # Get the previous running balance (use first row's balance as fallback for first group)
        if len(optimized_groups) == 0:
            # For first group, we don't have a previous balance, use descending order
            optimized_group = group.sort_values('balance', ascending=False).reset_index(drop=True)
        else:
            # Use the last row's balance from previous groups as starting point
            prev_running_balance = optimized_groups[-1].iloc[-1]['balance']
            optimized_group = optimize_same_timestamp_group(group, prev_running_balance, amounts_are_signed)

        optimized_groups.append(optimized_group)

    # Recombine all groups
    df = pd.concat(optimized_groups, ignore_index=True)

    # Mark duplicates
    df['is_duplicate'] = df.duplicated(
        subset=['txn_id', 'txn_date', 'amount', 'balance'],
        keep='first'
    )

    # Identify special transactions
    df['is_special_txn'] = False
    df['special_txn_type'] = ''

    # Mark Deallocation Transfers
    dealloc_mask = df['description'].str.contains('Deallocation', case=False, na=False)
    df.loc[dealloc_mask, 'is_special_txn'] = True
    df.loc[dealloc_mask, 'special_txn_type'] = 'Deallocation'

    # Mark Rollbacks
    rollback_mask = df['description'].str.contains('RollBack', case=False, na=False)
    df.loc[rollback_mask, 'is_special_txn'] = True
    df.loc[rollback_mask, 'special_txn_type'] = 'Rollback'

    # Mark Transaction Reversals
    reversal_mask = df['description'].str.contains('Transaction Reversal', case=False, na=False)
    df.loc[reversal_mask, 'is_special_txn'] = True
    df.loc[reversal_mask, 'special_txn_type'] = 'Reversal'

    # Mark Failed transactions
    failed_mask = df['status'].str.upper() == 'FAILED'
    df.loc[failed_mask, 'is_special_txn'] = True
    df.loc[failed_mask, 'special_txn_type'] = 'Failed'

    # Mark Commission Disbursements (exact phrase, not transfers from commission wallet)
    commission_mask = df['description'].str.contains('Commission Disbursement', case=False, na=False)
    df.loc[commission_mask, 'is_special_txn'] = True
    df.loc[commission_mask, 'special_txn_type'] = 'Commission'

    # Initialize columns
    df['calculated_running_balance'] = np.nan
    df['balance_diff'] = np.nan

    # Get opening balance from first transaction
    first_balance = df.iloc[0]['balance']
    first_amount = df.iloc[0]['amount']
    first_fee = df.iloc[0]['fee']
    first_direction = df.iloc[0]['txn_direction'].lower() if 'txn_direction' in df.columns else 'credit'

    # Detect format based on whether amounts are signed
    amounts_are_signed = (df['amount'] < 0).any()

    if amounts_are_signed:
        # Format 2: Amount is already signed and includes fees
        opening_balance = first_balance - first_amount
    else:
        # Format 1: Amount is unsigned, use direction, fees separate
        if first_direction == 'credit':
            opening_balance = first_balance - first_amount - first_fee
        else:
            opening_balance = first_balance + first_amount + first_fee

    # Set first row calculated balance to match statement balance
    df.loc[0, 'calculated_running_balance'] = first_balance
    df.loc[0, 'balance_diff'] = 0

    # Calculate running balance starting from second row
    running_balance = first_balance
    previous_balance_diff = 0

    for idx in range(1, len(df)):
        row = df.iloc[idx]

        # Check if this row is a duplicate
        is_duplicate = row.get('is_duplicate', False)
        is_special = row.get('is_special_txn', False)
        special_type = row.get('special_txn_type', '')

        if is_duplicate:
            # For duplicate rows, keep the running balance from previous row
            df.loc[idx, 'calculated_running_balance'] = running_balance
            df.loc[idx, 'balance_diff'] = previous_balance_diff

        elif is_special and special_type in ['Deallocation', 'Rollback', 'Reversal', 'Failed']:
            # For Deallocation/Rollback/Reversal/Failed: Keep previous running balance (no change)
            df.loc[idx, 'calculated_running_balance'] = running_balance
            df.loc[idx, 'balance_diff'] = previous_balance_diff

        elif is_special and special_type == 'Commission':
            # For Commission Disbursement: Apply OPPOSITE logic (won't match statement)
            # If debit: add to balance, if credit: subtract from balance
            if amounts_are_signed:
                # Format 2: amount is signed
                if row['amount'] < 0:  # Debit
                    running_balance = running_balance + abs(row['amount'])  # Add
                else:  # Credit
                    running_balance = running_balance - row['amount']  # Subtract
            else:
                # Format 1: use direction
                if row['txn_direction'].lower() == 'debit':
                    running_balance = running_balance + row['amount'] + row['fee']  # Add
                else:  # credit
                    running_balance = running_balance - row['amount'] - row['fee']  # Subtract

            df.loc[idx, 'calculated_running_balance'] = running_balance
            # Keep previous balance_diff for commission (don't calculate new one)
            df.loc[idx, 'balance_diff'] = previous_balance_diff

        else:
            # Normal calculation
            if amounts_are_signed:
                # Format 2: Amount is already signed and includes fees
                running_balance = running_balance + row['amount']
            else:
                # Format 1: Amount is unsigned, use direction, fees separate
                if row['txn_direction'].lower() == 'credit':
                    running_balance = running_balance + row['amount'] - row['fee']
                else:
                    running_balance = running_balance - row['amount'] - row['fee']

            df.loc[idx, 'calculated_running_balance'] = running_balance
            # Calculate balance diff normally
            balance_diff = row['balance'] - running_balance
            df.loc[idx, 'balance_diff'] = balance_diff
            previous_balance_diff = balance_diff

    # Count balance_diff transitions (how many times it changes)
    df['balance_diff_change_count'] = 0
    change_count = 0
    previous_diff_value = df.iloc[0]['balance_diff']

    for idx in range(1, len(df)):
        current_diff = df.iloc[idx]['balance_diff']
        if current_diff != previous_diff_value:
            change_count += 1
            previous_diff_value = current_diff
        df.loc[idx, 'balance_diff_change_count'] = change_count

    return df


def parse_pdf_date(date_str):
    """Parse PDF date format like D:20240807103154+03'00' into '2024-08-07 10:31:54'."""
    if not date_str or not date_str.startswith("D:"):
        return date_str
    try:
        return datetime.strptime(date_str[2:16], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str


def get_pdf_metadata(pdf_path):
    """Extract metadata from PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata or {}
            for key, value in metadata.items():
                if key in ["CreationDate", "ModDate"]:
                    value = parse_pdf_date(value)
                    metadata[key] = parse_pdf_date(value)

            author = metadata.get('Author', 'N/A')
            modified_at = metadata.get('ModDate', 'N/A')

            result = {
                'title': metadata.get('Title', 'N/A'),
                'author': author,
                'creator': metadata.get('Creator', 'N/A'),
                'producer': metadata.get('Producer', 'N/A'),
                'created_at': metadata.get('CreationDate', 'N/A'),
                'modified_at': modified_at,
                'has_author': 'Yes' if (author and author != 'N/A') else 'No',
                'has_modified_at': 'Yes' if (modified_at and modified_at != 'N/A') else 'No'
            }
        return result
    except Exception as e:
        logger.error(f"Error extracting metadata from {pdf_path}: {e}")
        return {
            'title': 'N/A',
            'author': 'N/A',
            'creator': 'N/A',
            'producer': 'N/A',
            'created_at': 'N/A',
            'modified_at': 'N/A',
            'has_author': 'No',
            'has_modified_at': 'No'
        }


def merge_with_mapper(summaries_df, mapper_path):
    """Merge summary data with mapper.csv to enrich with RM details."""
    try:
        mapper_df = pd.read_csv(mapper_path)

        # Merge on account_number
        merged_df = summaries_df.merge(
            mapper_df[['run_id', 'acc_number', 'rm_id', 'rm_name']],
            left_on='account_number',
            right_on='acc_number',
            how='left'
        )

        # Reorder columns to put run_id and rm_name first
        cols = ['run_id', 'rm_name', 'account_number', 'file_name', 'duplicate_count', 'balance_match',
                'opening_balance', 'credits', 'debits', 'fees', 'charges',
                'calculated_closing_balance', 'stmt_closing_balance',
                'title', 'author', 'has_author', 'creator', 'producer', 'created_at', 'modified_at', 'has_modified_at']

        # Add error column if it exists
        if 'error' in merged_df.columns:
            cols.append('error')

        # Only keep columns that exist
        cols = [col for col in cols if col in merged_df.columns]
        merged_df = merged_df[cols]

        return merged_df

    except Exception as e:
        logger.error(f"Error merging with mapper: {e}")
        return summaries_df


def detect_duplicate_transactions(df):
    """
    Detect duplicate transactions based on txn_id, txn_date, amount, and balance.
    Returns count of duplicates.
    """
    if df.empty:
        return 0

    # Find duplicates based on combination of txn_id, txn_date, amount, balance
    duplicate_mask = df.duplicated(subset=['txn_id', 'txn_date', 'amount', 'balance'], keep=False)
    duplicate_count = duplicate_mask.sum()

    return duplicate_count


def write_summary_csv(summaries, output_path):
    """Write summary data to CSV file."""
    try:
        df = pd.DataFrame(summaries)

        # Merge with mapper
        df = merge_with_mapper(df, MAPPER_PATH)

        # Write to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Summary written to {output_path}")

        return df

    except Exception as e:
        logger.error(f"Error writing summary CSV: {e}")
        raise


def process_all_statements():
    """Main function to process all PDF statements."""
    logger.info("Starting statement processing...")

    # Get all PDF files from statements directory
    pdf_files = [f for f in os.listdir(STATEMENTS_PATH) if f.endswith('.pdf')]

    if not pdf_files:
        logger.warning(f"No PDF files found in {STATEMENTS_PATH}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files to process")

    summaries = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(STATEMENTS_PATH, pdf_file)

        try:
            # Extract data from PDF
            df, acc_number = extract_data_from_pdf(pdf_path)

            # Detect and remove duplicate transactions
            duplicate_count = detect_duplicate_transactions(df)
            df_deduplicated = df.copy()

            if duplicate_count > 0:
                # Remove duplicates, keeping only the first occurrence
                df_deduplicated = df.drop_duplicates(
                    subset=['txn_id', 'txn_date', 'amount', 'balance'],
                    keep='first'
                ).reset_index(drop=True)
                logger.info(f"Removed {duplicate_count} duplicate transactions from {pdf_file}")

            # Compute balance summary (using deduplicated data)
            summary = compute_balance_summary(df_deduplicated, acc_number, pdf_file)
            summary['duplicate_count'] = duplicate_count

            # Get metadata
            metadata = get_pdf_metadata(pdf_path)

            # Merge summary with metadata
            summary.update(metadata)

            summaries.append(summary)

        except Exception as e:
            logger.error(f"Failed to process {pdf_file}: {e}")
            summaries.append({
                'account_number': 'Unknown',
                'file_name': pdf_file,
                'balance_match': 'Failed',
                'opening_balance': 0,
                'credits': 0,
                'debits': 0,
                'fees': 0,
                'charges': 0,
                'closing_balance': 0,
                'title': 'N/A',
                'author': 'N/A',
                'creator': 'N/A',
                'producer': 'N/A',
                'created_at': 'N/A',
                'modified_at': 'N/A',
                'error': str(e)
            })

    # Write summary to CSV
    result_df = write_summary_csv(summaries, OUTPUT_PATH)

    logger.info("Processing complete!")
    logger.info(f"Processed {len(summaries)} statements")
    logger.info(f"Success: {result_df['balance_match'].value_counts().get('Success', 0)}")
    logger.info(f"Failed: {result_df['balance_match'].value_counts().get('Failed', 0)}")

    return result_df


if __name__ == '__main__':
    process_all_statements()
