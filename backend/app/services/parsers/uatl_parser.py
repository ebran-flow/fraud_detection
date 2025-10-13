"""
UATL (Airtel) Parser
Uses PDF parsing utilities for Airtel Money statements
"""
import os
import hashlib
import logging
import pdfplumber
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Import PDF parsing utilities
from .pdf_utils import (
    extract_data_from_pdf,
)

logger = logging.getLogger(__name__)


def parse_pdf_date(date_str: str) -> str:
    """Parse PDF date format like D:20240807103154+03'00' into '2024-08-07 10:31:54'."""
    if not date_str or not date_str.startswith("D:"):
        return date_str
    try:
        return datetime.strptime(date_str[2:16], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str


def extract_pdf_metadata(path: str) -> Dict[str, Any]:
    """
    Extract PDF metadata (title, author, dates, etc.)

    Args:
        path: Path to PDF file

    Returns:
        Dictionary with metadata
    """
    result = {}
    try:
        with pdfplumber.open(path) as pdf:
            metadata = pdf.metadata or {}
            for key, value in metadata.items():
                if key in ["CreationDate", "ModDate"]:
                    value = parse_pdf_date(value)
                    metadata[key] = value

            result = {
                'title': metadata.get('Title', 'N/A'),
                'author': metadata.get('Author', 'N/A'),
                'creator': metadata.get('Creator', 'N/A'),
                'producer': metadata.get('Producer', 'N/A'),
                'created_at': metadata.get('CreationDate', 'N/A'),
                'modified_at': metadata.get('ModDate', 'N/A'),
            }
    except Exception as e:
        logger.warning(f"Could not extract PDF metadata: {e}")
        result = {
            'title': 'N/A',
            'author': 'N/A',
            'creator': 'N/A',
            'producer': 'N/A',
            'created_at': 'N/A',
            'modified_at': 'N/A',
        }
    return result


def parse_uatl_pdf(pdf_path: str, run_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse Airtel PDF using existing logic

    Args:
        pdf_path: Path to PDF file
        run_id: Unique run identifier

    Returns:
        Tuple of (raw_statements_list, metadata_dict)
    """
    logger.info(f"Parsing UATL PDF: {pdf_path} with run_id: {run_id}")

    try:
        # Use existing extraction logic
        df, acc_number, quality_issues_count = extract_data_from_pdf(pdf_path)

        if df.empty:
            raise ValueError(f"No transaction data extracted from {pdf_path}")

        logger.info(f"Extracted {len(df)} transactions with {quality_issues_count} quality issues")

        # Get PDF format
        pdf_format = df.iloc[0].get('pdf_format', 1) if len(df) > 0 else 1

        # Extract summary fields from PDF (only for format 1)
        summary_email_address = None
        summary_customer_name = None
        summary_mobile_number = None
        summary_statement_period = None
        summary_request_date = None

        if pdf_format == 1:
            try:
                import pdfplumber
                from .pdf_utils import (
                    extract_requestor_email,
                    extract_customer_name,
                    extract_mobile_number,
                    extract_statement_period,
                    extract_request_date
                )
                with pdfplumber.open(pdf_path) as pdf:
                    if len(pdf.pages) > 0:
                        first_page = pdf.pages[0]

                        # Extract all summary fields
                        summary_email_address = extract_requestor_email(first_page, pdf_format)
                        summary_customer_name = extract_customer_name(first_page, pdf_format)
                        summary_mobile_number = extract_mobile_number(first_page, pdf_format)
                        summary_statement_period = extract_statement_period(first_page, pdf_format)
                        summary_request_date = extract_request_date(first_page, pdf_format)

                        # Log successful extractions
                        if summary_email_address:
                            logger.info(f"Extracted email address: {summary_email_address}")
                        if summary_customer_name:
                            logger.info(f"Extracted customer name: {summary_customer_name}")
                        if summary_mobile_number:
                            logger.info(f"Extracted mobile number: {summary_mobile_number}")
                        if summary_statement_period:
                            logger.info(f"Extracted statement period: {summary_statement_period}")
                        if summary_request_date:
                            logger.info(f"Extracted request date: {summary_request_date}")
            except Exception as e:
                logger.warning(f"Could not extract summary fields: {e}")

        # Extract PDF metadata
        pdf_meta = extract_pdf_metadata(pdf_path)

        # Calculate MD5 hash
        sheet_md5 = hashlib.md5(df.to_csv(index=False).encode()).hexdigest()

        # Prepare raw statements for database insertion
        raw_statements = []
        for idx, row in df.iterrows():
            raw_stmt = {
                'run_id': run_id,
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
                'amount_raw': str(row.get('amount_raw', '')) if row.get('amount_raw') else None,
                'fee': float(row['fee']) if row['fee'] is not None else 0.0,
                'balance': float(row['balance']) if row['balance'] is not None else None,
                'balance_raw': str(row.get('balance_raw', '')) if row.get('balance_raw') else None,
                'has_quality_issue': bool(row.get('has_quality_issue', False)),
                'pdf_format': pdf_format,
            }
            raw_statements.append(raw_stmt)

        # Prepare metadata
        metadata = {
            'run_id': run_id,
            'acc_prvdr_code': 'UATL',
            'acc_number': acc_number,
            'rm_name': None,  # Will be populated from mapper
            'num_rows': len(df),
            'sheet_md5': sheet_md5,
            'summary_opening_balance': None,  # Will be extracted from PDF summary section if available
            'summary_closing_balance': None,  # Will be extracted from PDF summary section if available
            'first_balance': float(df.iloc[0]['balance']) if len(df) > 0 else None,
            'last_balance': float(df.iloc[-1]['balance']) if len(df) > 0 else None,
            # Data quality tracking (similar to duplicate_count)
            'quality_issues_count': quality_issues_count,
            # Summary fields extracted from Airtel Format 1 PDFs
            'summary_email_address': summary_email_address,
            'summary_customer_name': summary_customer_name,
            'summary_mobile_number': summary_mobile_number,
            'summary_statement_period': summary_statement_period,
            'summary_request_date': summary_request_date.date() if summary_request_date else None,
            'meta_title': pdf_meta.get('title'),
            'meta_author': pdf_meta.get('author'),
            'meta_producer': pdf_meta.get('producer'),
            'meta_created_at': parse_metadata_date(pdf_meta.get('created_at')),
            'meta_modified_at': parse_metadata_date(pdf_meta.get('modified_at')),
            'pdf_path': pdf_path,
            'format': f'format_{pdf_format}',  # e.g., 'format_1' or 'format_2'
        }

        logger.info(f"Successfully parsed {len(raw_statements)} UATL transactions for {run_id}")
        return raw_statements, metadata

    except Exception as e:
        logger.error(f"Error parsing UATL PDF {pdf_path}: {e}")
        raise


def parse_metadata_date(date_str: str) -> datetime:
    """Parse metadata date string to datetime"""
    if not date_str or date_str == 'N/A':
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            logger.warning(f"Could not parse metadata date: {date_str}")
            return None
