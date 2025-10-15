#!/usr/bin/env python3
"""
Update header_rows_count for all existing UATL statements
Scans PDFs to detect header rows mixed in transaction data (manipulation indicator)
"""
import os
import sys
import logging
import pandas as pd
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

# Import PDF parsing utilities
from app.services.parsers.pdf_utils import extract_data_from_pdf


def update_header_rows_count():
    """Update header_rows_count for all existing UATL statements"""

    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        # Get all UATL statements that haven't been checked (header_rows_count is NULL or 0)
        result = conn.execute(text("""
            SELECT run_id, pdf_path, acc_number
            FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            AND pdf_path IS NOT NULL
            ORDER BY run_id
        """))

        statements = result.fetchall()
        total = len(statements)

        logger.info(f"Found {total} UATL statements to check for header rows")

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

            # Check if file exists
            if not os.path.exists(pdf_path):
                logger.warning(f"[{idx}/{total}] ❌ {run_id} - File not found: {pdf_path}")
                file_not_found += 1
                continue

            try:
                # Parse PDF to get header_rows_count
                df, extracted_acc, quality_issues_count, header_rows_count = extract_data_from_pdf(pdf_path)

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
                    logger.info(f"[{idx}/{total}] ✅ {run_id} - No header rows detected")

                success_count += 1

                # Progress indicator
                if idx % 100 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total - idx) / rate if rate > 0 else 0
                    logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Speed: {rate:.2f}/s | ETA: {remaining/60:.1f}m")
                    logger.info(f"Stats: {statements_with_headers} statements with header rows ({total_header_rows} total header rows)")

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
        logger.info(f"📁 File not found:           {file_not_found}")
        logger.info("")
        logger.info(f"🚨 Statements with header rows: {statements_with_headers} ({statements_with_headers/total*100:.2f}%)")
        logger.info(f"📊 Total header rows found:     {total_header_rows}")
        logger.info("=" * 80)

        elapsed = datetime.now() - start_time
        logger.info(f"Duration: {elapsed}")
        logger.info(f"Average speed: {total/elapsed.total_seconds():.2f} statements/second")


if __name__ == '__main__':
    update_header_rows_count()
