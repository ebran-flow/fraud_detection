#!/usr/bin/env python3
"""
Populate customer_details table from existing customer_details_full.csv

This script:
1. Reads the customer_details_full.csv export
2. Inserts records into the customer_details table
3. Handles duplicates with REPLACE INTO strategy

Usage:
    python scripts/migration/populate_customer_details.py
    python scripts/migration/populate_customer_details.py --csv-file custom_export.csv
    python scripts/migration/populate_customer_details.py --batch-size 500
"""

import sys
import os
import argparse
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from tqdm import tqdm

# Setup paths
load_dotenv(Path(__file__).parent.parent.parent / '.env')
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_engine():
    """Create database engine for fraud_detection database."""
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME')

    return create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
        pool_pre_ping=True,
        pool_recycle=3600
    )


def convert_to_db_value(value):
    """Convert pandas/numpy values to database-compatible values."""
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value
    if isinstance(value, (int, float)):
        # Check if it's NaN
        if pd.isna(value):
            return None
        return value
    if isinstance(value, str):
        return value if value.strip() != '' else None
    return value


def prepare_record(row):
    """Prepare a single record for database insertion."""
    record = {}

    # Map CSV columns to database columns
    column_mapping = {
        'stmt_request_id': 'stmt_request_id',
        'run_id': 'run_id',
        'acc_number': 'acc_number',
        'alt_acc_num': 'alt_acc_num',
        'acc_prvdr_code': 'acc_prvdr_code',
        'stmt_status': 'stmt_status',
        'object_key': 'object_key',
        'lambda_status': 'lambda_status',
        'created_date': 'created_date',
        'created_at': 'created_at',
        'rm_id': 'rm_id',
        'rm_name': 'rm_name',
        'direct_entity': 'direct_entity',
        'direct_entity_id': 'direct_entity_id',
        'customer_statement_id': 'customer_statement_id',
        'cs_entity': 'cs_entity',
        'cs_entity_id': 'cs_entity_id',
        'holder_name': 'holder_name',
        'distributor_code': 'distributor_code',
        'acc_ownership': 'acc_ownership',
        'cs_status': 'cs_status',
        'cs_result': 'cs_result',
        'cs_score': 'cs_score',
        'cs_limit': 'cs_limit',
        'cs_prev_limit': 'cs_prev_limit',
        'cs_assessment_date': 'cs_assessment_date',
        'final_entity_type': 'final_entity_type',
        'final_entity_id': 'final_entity_id',
        'cust_id': 'cust_id',
        'lead_id': 'lead_id',
        'lead_mobile': 'lead_mobile',
        'lead_biz_name': 'lead_biz_name',
        'lead_first_name': 'lead_first_name',
        'lead_last_name': 'lead_last_name',
        'lead_id_proof': 'lead_id_proof',
        'lead_national_id': 'lead_national_id',
        'lead_location': 'lead_location',
        'lead_territory': 'lead_territory',
        'lead_status': 'lead_status',
        'lead_profile_status': 'lead_profile_status',
        'lead_score_status': 'lead_score_status',
        'lead_type': 'lead_type',
        'lead_date': 'lead_date',
        'lead_assessment_date': 'lead_assessment_date',
        'lead_onboarded_date': 'lead_onboarded_date',
        'reassessment_id': 'reassessment_id',
        'rr_prev_limit': 'rr_prev_limit',
        'rr_status': 'rr_status',
        'rr_type': 'rr_type',
        'rr_created_at': 'rr_created_at',
        'borrower_id': 'borrower_id',
        'borrower_cust_id': 'borrower_cust_id',
        'borrower_biz_name': 'borrower_biz_name',
        'borrower_reg_date': 'borrower_reg_date',
        'tot_loans': 'tot_loans',
        'tot_default_loans': 'tot_default_loans',
        'crnt_fa_limit': 'crnt_fa_limit',
        'prev_fa_limit': 'prev_fa_limit',
        'borrower_last_assessment_date': 'borrower_last_assessment_date',
        'borrower_kyc_status': 'borrower_kyc_status',
        'borrower_activity_status': 'borrower_activity_status',
        'borrower_profile_status': 'borrower_profile_status',
        'borrower_fa_status': 'borrower_fa_status',
        'borrower_status': 'borrower_status',
        'risk_category': 'risk_category',
        'reg_rm_id': 'reg_rm_id',
        'reg_rm_name': 'reg_rm_name',
        'current_rm_id': 'current_rm_id',
        'current_rm_name': 'current_rm_name',
    }

    for csv_col, db_col in column_mapping.items():
        if csv_col in row.index:
            record[db_col] = convert_to_db_value(row[csv_col])

    # Add sync timestamp
    record['synced_at'] = datetime.now()

    return record


def insert_batch(engine, records, batch_size=100):
    """Insert records in batches using REPLACE INTO."""
    total_inserted = 0

    with engine.connect() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            if not batch:
                continue

            # Build REPLACE INTO statement
            columns = list(batch[0].keys())
            placeholders = ', '.join([f':{col}' for col in columns])
            column_names = ', '.join([f'`{col}`' for col in columns])

            query = text(f"""
                REPLACE INTO customer_details ({column_names})
                VALUES ({placeholders})
            """)

            try:
                # Execute batch
                for record in batch:
                    conn.execute(query, record)
                conn.commit()
                total_inserted += len(batch)

            except Exception as e:
                logger.error(f"Error inserting batch starting at index {i}: {e}")
                conn.rollback()
                raise

    return total_inserted


def populate_from_csv(csv_path, engine, batch_size=100):
    """
    Populate customer_details table from CSV file.

    Args:
        csv_path: Path to CSV file
        engine: SQLAlchemy engine
        batch_size: Number of records to insert per batch

    Returns:
        Number of records inserted
    """
    logger.info(f"Reading CSV file: {csv_path}")

    # Read CSV with proper data types
    df = pd.read_csv(
        csv_path,
        parse_dates=['created_date', 'created_at', 'cs_assessment_date',
                     'lead_date', 'lead_assessment_date', 'lead_onboarded_date',
                     'rr_created_at', 'borrower_reg_date', 'borrower_last_assessment_date']
    )

    logger.info(f"Loaded {len(df):,} records from CSV")

    # Prepare records
    logger.info("Preparing records for database insertion...")
    records = []
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Preparing records"):
        record = prepare_record(row)
        records.append(record)

    logger.info(f"Prepared {len(records):,} records")

    # Insert records
    logger.info(f"Inserting records in batches of {batch_size}...")
    total_inserted = insert_batch(engine, records, batch_size)

    logger.info(f"✓ Successfully inserted {total_inserted:,} records")

    return total_inserted


def verify_insertion(engine):
    """Verify records were inserted correctly."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as count FROM customer_details"))
        count = result.scalar()
        logger.info(f"Total records in customer_details table: {count:,}")

        # Check for records with cust_id
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN cust_id IS NOT NULL THEN 1 ELSE 0 END) as with_cust_id,
                SUM(CASE WHEN borrower_id IS NOT NULL THEN 1 ELSE 0 END) as with_borrower
            FROM customer_details
        """))
        row = result.fetchone()
        logger.info(f"  With cust_id: {row.with_cust_id:,} ({row.with_cust_id/row.total*100:.1f}%)")
        logger.info(f"  With borrower_id: {row.with_borrower:,} ({row.with_borrower/row.total*100:.1f}%)")

        # Provider distribution
        result = conn.execute(text("""
            SELECT acc_prvdr_code, COUNT(*) as count
            FROM customer_details
            GROUP BY acc_prvdr_code
        """))
        logger.info("Provider distribution:")
        for row in result:
            logger.info(f"  {row.acc_prvdr_code}: {row.count:,}")


def main():
    parser = argparse.ArgumentParser(
        description='Populate customer_details table from CSV export',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--csv-file', type=str,
                       default='docs/data/customer_details_full.csv',
                       help='Path to CSV file (default: docs/data/customer_details_full.csv)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of records per batch (default: 100)')
    parser.add_argument('--verify-only', action='store_true',
                       help='Only verify existing records without inserting')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("POPULATE CUSTOMER_DETAILS TABLE")
    logger.info("=" * 80)

    # Get database engine
    engine = get_database_engine()

    if args.verify_only:
        logger.info("Verification mode - checking existing records")
        verify_insertion(engine)
    else:
        # Check if file exists
        csv_path = Path(args.csv_file)
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return 1

        # Populate from CSV
        total_inserted = populate_from_csv(csv_path, engine, args.batch_size)

        # Verify
        logger.info("\nVerifying insertion...")
        verify_insertion(engine)

    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE")
    logger.info("=" * 80)

    return 0


if __name__ == '__main__':
    exit(main())
