"""
UMTN (MTN) Parser
Handles Excel/CSV format MTN Mobile Money statements
"""
import os
import hashlib
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


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
        # Read file (supports both CSV and Excel)
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith(('.xlsx', '.xls')):
            # Try reading with pandas
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except:
                # If pandas fails, convert to CSV using LibreOffice and retry
                csv_path = convert_excel_to_csv(file_path)
                df = pd.read_csv(csv_path)
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

            # Determine transaction direction from amount
            amount = float(row['Amount']) if pd.notna(row['Amount']) else 0
            txn_direction = 'Credit' if amount > 0 else 'Debit'

            # Extract account number from From Account or To Account
            from_acc = str(row['From Account']) if pd.notna(row['From Account']) else ''
            to_acc = str(row['To Account']) if pd.notna(row['To Account']) else ''

            # Account number is usually the agent's number
            # For CASH_IN/CASH_OUT, agent is in From Account
            # For TRANSFER, agent could be either
            acc_number = extract_account_number(from_acc, to_acc, row['Transaction Type'])

            raw_stmt = {
                'run_id': run_id,
                'acc_number': acc_number,
                'txn_id': str(row['Transaction ID']) if pd.notna(row['Transaction ID']) else '',
                'txn_date': txn_date,
                'txn_type': str(row['Transaction Type']) if pd.notna(row['Transaction Type']) else '',
                'description': f"{row['Transaction Type']} - {from_acc} to {to_acc}",
                'from_acc': from_acc,
                'to_acc': to_acc,
                'status': 'success',  # UMTN only shows successful transactions
                'txn_direction': txn_direction,
                'amount': amount,
                'fee': float(row['Fee']) if pd.notna(row['Fee']) else 0.0,
                # UMTN-specific fields
                'commission_amount': float(row['Commision Amount']) if pd.notna(row['Commision Amount']) else None,
                'tax': float(row['TAX']) if pd.notna(row['TAX']) else None,
                'commission_receiving_no': str(row['Commision Receiving No.']) if pd.notna(row['Commision Receiving No.']) else None,
                'commission_balance': float(row['Commision Balance']) if pd.notna(row['Commision Balance']) else None,
                'float_balance': float(row['Float Balance']) if pd.notna(row['Float Balance']) else None,
            }
            raw_statements.append(raw_stmt)

        # Calculate MD5 hash
        sheet_md5 = hashlib.md5(df.to_csv(index=False).encode()).hexdigest()

        # Get date range
        first_date = raw_statements[0]['txn_date'] if raw_statements else None
        last_date = raw_statements[-1]['txn_date'] if raw_statements else None

        # Calculate opening and closing balances (from float_balance)
        opening_balance = raw_statements[0]['float_balance'] - raw_statements[0]['amount'] if raw_statements else 0
        closing_balance = raw_statements[-1]['float_balance'] if raw_statements else 0

        # Prepare metadata
        metadata = {
            'run_id': run_id,
            'acc_prvdr_code': 'UMTN',
            'acc_number': acc_number if raw_statements else None,
            'pdf_format': None,  # UMTN doesn't have PDF format
            'rm_name': None,  # Will be populated from mapper
            'num_rows': len(df),
            'sheet_md5': sheet_md5,
            'summary_opening_balance': opening_balance,
            'summary_closing_balance': closing_balance,
            'stmt_opening_balance': opening_balance,
            'stmt_closing_balance': closing_balance,
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
