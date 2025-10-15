#!/usr/bin/env python3
"""
Update header_rows_count for all existing UATL statements
Uses existing database records instead of re-parsing PDFs (MUCH FASTER!)
"""
import os
import sys
import logging
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


def is_header_row_from_db(row):
    """
    Detect if a database row is actually a header row (manipulation indicator)

    Checks for header keywords in transaction fields
    """
    # Get text fields
    txn_id = str(row['txn_id']).lower()
    description = str(row['description']).lower()
    txn_type = str(row['txn_type']).lower() if row['txn_type'] else ''
    amount = str(row['amount']) if row['amount'] else ''

    # Combine all text
    combined_text = f"{txn_id} {description} {txn_type}"

    # Header keywords that indicate manipulation
    header_keywords = [
        'transaction id', 'transation id', 'transaction type',
        'date', 'description', 'status', 'amount', 'fee', 'balance',
        'mobile number', 'from account', 'to account',
        'txn_id', 'txn_type', 'txn_date'
    ]

    # Count keyword matches
    keyword_count = sum(1 for keyword in header_keywords if keyword in combined_text)

    # If 2+ header keywords found, it's likely a header row
    if keyword_count >= 2:
        return True

    # Check if amount field contains header text instead of a number
    if amount.lower() in ['amount', 'balance', 'fee', 'total']:
        return True

    # Check if description is suspiciously short and matches header pattern
    if description in ['date', 'description', 'status', 'amount', 'fee', 'balance']:
        return True

    return False


def update_header_rows_count_fast():
    """Update header_rows_count by analyzing existing database records"""

    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        # Get all UATL statements
        result = conn.execute(text("""
            SELECT run_id, acc_number, num_rows
            FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            ORDER BY run_id
        """))

        statements = result.fetchall()
        total = len(statements)

        logger.info(f"Found {total} UATL statements to analyze")
        logger.info("Analyzing existing database records (fast method - no PDF parsing!)")

        success_count = 0
        error_count = 0
        total_header_rows = 0
        statements_with_headers = 0

        start_time = datetime.now()

        for idx, row in enumerate(statements, 1):
            run_id = row[0]
            acc_number = row[1]
            num_rows = row[2]

            try:
                # Get all transactions for this run_id
                result = conn.execute(text("""
                    SELECT txn_id, description, txn_type, amount
                    FROM uatl_raw_statements
                    WHERE run_id = :run_id
                """), {'run_id': run_id})

                transactions = result.fetchall()

                # Count header rows
                header_rows_count = 0
                for txn in transactions:
                    txn_dict = {
                        'txn_id': txn[0],
                        'description': txn[1],
                        'txn_type': txn[2],
                        'amount': txn[3]
                    }
                    if is_header_row_from_db(txn_dict):
                        header_rows_count += 1

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

                if header_rows_count > 0:
                    logger.info(f"[{idx}/{total}] 🚨 {run_id} - Found {header_rows_count} header rows (MANIPULATION)")
                    statements_with_headers += 1
                    total_header_rows += header_rows_count
                else:
                    if idx % 100 == 0:
                        logger.info(f"[{idx}/{total}] ✅ Clean batch")

                success_count += 1

                # Progress indicator every 500 statements
                if idx % 500 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total - idx) / rate if rate > 0 else 0
                    logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Speed: {rate:.1f}/s | ETA: {remaining/60:.1f}m")
                    logger.info(f"Stats so far: {statements_with_headers} statements with header rows ({total_header_rows} total header rows)")

            except Exception as e:
                logger.error(f"[{idx}/{total}] ❌ {run_id} - Error: {e}")
                error_count += 1
                continue

        # Final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total statements:           {total}")
        logger.info(f"✅ Successfully updated:     {success_count}")
        logger.info(f"❌ Errors:                   {error_count}")
        logger.info("")
        logger.info(f"🚨 Statements with header rows: {statements_with_headers} ({statements_with_headers/total*100:.2f}%)")
        logger.info(f"📊 Total header rows found:     {total_header_rows}")
        logger.info("=" * 80)

        elapsed = datetime.now() - start_time
        logger.info(f"Duration: {elapsed}")
        logger.info(f"Average speed: {total/elapsed.total_seconds():.1f} statements/second")


if __name__ == '__main__':
    update_header_rows_count_fast()
