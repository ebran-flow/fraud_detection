"""
UATL CSV Parser
Parses Airtel Money CSV statements (both Format 1 and Format 2)
"""
import logging
import pandas as pd
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


def parse_uatl_csv(file_path: str, run_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse Airtel Money CSV statement

    Args:
        file_path: Path to CSV file
        run_id: Unique identifier for this upload

    Returns:
        Tuple of (transactions_list, metadata_dict)
    """
    try:
        # Read the entire CSV to detect format
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Extract basic info
        metadata = extract_metadata_from_csv(content)

        # Find where transaction data starts
        lines = content.split('\n')
        header_line_idx = None
        for i, line in enumerate(lines):
            if 'Transaction ID' in line and 'Transaction Date' in line:
                header_line_idx = i
                break

        if header_line_idx is None:
            error_msg = "Could not find transaction header in CSV"
            logger.error(error_msg)
            metadata.update({
                'run_id': run_id,
                'acc_prvdr_code': 'UATL',
                'num_rows': 0,
                'parsing_status': 'FAILED',
                'parsing_error': error_msg
            })
            return [], metadata

        # Read transaction data starting from header
        df = pd.read_csv(file_path, skiprows=header_line_idx, encoding='utf-8-sig')

        # Clean column names
        df.columns = df.columns.str.strip()

        # Detect format
        # CSV with Credit/Debit column = Format 1 (amounts will be signed based on Credit/Debit)
        # CSV without Credit/Debit column = Format 2 (signed amounts)
        has_credit_debit_column = 'Credit/Debit' in df.columns
        pdf_format = 1 if has_credit_debit_column else 2

        logger.info(f"Detected Format {pdf_format} CSV for run_id: {run_id}")

        # Parse transactions based on format
        if pdf_format == 1:
            transactions = parse_format1_csv(df, run_id, metadata)
        else:
            transactions = parse_format2_csv(df, run_id, metadata)

        # Update metadata
        metadata.update({
            'run_id': run_id,
            'acc_prvdr_code': 'UATL',
            'pdf_format': pdf_format,
            'num_rows': len(transactions),
            'parsing_status': 'SUCCESS',
            'parsing_error': None
        })

        return transactions, metadata

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error parsing CSV {file_path}: {error_msg}")
        metadata = {
            'run_id': run_id,
            'acc_prvdr_code': 'UATL',
            'num_rows': 0,
            'parsing_status': 'FAILED',
            'parsing_error': error_msg
        }
        return [], metadata


def extract_metadata_from_csv(content: str) -> Dict[str, Any]:
    """Extract metadata from CSV content"""
    metadata = {}

    # Extract customer name
    match = re.search(r'Customer Name,(.+)', content)
    if match:
        metadata['rm_name'] = match.group(1).strip()

    # Extract mobile number
    match = re.search(r'Mobile Number,(\d+)', content)
    if match:
        metadata['acc_number'] = match.group(1).strip()

    # Extract opening balance
    match = re.search(r'Opening Balance,(?:Ugx\s*)?[\",]?([0-9,]+\.?\d*)', content)
    if match:
        balance_str = match.group(1).replace(',', '')
        try:
            metadata['stmt_opening_balance'] = float(balance_str)
        except:
            pass

    # Extract closing balance
    match = re.search(r'Closing Balance,(?:Ugx\s*)?[\",]?([0-9,]+\.?\d*)', content)
    if match:
        balance_str = match.group(1).replace(',', '')
        try:
            metadata['stmt_closing_balance'] = float(balance_str)
        except:
            pass

    # Extract total credit
    match = re.search(r'Total Credit,(?:Ugx\s*)?[\",]?([0-9,]+\.?\d*)', content)
    if match:
        balance_str = match.group(1).replace(',', '')
        try:
            metadata['summary_opening_balance'] = float(balance_str)  # Store total credit
        except:
            pass

    # Extract total debit
    match = re.search(r'Total Debit,(?:Ugx\s*)?[\",]?([0-9,]+\.?\d*)', content)
    if match:
        balance_str = match.group(1).replace(',', '')
        try:
            metadata['summary_closing_balance'] = float(balance_str)  # Store total debit
        except:
            pass

    # CSV metadata
    metadata['meta_title'] = 'Airtel Money CSV Statement'
    metadata['meta_author'] = 'Airtel'
    metadata['meta_producer'] = 'CSV Export'

    return metadata


def parse_format1_csv(df: pd.DataFrame, run_id: str, metadata: Dict) -> List[Dict[str, Any]]:
    """
    Parse Format 1 CSV (with Credit/Debit column)
    Columns: Transaction ID, Transaction Date, Description, Status, Transaction Amount, Credit/Debit, Fee, Balance
    Amounts are signed based on Credit/Debit column: Credit=positive, Debit=negative
    """
    transactions = []
    acc_number = metadata.get('acc_number', 'Unknown')

    for idx, row in df.iterrows():
        try:
            # Skip empty rows
            if pd.isna(row.get('Transaction ID')):
                continue

            # Parse transaction date
            txn_date = parse_date(str(row['Transaction Date']))

            # Get amount and direction
            amount_str = str(row['Transaction Amount']).replace(',', '')
            amount_abs = abs(float(amount_str)) if amount_str else 0.0

            direction = str(row['Credit/Debit']).strip().upper()

            # Sign amount based on Credit/Debit column
            # Credit = positive, Debit = negative
            if direction == 'DEBIT':
                amount = -amount_abs
                txn_direction = 'DR'
            else:  # CREDIT
                amount = amount_abs
                txn_direction = 'CR'

            # Parse fee
            fee_str = str(row.get('Fee', '0')).replace(',', '')
            fee = float(fee_str) if fee_str and fee_str != 'nan' else 0.0

            # Parse balance
            balance_str = str(row['Balance']).replace(',', '')
            balance = float(balance_str) if balance_str and balance_str != 'nan' else None

            transaction = {
                'run_id': run_id,
                'acc_number': acc_number,
                'txn_id': str(row['Transaction ID']),
                'txn_date': txn_date,
                'txn_type': None,
                'description': str(row['Description']).strip(),
                'from_acc': None,
                'to_acc': None,
                'status': str(row['Status']).strip(),
                'txn_direction': txn_direction,
                'amount': amount,
                'fee': fee,
                'balance': balance
            }

            transactions.append(transaction)

        except Exception as e:
            logger.warning(f"Error parsing row {idx}: {e}")
            continue

    return transactions


def parse_format2_csv(df: pd.DataFrame, run_id: str, metadata: Dict) -> List[Dict[str, Any]]:
    """
    Parse Format 2 CSV (signed amounts, no Credit/Debit column)
    Columns: Transaction ID, Transaction Date, Description, Status, Amount, Fee, Balance
    """
    transactions = []
    acc_number = metadata.get('acc_number', 'Unknown')

    for idx, row in df.iterrows():
        try:
            # Skip empty rows
            if pd.isna(row.get('Transaction ID')):
                continue

            # Parse transaction date
            txn_date = parse_date(str(row['Transaction Date']))

            # Get signed amount
            amount_str = str(row['Transaction Amount']).replace(',', '')
            amount = float(amount_str) if amount_str else 0.0

            # Determine direction from amount sign
            if amount < 0:
                txn_direction = 'DR'
            else:
                txn_direction = 'CR'

            # Parse fee
            fee_str = str(row.get('Fee', '0')).replace(',', '')
            fee = float(fee_str) if fee_str and fee_str != 'nan' else 0.0

            # Parse balance
            balance_str = str(row['Balance']).replace(',', '')
            balance = float(balance_str) if balance_str and balance_str != 'nan' else None

            transaction = {
                'run_id': run_id,
                'acc_number': acc_number,
                'txn_id': str(row['Transaction ID']),
                'txn_date': txn_date,
                'txn_type': None,
                'description': str(row['Description']).strip(),
                'from_acc': None,
                'to_acc': None,
                'status': str(row['Status']).strip(),
                'txn_direction': txn_direction,
                'amount': amount,
                'fee': fee,
                'balance': balance
            }

            transactions.append(transaction)

        except Exception as e:
            logger.warning(f"Error parsing row {idx}: {e}")
            continue

    return transactions


def parse_date(date_str: str) -> datetime:
    """
    Parse date from various formats
    Examples: "01-05-25 08:17 AM", "2025-05-01 08:17:00"
    """
    date_str = date_str.strip()

    # Try format: "01-05-25 08:17 AM"
    try:
        return datetime.strptime(date_str, "%d-%m-%y %I:%M %p")
    except:
        pass

    # Try format: "01-May-25 08:17 AM"
    try:
        return datetime.strptime(date_str, "%d-%b-%y %I:%M %p")
    except:
        pass

    # Try format: "2025-05-01 08:17:00"
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except:
        pass

    # Try format: "01/05/2025 08:17"
    try:
        return datetime.strptime(date_str, "%d/%m/%Y %H:%M")
    except:
        pass

    # Default fallback
    logger.warning(f"Could not parse date: {date_str}, using current time")
    return datetime.now()
