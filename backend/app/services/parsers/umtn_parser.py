"""
UMTN (MTN) Parser
Handles Excel/CSV format MTN Mobile Money statements
Uses xlrd3 for legacy Excel files that have compatibility issues with openpyxl
"""
import os
import hashlib
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd
import xlrd3 as xlrd
from ..mapper import get_mapping_by_run_id

logger = logging.getLogger(__name__)


def jsonify_worksheet(worksheet):
    """Convert xlrd worksheet to list of dictionaries"""
    rows_dict = []
    header = [cell.value for cell in worksheet.row(0)]
    for row_idx in range(1, worksheet.nrows):
        row_dict = {}
        NUMBER_TYPE = 2
        for col_idx, cell in enumerate(worksheet.row(row_idx)):
            # Convert number cells to string (preserving int values)
            cell_value = str(int(float(cell.value))) if cell.ctype == NUMBER_TYPE else cell.value
            row_dict[header[col_idx]] = cell_value
        rows_dict.append(row_dict)
    return rows_dict


def get_df_from_mtn_excel(file_path: str) -> pd.DataFrame:
    """
    Read MTN Excel file using xlrd3 (handles legacy Excel formats)
    """
    with open(file_path, 'rb') as f:
        file_contents = f.read()

    workbook = xlrd.open_workbook(file_contents=file_contents)
    sheet_name = workbook.sheet_names()[0]
    loaded_sheet = workbook.sheet_by_name(sheet_name)
    json_data = jsonify_worksheet(loaded_sheet)
    df = pd.DataFrame(json_data)
    return df


def parse_umtn_excel(file_path: str, run_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse MTN Excel/CSV file

    Args:
        file_path: Path to Excel or CSV file
        run_id: Unique run identifier

    Returns:
        Tuple of (raw_statements_list, metadata_dict)
    """
    logger.info(f"Parsing UMTN file: {file_path} with run_id: {run_id}")

    try:
        # Get account number from mapper.csv
        mapper_data = get_mapping_by_run_id(run_id)
        if not mapper_data:
            logger.warning(f"No mapper data found for run_id: {run_id}")
            acc_number = None
        else:
            acc_number = mapper_data.get('acc_number')
            logger.info(f"Found acc_number from mapper: {acc_number}")

        # Read file (supports both CSV and Excel)
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith(('.xlsx', '.xls')):
            # Use xlrd3 for legacy Excel files (MTN uses old Excel generators)
            df = get_df_from_mtn_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        if df.empty:
            raise ValueError(f"No transaction data in {file_path}")

        logger.info(f"Loaded {len(df)} rows from UMTN file")

        # Parse transactions
        raw_statements = []
        for idx, row in df.iterrows():
            # Parse date/time
            txn_date = parse_umtn_datetime(row.get('Date / Time'))

            # Helper to safely convert to float (handles strings from xlrd3)
            def safe_float(val):
                if pd.isna(val) or val == '' or val == 'None':
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            # Determine transaction direction from amount
            amount = safe_float(row.get('Amount'))
            if amount is None:
                amount = 0.0
            txn_direction = 'Credit' if amount > 0 else 'Debit'

            # Extract from/to accounts
            from_acc = str(row.get('From Account', '')) if pd.notna(row.get('From Account')) else ''
            to_acc = str(row.get('To Account', '')) if pd.notna(row.get('To Account')) else ''

            # Extract transaction ID
            txn_id = str(row.get('Transaction ID', '')) if pd.notna(row.get('Transaction ID')) else ''

            # Skip rows with empty transaction ID (prevents unique constraint violations)
            if not txn_id or txn_id.strip() == '':
                logger.warning(f"Skipping row {idx} with empty Transaction ID")
                continue

            raw_stmt = {
                'run_id': run_id,
                'acc_number': acc_number,  # From mapper.csv
                'txn_id': txn_id,
                'txn_date': txn_date,
                'txn_type': str(row.get('Transaction Type', '')) if pd.notna(row.get('Transaction Type')) else '',
                'description': f"{row.get('Transaction Type', '')} - {from_acc} to {to_acc}",
                'from_acc': from_acc,
                'to_acc': to_acc,
                'status': 'success',  # UMTN only shows successful transactions
                'txn_direction': txn_direction,
                'amount': amount,
                'fee': safe_float(row.get('Fee')) or 0.0,
                # UMTN-specific fields
                'commission_amount': safe_float(row.get('Commision Amount')),
                'tax': safe_float(row.get('TAX')),
                'commission_receiving_no': str(row.get('Commision Receiving No.', '')) if pd.notna(row.get('Commision Receiving No.')) and str(row.get('Commision Receiving No.', '')) != 'None' else None,
                'commission_balance': safe_float(row.get('Commision Balance')),
                'float_balance': safe_float(row.get('Float Balance')),
            }
            raw_statements.append(raw_stmt)

        # Calculate MD5 hash
        sheet_md5 = hashlib.md5(df.to_csv(index=False).encode()).hexdigest()

        # Get date range
        first_date = raw_statements[0]['txn_date'] if raw_statements else None
        last_date = raw_statements[-1]['txn_date'] if raw_statements else None

        # Get first and last balance from float_balance column
        first_balance = raw_statements[0]['float_balance'] if raw_statements else None
        last_balance = raw_statements[-1]['float_balance'] if raw_statements else None

        # Prepare metadata
        metadata = {
            'run_id': run_id,
            'acc_prvdr_code': 'UMTN',
            'acc_number': acc_number,  # From mapper.csv
            'format': 'excel',  # MTN uses Excel/CSV format
            'rm_name': None,  # Will be populated from mapper
            'num_rows': len(df),
            'sheet_md5': sheet_md5,
            'summary_opening_balance': None,  # MTN doesn't have a summary section
            'summary_closing_balance': None,  # MTN doesn't have a summary section
            'first_balance': first_balance,
            'last_balance': last_balance,
            'meta_title': f'MTN Statement {first_date.strftime("%Y-%m-%d") if first_date else ""}',
            'meta_author': 'MTN Uganda',
            'meta_producer': 'MTN Mobile Money',
            'meta_created_at': first_date,
            'meta_modified_at': last_date,
            'pdf_path': file_path,
        }

        logger.info(f"Successfully parsed {len(raw_statements)} UMTN transactions for {run_id}")
        return raw_statements, metadata

    except Exception as e:
        logger.error(f"Error parsing UMTN file {file_path}: {e}")
        raise


def parse_umtn_datetime(date_str: str) -> datetime:
    """
    Parse UMTN date/time string

    Format: '2025-09-01 08:41'
    """
    if not date_str or pd.isna(date_str):
        return None

    try:
        # Try standard format
        return datetime.strptime(str(date_str).strip(), '%Y-%m-%d %H:%M')
    except:
        try:
            # Try with seconds
            return datetime.strptime(str(date_str).strip(), '%Y-%m-%d %H:%M:%S')
        except:
            logger.warning(f"Could not parse UMTN date: {date_str}")
            return None


def extract_account_number(from_acc: str, to_acc: str, txn_type: str) -> str:
    """
    Extract agent account number from transaction

    For UMTN, the agent's number appears consistently in specific positions
    """
    # Remove country code prefix if present (256)
    def clean_number(num):
        num = str(num).strip()
        if num.startswith('256'):
            return num[3:]
        return num

    # For most transactions, the agent number is in From Account
    if from_acc and from_acc != 'nan':
        return clean_number(from_acc)

    # Fallback to To Account
    if to_acc and to_acc != 'nan':
        # Remove @domain part if present
        num = to_acc.split('@')[0]
        return clean_number(num)

    return None


def convert_excel_to_csv(excel_path: str) -> str:
    """
    Convert Excel to CSV using LibreOffice

    Args:
        excel_path: Path to Excel file

    Returns:
        Path to CSV file
    """
    import subprocess
    import tempfile

    csv_path = os.path.join(tempfile.gettempdir(), os.path.basename(excel_path).replace('.xlsx', '.csv'))

    try:
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'csv',
            '--outdir', tempfile.gettempdir(),
            excel_path
        ], check=True, capture_output=True)

        logger.info(f"Converted {excel_path} to {csv_path}")
        return csv_path

    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting Excel to CSV: {e}")
        raise
