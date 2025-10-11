"""
PDF Parser Service
Wraps existing parsing logic from process_statements.py and fraud.py
Returns data in format ready for database insertion
"""
import os
import sys
import hashlib
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path

# Add project root to path to import existing modules
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import existing parsing functions
from process_statements import (
    extract_data_from_pdf,
    detect_pdf_format,
    extract_account_number,
    clean_dataframe,
    apply_format2_business_rules,
    compute_balance_summary,
    parse_date_string,
)
from fraud import get_metadata as extract_pdf_metadata

logger = logging.getLogger(__name__)


def parse_pdf_file(pdf_path: str, run_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse PDF file and return raw transactions + metadata

    Args:
        pdf_path: Path to PDF file
        run_id: Unique identifier for this statement

    Returns:
        Tuple of (raw_statements_list, metadata_dict)
    """
    logger.info(f"Parsing PDF: {pdf_path} with run_id: {run_id}")

    try:
        # Extract data from PDF using existing logic
        df, acc_number = extract_data_from_pdf(pdf_path)

        if df.empty:
            raise ValueError(f"No transaction data extracted from {pdf_path}")

        # Get PDF format
        pdf_format = df.iloc[0].get('pdf_format', 1) if len(df) > 0 else 1

        # Extract PDF metadata (title, author, producer, dates)
        pdf_meta = extract_pdf_metadata(pdf_path)

        # Calculate MD5 hash of the statement data for verification
        sheet_md5 = calculate_dataframe_hash(df)

        # Compute balance summary
        balance_summary = compute_balance_summary(df, acc_number, os.path.basename(pdf_path))

        # Prepare raw statements for database insertion
        raw_statements = []
        for idx, row in df.iterrows():
            # Convert pandas row to dictionary suitable for RawStatement model
            raw_stmt = {
                'run_id': run_id,
                'acc_prvdr_code': 'UATL',  # Default to UATL, will be updated from mapper
                'acc_number': acc_number,
                'txn_id': str(row.get('txn_id', '')),
                'txn_date': row['txn_date'] if row['txn_date'] else None,
                'txn_type': row.get('txn_type'),
                'description': str(row.get('description', '')),
                'from_acc': row.get('from_acc'),
                'to_acc': row.get('to_acc'),
                'status': str(row.get('status', '')),
                'txn_direction': str(row.get('txn_direction', '')),
                'amount': float(row['amount']) if row['amount'] is not None else None,
                'fee': float(row['fee']) if row['fee'] is not None else 0.0,
                'balance': float(row['balance']) if row['balance'] is not None else None,
            }
            raw_statements.append(raw_stmt)

        # Prepare metadata for database insertion
        metadata = {
            'run_id': run_id,
            'acc_prvdr_code': 'UATL',  # Default to UATL, can be updated via mapper
            'acc_number': acc_number,
            'pdf_format': pdf_format,
            'rm_name': None,  # Will be populated from mapper service
            'num_rows': len(df),
            'sheet_md5': sheet_md5,
            'summary_opening_balance': float(balance_summary.get('opening_balance', 0)),
            'summary_closing_balance': float(balance_summary.get('stmt_closing_balance', 0)),
            'stmt_opening_balance': float(df.iloc[0]['balance']) if len(df) > 0 else None,
            'stmt_closing_balance': float(df.iloc[-1]['balance']) if len(df) > 0 else None,
            'meta_title': pdf_meta.get('title'),
            'meta_author': pdf_meta.get('author'),
            'meta_producer': pdf_meta.get('producer'),
            'meta_created_at': parse_metadata_date(pdf_meta.get('created_at')),
            'meta_modified_at': parse_metadata_date(pdf_meta.get('modified_at')),
            'pdf_path': pdf_path,
        }

        logger.info(f"Successfully parsed {len(raw_statements)} transactions for {run_id}")
        return raw_statements, metadata

    except Exception as e:
        logger.error(f"Error parsing PDF {pdf_path}: {e}")
        raise


def calculate_dataframe_hash(df) -> str:
    """Calculate MD5 hash of dataframe for verification"""
    try:
        # Convert dataframe to CSV string for hashing
        csv_str = df.to_csv(index=False)
        return hashlib.md5(csv_str.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Error calculating hash: {e}")
        return ""


def parse_metadata_date(date_str: str) -> datetime:
    """Parse metadata date string to datetime"""
    if not date_str or date_str == 'N/A':
        return None
    try:
        # Try ISO format first
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        try:
            # Try standard datetime format
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            logger.warning(f"Could not parse metadata date: {date_str}")
            return None


def extract_run_id_from_filename(filename: str) -> str:
    """
    Extract run_id from PDF filename
    Convention: filename should be in format {run_id}.pdf
    """
    return Path(filename).stem


def validate_pdf_file(pdf_path: str) -> bool:
    """Validate that file exists and is a PDF"""
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return False

    if not pdf_path.lower().endswith('.pdf'):
        logger.error(f"File is not a PDF: {pdf_path}")
        return False

    return True
