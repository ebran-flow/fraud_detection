#!/usr/bin/env python3
"""
Update MIME types in metadata table to differentiate between:
- Regular CSV files: text/csv
- Gzipped CSV files: application/gzip or application/x-gzip
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

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


def update_csv_mime_types(dry_run=False):
    """
    Update MIME types for CSV files:
    - *.csv.gz -> application/gzip
    - *.csv -> text/csv (keep as is)
    """

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            # Find all CSV files that need updating
            query = text("""
                SELECT run_id, pdf_path, mime
                FROM metadata
                WHERE pdf_path LIKE '%.csv%'
            """)

            result = conn.execute(query)
            rows = result.fetchall()

            logger.info(f"Found {len(rows)} CSV-related files")

            # Categorize files
            gzip_csv_files = []
            regular_csv_files = []

            for row in rows:
                run_id, pdf_path, current_mime = row

                if pdf_path and pdf_path.endswith('.csv.gz'):
                    # Gzipped CSV file
                    if current_mime != 'application/gzip':
                        gzip_csv_files.append((run_id, pdf_path, current_mime))
                elif pdf_path and pdf_path.endswith('.csv'):
                    # Regular CSV file
                    if current_mime != 'text/csv':
                        regular_csv_files.append((run_id, pdf_path, current_mime))

            logger.info(f"\nFiles to update:")
            logger.info(f"  Gzipped CSV files (*.csv.gz -> application/gzip): {len(gzip_csv_files)}")
            logger.info(f"  Regular CSV files (*.csv -> text/csv): {len(regular_csv_files)}")

            if dry_run:
                logger.info("\n=== DRY RUN MODE - No changes will be made ===")

                if gzip_csv_files:
                    logger.info("\nSample gzipped CSV files (first 5):")
                    for run_id, pdf_path, current_mime in gzip_csv_files[:5]:
                        logger.info(f"  {run_id}: {current_mime} -> application/gzip")
                        logger.info(f"    Path: {pdf_path}")

                if regular_csv_files:
                    logger.info("\nSample regular CSV files (first 5):")
                    for run_id, pdf_path, current_mime in regular_csv_files[:5]:
                        logger.info(f"  {run_id}: {current_mime} -> text/csv")
                        logger.info(f"    Path: {pdf_path}")

                trans.rollback()
                return

            # Update gzipped CSV files
            if gzip_csv_files:
                logger.info(f"\nUpdating {len(gzip_csv_files)} gzipped CSV files...")
                for run_id, pdf_path, _ in gzip_csv_files:
                    update_query = text("""
                        UPDATE metadata
                        SET mime = 'application/gzip'
                        WHERE run_id = :run_id
                    """)
                    conn.execute(update_query, {'run_id': run_id})
                logger.info(f"✓ Updated {len(gzip_csv_files)} gzipped CSV files to application/gzip")

            # Update regular CSV files
            if regular_csv_files:
                logger.info(f"\nUpdating {len(regular_csv_files)} regular CSV files...")
                for run_id, pdf_path, _ in regular_csv_files:
                    update_query = text("""
                        UPDATE metadata
                        SET mime = 'text/csv'
                        WHERE run_id = :run_id
                    """)
                    conn.execute(update_query, {'run_id': run_id})
                logger.info(f"✓ Updated {len(regular_csv_files)} regular CSV files to text/csv")

            # Commit transaction
            trans.commit()
            logger.info("\n=== Update completed successfully ===")

            # Show final statistics
            query = text("""
                SELECT
                    mime,
                    COUNT(*) as count,
                    COUNT(CASE WHEN pdf_path LIKE '%.csv.gz' THEN 1 END) as gz_files,
                    COUNT(CASE WHEN pdf_path LIKE '%.csv' AND pdf_path NOT LIKE '%.csv.gz' THEN 1 END) as csv_files
                FROM metadata
                WHERE mime IN ('text/csv', 'application/gzip')
                GROUP BY mime
            """)

            result = conn.execute(query)
            rows = result.fetchall()

            logger.info("\nFinal MIME type distribution:")
            logger.info("=" * 70)
            logger.info(f"{'MIME Type':<30} {'Total':<10} {'*.csv.gz':<10} {'*.csv':<10}")
            logger.info("-" * 70)
            for row in rows:
                logger.info(f"{row[0]:<30} {row[1]:<10} {row[2]:<10} {row[3]:<10}")

        except Exception as e:
            trans.rollback()
            logger.error(f"Error updating MIME types: {e}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Update CSV MIME types in metadata table')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')

    args = parser.parse_args()

    update_csv_mime_types(dry_run=args.dry_run)
