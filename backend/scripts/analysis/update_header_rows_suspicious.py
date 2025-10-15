#!/usr/bin/env python3
"""
Update header_rows_count for suspicious UATL format_2 statements
Only scans PDFs where balance_match failed and balance_diff_changes is high
"""
import os
import sys
import logging
import pdfplumber
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3307')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')


def is_header_row(row_text: str) -> bool:
    """
    Check if text looks like a table header row
    """
    row_lower = row_text.lower()

    # Header keywords that indicate this is a header row
    header_patterns = [
        'transaction id',
        'transation id',  # Common typo
        'date transaction',
        'date/time',
        'transaction type',
        'description',
        'from account',
        'to account',
        'mobile number',
    ]

    # If row contains multiple header keywords, it's likely a header
    matches = sum(1 for pattern in header_patterns if pattern in row_lower)
    return matches >= 2


def count_header_rows_in_pdf(pdf_path: str) -> int:
    """
    Scan all pages in PDF and count how many times header rows appear
    If header appears 2+ times, the PDF has been edited (manipulation)
    """
    header_count = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text from page
                text = page.extract_text()
                if not text:
                    continue

                # Split into lines
                lines = text.split('\n')

                # Check each line for header pattern
                for line in lines:
                    if is_header_row(line):
                        header_count += 1
                        logger.debug(f"  Found header on page {page_num}: {line[:80]}")

        return header_count

    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return 0


def update_suspicious_statements():
    """
    Update header_rows_count only for suspicious format_2 statements
    """

    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        # Get suspicious format_2 statements
        # Criteria: format_2 with quality issues
        logger.info("Finding suspicious format_2 statements...")

        result = conn.execute(text("""
            SELECT
                run_id,
                pdf_path,
                acc_number,
                format,
                quality_issues_count
            FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            AND format = 'format_2'
            AND pdf_path IS NOT NULL
            AND quality_issues_count > 0
            ORDER BY quality_issues_count DESC
        """))

        statements = result.fetchall()
        total = len(statements)

        logger.info(f"Found {total} suspicious format_2 statements to scan")
        logger.info("Scanning for duplicate header rows (indicates PDF manipulation)...")
        logger.info("")

        success_count = 0
        error_count = 0
        file_not_found = 0
        total_header_rows = 0
        statements_with_headers = 0

        start_time = datetime.now()

        for idx, row in enumerate(statements, 1):
            run_id = row[0]
            pdf_path = row[1]
            acc_number = row[2]
            format_type = row[3]
            quality_issues_count = row[4]

            # Check if file exists
            if not os.path.exists(pdf_path):
                logger.warning(f"[{idx}/{total}] ❌ {run_id} - File not found")
                file_not_found += 1
                continue

            try:
                # Scan PDF for header rows
                header_rows_count = count_header_rows_in_pdf(pdf_path)

                # Update metadata
                conn.execute(text("""
                    UPDATE metadata
                    SET header_rows_count = :header_rows_count
                    WHERE run_id = :run_id
                """), {
                    'header_rows_count': header_rows_count,
                    'run_id': run_id
                })
                conn.commit()

                if header_rows_count >= 2:
                    logger.info(
                        f"[{idx}/{total}] 🚨 {run_id} - MANIPULATION DETECTED! "
                        f"{header_rows_count} header rows found "
                        f"(quality_issues={quality_issues_count})"
                    )
                    statements_with_headers += 1
                    total_header_rows += header_rows_count
                elif header_rows_count == 1:
                    logger.info(f"[{idx}/{total}] ✅ {run_id} - Clean (1 header row is normal)")
                else:
                    logger.info(f"[{idx}/{total}] ⚠️  {run_id} - No header rows found (unusual)")

                success_count += 1

                # Progress indicator
                if idx % 50 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total - idx) / rate if rate > 0 else 0
                    logger.info("")
                    logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Speed: {rate:.2f}/s | ETA: {remaining/60:.1f}m")
                    logger.info(f"Manipulation found: {statements_with_headers} statements ({statements_with_headers/idx*100:.1f}%)")
                    logger.info("")

            except Exception as e:
                logger.error(f"[{idx}/{total}] ❌ {run_id} - Error: {e}")
                error_count += 1
                continue

        # Final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY - SUSPICIOUS FORMAT_2 STATEMENTS")
        logger.info("=" * 80)
        logger.info(f"Total suspicious statements:    {total}")
        logger.info(f"✅ Successfully scanned:         {success_count}")
        logger.info(f"❌ Errors:                       {error_count}")
        logger.info(f"📁 File not found:               {file_not_found}")
        logger.info("")
        logger.info(f"🚨 MANIPULATED statements:       {statements_with_headers} ({statements_with_headers/total*100:.2f}%)")
        logger.info(f"📊 Total header rows found:      {total_header_rows}")
        logger.info("=" * 80)

        elapsed = datetime.now() - start_time
        logger.info(f"Duration: {elapsed}")
        logger.info(f"Average speed: {success_count/elapsed.total_seconds():.2f} statements/second")


if __name__ == '__main__':
    update_suspicious_statements()
