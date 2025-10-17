#!/usr/bin/env python3
"""
Fill missing summary fields from CSV files for UATL format_1 statements.
These statements were processed from CSV files without PDF paths.
"""

import os
import sys
import csv
import re
import gzip
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')


def parse_csv_value(value: str) -> str:
    """Parse a CSV value, removing quotes and extra whitespace."""
    if not value:
        return ""
    # Remove leading/trailing whitespace
    value = value.strip()
    # Remove quotes (including malformed trailing quotes)
    value = value.strip('"').strip()
    # Remove any trailing commas or extra quotes
    value = re.sub(r'[",]+$', '', value)
    return value.strip()


def extract_summary_from_csv(csv_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract summary information from CSV file.
    Handles both regular CSV and gzip-compressed CSV files.

    CSV format:
    Customer Name,Mary Asabaawebwa
    Mobile Number,742398025
    Email Address,kyesilimira.n@ug.flowglobal.net
    Statement Period,01-Apr-25 to 30-Jun-25
    Request Date,"30 Jul, 2025"
    Opening Balance,"Ugx 3,887.80"
    Closing Balance,Ugx 15.80
    """
    try:
        summary = {}

        # Check if file is gzip compressed
        is_gzip = False
        with open(csv_path, 'rb') as f:
            # Check for gzip magic number
            magic = f.read(2)
            is_gzip = (magic == b'\x1f\x8b')

        # Open file with appropriate handler
        if is_gzip:
            file_handle = gzip.open(csv_path, 'rt', encoding='utf-8')
        else:
            file_handle = open(csv_path, 'r', encoding='utf-8')

        try:
            # Read line by line to extract metadata
            for line in file_handle:
                line = line.strip()

                # Skip empty lines and headers
                if not line or line.startswith('Airtel Money') or line == 'Basic Info':
                    continue

                # Stop when we reach transaction details
                if 'Transaction Details' in line or 'Transaction ID' in line:
                    break

                # Parse key-value pairs
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parse_csv_value(parts[1])

                        if key == 'Customer Name':
                            summary['customer_name'] = value
                        elif key == 'Mobile Number':
                            summary['mobile_number'] = value
                        elif key == 'Email Address':
                            summary['email_address'] = value
                        elif key == 'Statement Period':
                            summary['statement_period'] = value
                        elif key == 'Request Date':
                            # Parse date
                            request_date = parse_request_date(value)
                            if request_date:
                                summary['request_date'] = request_date
                        elif key == 'Opening Balance':
                            # Parse balance: "Ugx 3,887.80" -> 3887.80
                            balance = parse_balance(value)
                            if balance is not None:
                                summary['opening_balance'] = balance
                        elif key == 'Closing Balance':
                            balance = parse_balance(value)
                            if balance is not None:
                                summary['closing_balance'] = balance

            return summary if summary else None

        finally:
            file_handle.close()

    except Exception as e:
        logger.error(f"Error reading CSV {csv_path}: {e}")
        return None


def parse_request_date(date_str: str) -> Optional[datetime]:
    """Parse request date from various formats."""
    if not date_str:
        return None

    # Clean the date string
    date_str = date_str.strip().strip('"').strip()
    date_str = re.sub(r'\s+', ' ', date_str)

    # Try various date formats
    date_formats = [
        '%d %b, %Y',     # 30 Jul, 2025
        '%d %B, %Y',     # 30 July, 2025
        '%d-%b-%Y',      # 30-Jul-2025
        '%d %b %Y',      # 30 Jul 2025
        '%d-%m-%Y',      # 30-07-2025
        '%Y-%m-%d',      # 2025-07-30
        '%d/%m/%Y',      # 30/07/2025
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse request date: {date_str}")
    return None


def parse_balance(balance_str: str) -> Optional[Decimal]:
    """
    Parse balance from string.
    Example: "Ugx 3,887.80" -> 3887.80
    """
    if not balance_str:
        return None

    try:
        # Remove currency symbols, commas, and whitespace
        balance_str = balance_str.upper()
        balance_str = balance_str.replace('UGX', '').replace('USH', '')
        balance_str = balance_str.replace(',', '').strip()

        if not balance_str:
            return None

        return Decimal(balance_str)
    except Exception as e:
        logger.warning(f"Could not parse balance: {balance_str} - {e}")
        return None


def fill_missing_summary_from_csv(limit: Optional[int] = None, dry_run: bool = False):
    """
    Fill missing summary fields from CSV files for statements without PDF paths.

    Args:
        limit: Maximum number of statements to process (None = all)
        dry_run: If True, don't update database, just report
    """
    logger.info("=" * 80)
    logger.info("FILL SUMMARY FIELDS FROM CSV FILES")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("")

    with engine.connect() as conn:
        # Get statements without PDF paths (format_1, UATL)
        query = text("""
            SELECT run_id, pdf_path,
                   summary_email_address, summary_customer_name,
                   summary_mobile_number, summary_statement_period,
                   summary_request_date, summary_opening_balance,
                   summary_closing_balance
            FROM metadata
            WHERE format = 'format_1'
            AND acc_prvdr_code = 'UATL'
            AND pdf_path IS NULL
            ORDER BY run_id
            {}
        """.format(f"LIMIT {limit}" if limit else ""))

        result = conn.execute(query)
        statements = result.fetchall()

        total = len(statements)
        logger.info(f"Found {total} statements without PDF paths")
        logger.info("")

        if total == 0:
            logger.info("No statements to process")
            return

        # Statistics
        processed = 0
        updated = 0
        failed = 0
        skipped = 0

        # Process each statement
        for i, row in enumerate(statements, 1):
            run_id = row[0]

            if i % 50 == 0:
                logger.info(f"Progress: {i}/{total}...")

            # Look for CSV file
            csv_path = f"/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/{run_id}.csv"

            if not os.path.exists(csv_path):
                logger.warning(f"CSV not found for {run_id}")
                skipped += 1
                continue

            # Extract summary from CSV
            summary = extract_summary_from_csv(csv_path)

            if not summary:
                logger.warning(f"Could not extract summary from {csv_path}")
                failed += 1
                continue

            # Update database
            if not dry_run:
                try:
                    update_query = text("""
                        UPDATE metadata
                        SET summary_email_address = :email,
                            summary_customer_name = :customer_name,
                            summary_mobile_number = :mobile,
                            summary_statement_period = :period,
                            summary_request_date = :request_date,
                            summary_opening_balance = :opening_balance,
                            summary_closing_balance = :closing_balance
                        WHERE run_id = :run_id
                    """)

                    conn.execute(update_query, {
                        'run_id': run_id,
                        'email': summary.get('email_address'),
                        'customer_name': summary.get('customer_name'),
                        'mobile': summary.get('mobile_number'),
                        'period': summary.get('statement_period'),
                        'request_date': summary.get('request_date'),
                        'opening_balance': summary.get('opening_balance'),
                        'closing_balance': summary.get('closing_balance')
                    })
                    conn.commit()

                    updated += 1
                except Exception as e:
                    logger.error(f"Failed to update {run_id}: {e}")
                    failed += 1
                    continue
            else:
                # Dry run - just log what would be updated
                logger.info(f"Would update {run_id}:")
                for key, value in summary.items():
                    logger.info(f"  {key}: {value}")
                updated += 1

            processed += 1

        # Final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total statements: {total}")
        logger.info(f"Processed: {processed}")
        logger.info(f"Updated: {updated}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Skipped (no CSV): {skipped}")
        logger.info("")

        if not dry_run and updated > 0:
            logger.info(f"✓ Successfully updated {updated} statements from CSV files")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fill summary fields from CSV files")
    parser.add_argument('--limit', type=int, help='Limit number of statements to process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no database updates)')

    args = parser.parse_args()

    fill_missing_summary_from_csv(limit=args.limit, dry_run=args.dry_run)
