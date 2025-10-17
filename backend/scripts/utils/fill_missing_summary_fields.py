#!/usr/bin/env python3
"""
Fill missing summary fields for Airtel format_1 PDF statements.
Uses pypdfium2 for fast PDF text extraction.

Summary fields include:
- Email address
- Customer name
- Mobile number
- Statement period
- Request date
- Opening balance
- Closing balance (from summary section, not last transaction)
"""
import os
import re
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pypdfium2 as pdfium
import pdfplumber

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')
Session = sessionmaker(bind=engine)


def extract_text_from_pdf_page(pdf_path: str, page_num: int = 0) -> Optional[str]:
    """
    Extract text from a specific PDF page using pypdfium2.
    Fast and efficient.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)

    Returns:
        Extracted text or None if error
    """
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        if page_num >= len(pdf):
            logger.warning(f"Page {page_num} not found in {pdf_path}")
            return None

        page = pdf[page_num]
        textpage = page.get_textpage()
        text = textpage.get_text_range()

        # Cleanup
        textpage.close()
        page.close()
        pdf.close()

        return text
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        return None


def extract_balances_with_coordinates(pdf_path: str) -> Dict[str, Optional[float]]:
    """
    Extract balance values using coordinate-based extraction with pdfplumber.
    Some PDFs have balance values positioned separately from their labels.

    Returns dict with: opening_balance, closing_balance, total_credit, total_debit
    """
    result = {
        'opening_balance': None,
        'closing_balance': None,
        'total_credit': None,
        'total_debit': None
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return result

            first_page = pdf.pages[0]
            words = first_page.extract_words()

            # Look for balance values in the summary section (y between 150-250, x > 300)
            for word in words:
                y = word['top']
                x = word['x0']
                text = word['text']

                # Check if in summary section
                if 150 <= y <= 250 and x > 300:
                    # Try to parse as a number (with or without commas)
                    if any(c.isdigit() for c in text):
                        try:
                            # Remove commas and parse
                            value = float(text.replace(',', ''))

                            # Map based on y-coordinate ranges
                            if 165 <= y <= 177:  # Opening Balance line
                                result['opening_balance'] = value
                            elif 183 <= y <= 195:  # Closing Balance line
                                result['closing_balance'] = value
                            elif 201 <= y <= 213:  # Total Credit line
                                result['total_credit'] = value
                            elif 219 <= y <= 231:  # Total Debit line
                                result['total_debit'] = value
                        except ValueError:
                            pass

            return result

    except Exception as e:
        logger.warning(f"Could not extract balances with coordinates from {pdf_path}: {e}")
        return result


def extract_email_address(text: str) -> Optional[str]:
    """Extract email address from text."""
    # Pattern: "Email Address:" followed by the email
    email_pattern = re.compile(r'Email\s+Address\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.I)
    match = email_pattern.search(text)

    if match:
        return match.group(1)

    # Alternative: search for any email pattern
    general_email_pattern = re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b')
    matches = general_email_pattern.findall(text)

    if matches:
        return matches[0]

    return None


def extract_customer_name(text: str) -> Optional[str]:
    """Extract customer name from text."""
    # Pattern: "Customer Name:" followed by the name
    pattern = re.compile(r'Customer\s+Name\s*:\s*(.+?)(?:\n|Mobile Number)', re.I | re.S)
    match = pattern.search(text)

    if match:
        name = match.group(1).strip()
        # Clean up any extra whitespace
        name = re.sub(r'\s+', ' ', name)
        return name

    return None


def extract_mobile_number(text: str) -> Optional[str]:
    """Extract mobile number from text (from header, not account field)."""
    # Pattern: "Mobile Number:" followed by the number
    pattern = re.compile(r'Mobile\s+Number\s*:\s*(\d+)', re.I)
    match = pattern.search(text)

    if match:
        return match.group(1).strip()

    return None


def extract_statement_period(text: str) -> Optional[str]:
    """Extract statement period from text."""
    # Pattern: "Statement Period:" followed by the date range
    pattern = re.compile(r'Statement\s+Period\s*:\s*(.+?)(?:\n|Request Date)', re.I | re.S)
    match = pattern.search(text)

    if match:
        period = match.group(1).strip()
        # Clean up any extra whitespace or newlines
        period = re.sub(r'\s+', ' ', period)
        return period

    return None


def extract_request_date(text: str) -> Optional[datetime]:
    """Extract request date from text."""
    # Pattern: "Request Date:" followed by the date
    pattern = re.compile(r'Request\s+Date\s*:\s*(.+?)(?:\n|$)', re.I)
    match = pattern.search(text)

    if match:
        date_str = match.group(1).strip()
        # Clean up
        date_str = re.sub(r'\s+', ' ', date_str)

        # Try to parse the date
        date_formats = [
            '%d-%b-%Y',      # 01-Sep-2025
            '%d %b, %Y',     # 23 Jul, 2025 (with comma)
            '%d %b %Y',      # 01 Sep 2025
            '%d-%m-%Y',      # 01-09-2025
            '%Y-%m-%d',      # 2025-09-01
            '%d/%m/%Y',      # 01/09/2025
            '%d %B %Y',      # 01 September 2025
            '%d %B, %Y',     # 01 September, 2025 (with comma)
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse request date: {date_str}")
        return None

    return None


def extract_summary_balances(text: str) -> tuple[Optional[float], Optional[float]]:
    """
    Extract opening and closing balances from the summary section.

    Format 1 PDFs typically have a summary section with:
    - Opening Balance: XXXX
    - Closing Balance: YYYY

    Returns:
        Tuple of (opening_balance, closing_balance)
    """
    opening_balance = None
    closing_balance = None

    # Pattern for opening balance
    opening_pattern = re.compile(r'Opening\s+Balance\s*:\s*UGX\s*([\d,]+\.?\d*)', re.I)
    opening_match = opening_pattern.search(text)

    if opening_match:
        opening_str = opening_match.group(1).replace(',', '')
        try:
            opening_balance = float(opening_str)
        except ValueError:
            logger.warning(f"Could not parse opening balance: {opening_str}")

    # Pattern for closing balance
    closing_pattern = re.compile(r'Closing\s+Balance\s*:\s*UGX\s*([\d,]+\.?\d*)', re.I)
    closing_match = closing_pattern.search(text)

    if closing_match:
        closing_str = closing_match.group(1).replace(',', '')
        try:
            closing_balance = float(closing_str)
        except ValueError:
            logger.warning(f"Could not parse closing balance: {closing_str}")

    # Alternative pattern without "UGX"
    if opening_balance is None:
        opening_pattern = re.compile(r'Opening\s+Balance\s*:\s*([\d,]+\.?\d*)', re.I)
        opening_match = opening_pattern.search(text)

        if opening_match:
            opening_str = opening_match.group(1).replace(',', '')
            try:
                opening_balance = float(opening_str)
            except ValueError:
                pass

    if closing_balance is None:
        closing_pattern = re.compile(r'Closing\s+Balance\s*:\s*([\d,]+\.?\d*)', re.I)
        closing_match = closing_pattern.search(text)

        if closing_match:
            closing_str = closing_match.group(1).replace(',', '')
            try:
                closing_balance = float(closing_str)
            except ValueError:
                pass

    return opening_balance, closing_balance


def extract_all_summary_fields(pdf_path: str) -> Dict[str, Any]:
    """
    Extract all summary fields from format_1 PDF using pypdfium2.

    Returns:
        Dictionary with extracted fields
    """
    # Extract text from first page
    text = extract_text_from_pdf_page(pdf_path, page_num=0)

    if not text:
        return {}

    # Extract all fields
    result = {}

    email = extract_email_address(text)
    if email:
        result['summary_email_address'] = email

    customer_name = extract_customer_name(text)
    if customer_name:
        result['summary_customer_name'] = customer_name

    mobile_number = extract_mobile_number(text)
    if mobile_number:
        result['summary_mobile_number'] = mobile_number

    statement_period = extract_statement_period(text)
    if statement_period:
        result['summary_statement_period'] = statement_period

    request_date = extract_request_date(text)
    if request_date:
        result['summary_request_date'] = request_date.date()

    opening_balance, closing_balance = extract_summary_balances(text)
    if opening_balance is not None:
        result['summary_opening_balance'] = Decimal(str(opening_balance))
    if closing_balance is not None:
        result['summary_closing_balance'] = Decimal(str(closing_balance))

    # If balances are still missing, try coordinate-based extraction
    # (Some PDFs have balance values positioned separately from labels)
    if opening_balance is None or closing_balance is None:
        coord_balances = extract_balances_with_coordinates(pdf_path)
        if coord_balances['opening_balance'] is not None and opening_balance is None:
            result['summary_opening_balance'] = Decimal(str(coord_balances['opening_balance']))
        if coord_balances['closing_balance'] is not None and closing_balance is None:
            result['summary_closing_balance'] = Decimal(str(coord_balances['closing_balance']))

    return result


def resolve_pdf_path(pdf_path: str) -> Optional[str]:
    """
    Resolve PDF path - tries multiple common locations.

    Args:
        pdf_path: Original PDF path from database

    Returns:
        Resolved path if found, None otherwise
    """
    # Try the original path first
    if os.path.exists(pdf_path):
        return pdf_path

    # Check if path needs /backend/ inserted
    # Pattern: /home/.../airtel_fraud_detection/docs/... -> /home/.../airtel_fraud_detection/backend/docs/...
    if '/airtel_fraud_detection/docs/' in pdf_path and '/backend/' not in pdf_path:
        fixed_path = pdf_path.replace('/airtel_fraud_detection/docs/', '/airtel_fraud_detection/backend/docs/')
        if os.path.exists(fixed_path):
            return fixed_path

    # Try alternative locations
    filename = os.path.basename(pdf_path)
    alternative_dirs = [
        '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/',
        '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/uploaded_pdfs/',
        '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/statements/',
        '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/statements/special/',
    ]

    for alt_dir in alternative_dirs:
        alt_path = os.path.join(alt_dir, filename)
        if os.path.exists(alt_path):
            return alt_path

    return None


def fill_missing_summary_fields(limit: Optional[int] = None, dry_run: bool = False, reprocess_all: bool = False):
    """
    Fill missing summary fields for format_1 statements.

    Args:
        limit: Maximum number of statements to process (None = all)
        dry_run: If True, don't update database, just report
        reprocess_all: If True, reprocess all format_1 statements (not just missing fields)
    """
    with engine.connect() as conn:
        # Find format_1 statements with missing fields and valid PDF paths
        if reprocess_all:
            # Process all format_1 statements
            query = text("""
                SELECT run_id, pdf_path,
                       summary_email_address,
                       summary_customer_name,
                       summary_mobile_number,
                       summary_statement_period,
                       summary_request_date,
                       summary_opening_balance,
                       summary_closing_balance
                FROM metadata
                WHERE format = 'format_1'
                AND acc_prvdr_code = 'UATL'
                AND pdf_path IS NOT NULL
                ORDER BY run_id
            """)
        else:
            # Only process statements with missing fields
            query = text("""
                SELECT run_id, pdf_path,
                       summary_email_address,
                       summary_customer_name,
                       summary_mobile_number,
                       summary_statement_period,
                       summary_request_date,
                       summary_opening_balance,
                       summary_closing_balance
                FROM metadata
                WHERE format = 'format_1'
                AND acc_prvdr_code = 'UATL'
                AND pdf_path IS NOT NULL
                AND (
                    summary_email_address IS NULL OR
                    summary_customer_name IS NULL OR
                    summary_mobile_number IS NULL OR
                    summary_statement_period IS NULL OR
                    summary_request_date IS NULL OR
                    summary_opening_balance IS NULL OR
                    summary_closing_balance IS NULL
                )
                ORDER BY run_id
            """)

        if limit:
            query = text(str(query) + f" LIMIT {limit}")

        result = conn.execute(query)
        statements = result.fetchall()

        if reprocess_all:
            logger.info(f"Found {len(statements)} format_1 statements to reprocess (including those with existing fields)")
        else:
            logger.info(f"Found {len(statements)} format_1 statements with missing summary fields")

        if dry_run:
            logger.info("DRY RUN MODE - No database updates will be made")

        updated_count = 0
        failed_count = 0
        skipped_count = 0

        fields_extracted = {
            'email': 0,
            'customer_name': 0,
            'mobile_number': 0,
            'statement_period': 0,
            'request_date': 0,
            'opening_balance': 0,
            'closing_balance': 0,
        }

        for i, row in enumerate(statements, 1):
            run_id = row[0]
            pdf_path = row[1]

            # Check which fields are missing
            missing_fields = []
            if row[2] is None:
                missing_fields.append('email')
            if row[3] is None:
                missing_fields.append('customer_name')
            if row[4] is None:
                missing_fields.append('mobile')
            if row[5] is None:
                missing_fields.append('period')
            if row[6] is None:
                missing_fields.append('request_date')
            if row[7] is None:
                missing_fields.append('opening_balance')
            if row[8] is None:
                missing_fields.append('closing_balance')

            logger.info(f"[{i}/{len(statements)}] Processing {run_id} (missing: {', '.join(missing_fields)})")

            # Resolve PDF path
            resolved_path = resolve_pdf_path(pdf_path)
            if not resolved_path:
                logger.warning(f"  PDF not found: {pdf_path}")
                skipped_count += 1
                continue

            # Update database path if it was resolved to a different location
            path_updated = False
            if resolved_path != pdf_path:
                logger.info(f"  Path corrected: {pdf_path} -> {resolved_path}")
                if not dry_run:
                    conn.execute(text("UPDATE metadata SET pdf_path = :new_path WHERE run_id = :run_id"),
                                {'new_path': resolved_path, 'run_id': run_id})
                    conn.commit()
                path_updated = True

            # Extract summary fields
            try:
                extracted = extract_all_summary_fields(resolved_path)

                if not extracted:
                    logger.warning(f"  No summary fields extracted from {resolved_path}")
                    if path_updated:
                        # We updated the path but couldn't extract, still count as partial success
                        logger.info(f"  ✓ Path updated in database")
                    failed_count += 1
                    continue

                # Build update query
                update_parts = []
                params = {'run_id': run_id}

                if 'summary_email_address' in extracted:
                    update_parts.append("summary_email_address = :email")
                    params['email'] = extracted['summary_email_address']
                    fields_extracted['email'] += 1
                    logger.info(f"  ✓ Email: {extracted['summary_email_address']}")

                if 'summary_customer_name' in extracted:
                    update_parts.append("summary_customer_name = :customer_name")
                    params['customer_name'] = extracted['summary_customer_name']
                    fields_extracted['customer_name'] += 1
                    logger.info(f"  ✓ Customer: {extracted['summary_customer_name']}")

                if 'summary_mobile_number' in extracted:
                    update_parts.append("summary_mobile_number = :mobile")
                    params['mobile'] = extracted['summary_mobile_number']
                    fields_extracted['mobile_number'] += 1
                    logger.info(f"  ✓ Mobile: {extracted['summary_mobile_number']}")

                if 'summary_statement_period' in extracted:
                    update_parts.append("summary_statement_period = :period")
                    params['period'] = extracted['summary_statement_period']
                    fields_extracted['statement_period'] += 1
                    logger.info(f"  ✓ Period: {extracted['summary_statement_period']}")

                if 'summary_request_date' in extracted:
                    update_parts.append("summary_request_date = :request_date")
                    params['request_date'] = extracted['summary_request_date']
                    fields_extracted['request_date'] += 1
                    logger.info(f"  ✓ Request Date: {extracted['summary_request_date']}")

                if 'summary_opening_balance' in extracted:
                    update_parts.append("summary_opening_balance = :opening_balance")
                    params['opening_balance'] = extracted['summary_opening_balance']
                    fields_extracted['opening_balance'] += 1
                    logger.info(f"  ✓ Opening Balance: {extracted['summary_opening_balance']}")

                if 'summary_closing_balance' in extracted:
                    update_parts.append("summary_closing_balance = :closing_balance")
                    params['closing_balance'] = extracted['summary_closing_balance']
                    fields_extracted['closing_balance'] += 1
                    logger.info(f"  ✓ Closing Balance: {extracted['summary_closing_balance']}")

                if update_parts and not dry_run:
                    update_query = text(f"""
                        UPDATE metadata
                        SET {', '.join(update_parts)}
                        WHERE run_id = :run_id
                    """)

                    conn.execute(update_query, params)
                    conn.commit()
                    updated_count += 1
                elif update_parts and dry_run:
                    logger.info(f"  [DRY RUN] Would update {len(update_parts)} fields")
                    updated_count += 1
                else:
                    logger.warning(f"  No new fields extracted")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  Error processing {run_id}: {e}")
                failed_count += 1
                continue

        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total statements processed: {len(statements)}")
        logger.info(f"Successfully updated: {updated_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Skipped (PDF not found): {skipped_count}")
        logger.info("")
        logger.info("Fields extracted:")
        logger.info(f"  Email addresses: {fields_extracted['email']}")
        logger.info(f"  Customer names: {fields_extracted['customer_name']}")
        logger.info(f"  Mobile numbers: {fields_extracted['mobile_number']}")
        logger.info(f"  Statement periods: {fields_extracted['statement_period']}")
        logger.info(f"  Request dates: {fields_extracted['request_date']}")
        logger.info(f"  Opening balances: {fields_extracted['opening_balance']}")
        logger.info(f"  Closing balances: {fields_extracted['closing_balance']}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fill missing summary fields for Airtel format_1 PDFs')
    parser.add_argument('--limit', type=int, help='Maximum number of statements to process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no database updates)')
    parser.add_argument('--reprocess-all', action='store_true', help='Reprocess all format_1 statements (not just missing fields)')

    args = parser.parse_args()

    fill_missing_summary_fields(limit=args.limit, dry_run=args.dry_run, reprocess_all=args.reprocess_all)
