#!/usr/bin/env python3
"""
Scan format_2 statements for header row manipulation
Checks for:
1. Pages with header_rows != 1 (either 0 or >1)
2. Headers not at the first content line (after blank lines/page numbers)
Stores manipulation count in header_row_manipulation_count column
"""
import os
import sys
import logging
import json
import pypdfium2 as pdfium  # 32x faster than pdfplumber with same accuracy!
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
DB_PORT = os.getenv('DB_PORT', '3306')
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


def is_page_number(text: str) -> bool:
    """
    Check if text looks like a page number (single number, usually small)
    """
    text = text.strip()
    if not text:
        return False
    try:
        num = int(text)
        return 1 <= num <= 999  # Reasonable page number range
    except:
        return False


def find_first_content_line(lines: list) -> int:
    """
    Find the index of the first line that contains actual content
    (not blank, not just a page number)

    Returns: index of first content line, or 0 if none found
    """
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped and not is_page_number(line_stripped):
            return idx
    return 0


def check_pdf_for_manipulation(pdf_path: str) -> tuple:
    """
    Scan PDF and check for header manipulation (Format_2 only):
    1. Any page where header_rows != 1 (either 0 or >1)
    2. Any page where header is NOT the first content row (skips blank lines and page numbers)
       - Header in middle of data = manipulation

    Uses pypdfium2 (32x faster than pdfplumber with same accuracy)

    Returns: (is_manipulated, bad_pages_dict, headers_per_page_list)
    """
    headers_per_page = []
    bad_pages = {}  # page_num: reason

    try:
        pdf = pdfium.PdfDocument(pdf_path)

        for page_num in range(len(pdf)):
            page = pdf[page_num]
            textpage = page.get_textpage()
            text = textpage.get_text_range()

            page_index = page_num + 1  # Convert to 1-indexed

            if not text:
                headers_per_page.append(0)
                continue

            # Split into lines
            lines = text.split('\n')
            page_header_count = 0
            header_positions = []  # Track which line numbers have headers

            for line_num, line in enumerate(lines):
                if is_header_row(line):
                    page_header_count += 1
                    header_positions.append(line_num)

            headers_per_page.append(page_header_count)

            # Check for manipulation on this page (Format_2 logic)
            # Flag if header_rows != 1 (either 0 or >1)
            if page_header_count == 0:
                bad_pages[page_index] = f"No header row found"
            elif page_header_count > 1:
                # Multiple headers on same page = manipulation
                bad_pages[page_index] = f"{page_header_count} headers (positions: {header_positions})"
            elif page_index > 1 and page_header_count == 1:
                # For pages 2+, header should be at the first content line
                # (skip blank lines and page numbers)
                expected_position = find_first_content_line(lines)

                if header_positions[0] > expected_position:
                    # Header NOT at expected position = manipulation
                    bad_pages[page_index] = f"Header at line {header_positions[0]} (expected at line {expected_position})"

        is_manipulated = len(bad_pages) > 0

        return is_manipulated, bad_pages, headers_per_page

    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return False, {}, []


def scan_suspicious_statements():
    """
    Scan suspicious format_2 statements and report findings
    """

    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        # Get suspicious format_2 statements
        logger.info("Finding suspicious format_2 statements...")

        # Toggle this to test different statement sets
        test_clean_statements = os.getenv('TEST_CLEAN', '').lower() == 'true'

        if test_clean_statements:
            # Test statements where balance_match = 1 (should have NO manipulation)
            result = conn.execute(text("""
                SELECT
                    m.run_id,
                    m.pdf_path,
                    m.acc_number,
                    m.format,
                    s.balance_match,
                    s.balance_diff_change_ratio
                FROM metadata m
                LEFT JOIN summary s ON m.run_id = s.run_id
                WHERE m.acc_prvdr_code = 'UATL'
                AND m.format = 'format_2'
                AND m.pdf_path IS NOT NULL
                AND s.balance_match = 1
                ORDER BY RAND()
                LIMIT 100
            """))
        else:
            # Scan ALL format_2 UATL statements
            result = conn.execute(text("""
                SELECT
                    m.run_id,
                    m.pdf_path,
                    m.acc_number,
                    m.format,
                    s.balance_match,
                    s.balance_diff_change_ratio
                FROM metadata m
                LEFT JOIN summary s ON m.run_id = s.run_id
                WHERE m.acc_prvdr_code = 'UATL'
                AND m.format = 'format_2'
                AND m.pdf_path IS NOT NULL
                ORDER BY s.balance_diff_change_ratio DESC
            """))

        statements = result.fetchall()
        total = len(statements)

        if test_clean_statements:
            logger.info(f"Found {total} statements with balance_match=Success (TEST MODE)")
        else:
            logger.info(f"Found {total} format_2 UATL statements")
        logger.info("Scanning for header row manipulation (0 headers, >1 headers, or misplaced headers)...")
        logger.info("Results will be saved to header_manipulation_results.json")
        logger.info(f"Estimated duration: {total/10/60:.1f} minutes at ~10 statements/sec")
        logger.info("")

        manipulated_statements = []
        clean_statements = []
        file_not_found = []
        all_results = []  # Store all results for JSON export

        start_time = datetime.now()

        for idx, row in enumerate(statements, 1):
            run_id = row[0]
            pdf_path = row[1]
            acc_number = row[2]
            format_type = row[3]
            balance_match = row[4]
            balance_diff_change_ratio = row[5]

            # Fix path if needed (database paths may be from Docker or missing "backend/")
            if not os.path.exists(pdf_path):
                # Try multiple path variations
                alt_paths = [
                    pdf_path.replace('/app/', '/home/ebran/Developer/projects/airtel_fraud_detection/backend/'),
                    pdf_path.replace('/airtel_fraud_detection/', '/airtel_fraud_detection/backend/'),
                ]
                found = False
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        pdf_path = alt_path
                        found = True
                        break

                if not found:
                    logger.warning(f"[{idx}/{total}] ❌ {run_id} - File not found")
                    file_not_found.append(run_id)
                    continue

            try:
                # Check for manipulation
                is_manipulated, bad_pages_dict, headers_per_page = check_pdf_for_manipulation(pdf_path)

                # Store result for JSON export
                result_entry = {
                    'run_id': run_id,
                    'acc_number': acc_number,
                    'pdf_path': pdf_path,
                    'balance_match': balance_match,
                    'balance_diff_change_ratio': float(balance_diff_change_ratio) if balance_diff_change_ratio else 0,
                    'is_manipulated': is_manipulated,
                    'manipulated_pages_count': len(bad_pages_dict),
                    'bad_pages': {str(k): v for k, v in bad_pages_dict.items()},  # Convert keys to strings for JSON
                    'total_pages': len(headers_per_page),
                    'headers_per_page': headers_per_page,
                }
                all_results.append(result_entry)

                if is_manipulated:
                    logger.info(
                        f"[{idx}/{total}] 🚨 {run_id} - MANIPULATION! "
                        f"{len(bad_pages_dict)} pages flagged "
                        f"(change_ratio={balance_diff_change_ratio:.4f})"
                    )
                    for page_num, reason in bad_pages_dict.items():
                        logger.info(f"      Page {page_num}: {reason}")

                    manipulated_statements.append({
                        'run_id': run_id,
                        'bad_pages': bad_pages_dict,
                        'headers_per_page': headers_per_page,
                        'change_ratio': balance_diff_change_ratio
                    })
                else:
                    num_pages = len(headers_per_page)
                    total_headers = sum(headers_per_page)
                    logger.info(
                        f"[{idx}/{total}] ✅ {run_id} - Clean "
                        f"({num_pages} pages, {total_headers} headers total)"
                    )
                    clean_statements.append(run_id)

                # Progress indicator
                if idx % 50 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total - idx) / rate if rate > 0 else 0
                    logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Speed: {rate:.2f}/s | ETA: {remaining/60:.1f}m | Manipulated: {len(manipulated_statements)}")
                    logger.info("")

            except Exception as e:
                logger.error(f"[{idx}/{total}] ❌ {run_id} - Error: {e}")
                continue

        # Final report
        logger.info("")
        logger.info("=" * 80)
        logger.info("FINAL REPORT - HEADER ROW MANIPULATION SCAN")
        logger.info("=" * 80)
        logger.info(f"Total suspicious statements:    {total}")
        logger.info(f"📁 File not found:               {len(file_not_found)}")
        logger.info(f"✅ Clean statements:             {len(clean_statements)}")
        logger.info(f"🚨 MANIPULATED statements:       {len(manipulated_statements)}")
        logger.info("")

        if manipulated_statements:
            logger.info("=" * 80)
            logger.info("MANIPULATED STATEMENTS")
            logger.info("=" * 80)
            for item in manipulated_statements:
                logger.info(f"run_id: {item['run_id']}")
                logger.info(f"  Balance change ratio: {item['change_ratio']:.4f}")
                logger.info(f"  Flagged pages:")
                for page_num, reason in item['bad_pages'].items():
                    logger.info(f"    Page {page_num}: {reason}")
                logger.info(f"  Headers per page: {item['headers_per_page']}")
                logger.info("")

        logger.info("=" * 80)
        elapsed = datetime.now() - start_time
        logger.info(f"Duration: {elapsed}")
        logger.info(f"Average speed: {total/elapsed.total_seconds():.2f} statements/second")

        # Save results to JSON file
        output_file = 'header_manipulation_results.json'
        output_data = {
            'scan_date': datetime.now().isoformat(),
            'total_scanned': total,
            'file_not_found': len(file_not_found),
            'clean_statements': len(clean_statements),
            'manipulated_statements': len(manipulated_statements),
            'duration_seconds': elapsed.total_seconds(),
            'results': all_results,
            'summary': {
                'manipulated_run_ids': [item['run_id'] for item in manipulated_statements],
                'clean_run_ids': clean_statements,
                'not_found_run_ids': file_not_found,
            }
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 80)
        logger.info("")

        # Update database with manipulation counts
        logger.info("Updating database with header_row_manipulation_count...")
        update_count = 0
        for result_entry in all_results:
            run_id = result_entry['run_id']
            manipulation_count = result_entry['manipulated_pages_count']

            conn.execute(text("""
                UPDATE metadata
                SET header_row_manipulation_count = :manipulation_count
                WHERE run_id = :run_id
            """), {'manipulation_count': manipulation_count, 'run_id': run_id})
            update_count += 1

        conn.commit()
        logger.info(f"✅ Updated {update_count} records in database")
        logger.info("")


if __name__ == '__main__':
    scan_suspicious_statements()
