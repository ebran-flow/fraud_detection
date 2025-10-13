#!/usr/bin/env python3
"""
Metadata Repair Script
Ensures all metadata fields are properly populated
Fills missing values from mapper.csv and raw_statements tables
Reads credentials from .env file
"""
import pandas as pd
import logging
from sqlalchemy import create_engine, text
from pathlib import Path
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    print("Error: .env file not found")
    sys.exit(1)

load_dotenv(env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_metadata.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database configuration (read from .env with defaults)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3307'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Mapper CSV path
MAPPER_CSV = Path(__file__).parent / "docs" / "data" / "statements" / "mapper.csv"


def load_mapper():
    """Load mapper.csv"""
    try:
        if not MAPPER_CSV.exists():
            logger.warning(f"Mapper CSV not found: {MAPPER_CSV}")
            return pd.DataFrame()

        df = pd.read_csv(MAPPER_CSV)
        logger.info(f"Loaded {len(df)} records from mapper.csv")
        return df
    except Exception as e:
        logger.error(f"Error loading mapper CSV: {e}")
        return pd.DataFrame()


def get_incomplete_metadata(engine):
    """Get metadata records with missing fields"""
    query = """
    SELECT
        id,
        run_id,
        acc_prvdr_code,
        acc_number,
        rm_name,
        num_rows,
        first_balance,
        last_balance,
        start_date,
        end_date,
        submitted_date
    FROM metadata
    WHERE
        rm_name IS NULL
        OR num_rows IS NULL
        OR first_balance IS NULL
        OR last_balance IS NULL
        OR start_date IS NULL
        OR end_date IS NULL
        OR submitted_date IS NULL
    ORDER BY created_at DESC
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()

    df = pd.DataFrame(rows, columns=columns)
    logger.info(f"Found {len(df)} metadata records with missing fields")
    return df


def get_data_from_raw_statements(engine, run_id, provider):
    """Get data from raw_statements table"""
    table = 'uatl_raw_statements' if provider == 'UATL' else 'umtn_raw_statements'

    query = f"""
    SELECT
        COUNT(*) as num_rows,
        MIN(DATE(txn_date)) as start_date,
        MAX(DATE(txn_date)) as end_date,
        (SELECT balance FROM {table} WHERE run_id = :run_id ORDER BY txn_date ASC LIMIT 1) as first_balance,
        (SELECT balance FROM {table} WHERE run_id = :run_id ORDER BY txn_date DESC LIMIT 1) as last_balance
    FROM {table}
    WHERE run_id = :run_id
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {"run_id": run_id})
            row = result.fetchone()

            if row and row[0] > 0:  # num_rows > 0
                return {
                    'num_rows': row[0],
                    'start_date': row[1],
                    'end_date': row[2],
                    'first_balance': float(row[3]) if row[3] is not None else None,
                    'last_balance': float(row[4]) if row[4] is not None else None,
                }
    except Exception as e:
        logger.error(f"Error getting data from {table} for run_id {run_id}: {e}")

    return {}


def get_data_from_mapper(mapper_df, run_id):
    """Get data from mapper CSV"""
    if mapper_df.empty:
        return {}

    match = mapper_df[mapper_df['run_id'] == run_id]
    if match.empty:
        return {}

    row = match.iloc[0]

    data = {}

    # Get rm_name
    if 'rm_name' in row and pd.notna(row['rm_name']):
        data['rm_name'] = str(row['rm_name'])

    # Get submitted_date from created_date
    if 'created_date' in row and pd.notna(row['created_date']):
        try:
            submitted_date = datetime.strptime(str(row['created_date']), '%Y-%m-%d').date()
            data['submitted_date'] = submitted_date
        except Exception as e:
            logger.warning(f"Could not parse created_date for run_id {run_id}: {e}")

    return data


def update_metadata(engine, metadata_id, updates):
    """Update metadata record"""
    if not updates:
        return False

    # Build SET clause
    set_clauses = []
    params = {'metadata_id': metadata_id}

    for key, value in updates.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = value

    query = f"""
    UPDATE metadata
    SET {', '.join(set_clauses)}
    WHERE id = :metadata_id
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(query), params)
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating metadata {metadata_id}: {e}")
        return False


def fix_metadata_record(engine, mapper_df, record, dry_run=False):
    """Fix a single metadata record"""
    metadata_id = record['id']
    run_id = record['run_id']
    provider = record['acc_prvdr_code']

    logger.info(f"Processing {run_id} ({provider})...")

    updates = {}

    # Get data from mapper
    mapper_data = get_data_from_mapper(mapper_df, run_id)

    # Get data from raw_statements
    raw_data = get_data_from_raw_statements(engine, run_id, provider)

    # Determine what needs to be updated
    if pd.isna(record['rm_name']) and 'rm_name' in mapper_data:
        updates['rm_name'] = mapper_data['rm_name']

    if pd.isna(record['submitted_date']) and 'submitted_date' in mapper_data:
        updates['submitted_date'] = mapper_data['submitted_date']

    if pd.isna(record['num_rows']) and 'num_rows' in raw_data:
        updates['num_rows'] = raw_data['num_rows']

    if pd.isna(record['start_date']) and 'start_date' in raw_data:
        updates['start_date'] = raw_data['start_date']

    if pd.isna(record['end_date']) and 'end_date' in raw_data:
        updates['end_date'] = raw_data['end_date']

    if pd.isna(record['first_balance']) and 'first_balance' in raw_data:
        updates['first_balance'] = raw_data['first_balance']

    if pd.isna(record['last_balance']) and 'last_balance' in raw_data:
        updates['last_balance'] = raw_data['last_balance']

    # Update metadata
    if updates:
        logger.info(f"  Would update fields: {', '.join(updates.keys())}")
        if dry_run:
            logger.info(f"  [DRY-RUN] Would update {run_id}")
            # Show what would be updated
            for key, value in updates.items():
                logger.info(f"    {key}: {value}")
            return True
        else:
            success = update_metadata(engine, metadata_id, updates)
            if success:
                logger.info(f"  ✓ Updated {run_id}")
                return True
            else:
                logger.error(f"  ✗ Failed to update {run_id}")
                return False
    else:
        logger.info(f"  - No updates needed for {run_id}")
        return False


def print_summary(stats, dry_run=False):
    """Print summary of operations"""
    print("\n" + "=" * 60)
    if dry_run:
        print("METADATA REPAIR SUMMARY (DRY-RUN)")
    else:
        print("METADATA REPAIR SUMMARY")
    print("=" * 60)
    print(f"Total records processed: {stats['total']}")
    if dry_run:
        print(f"Records that would be updated: {stats['updated']}")
    else:
        print(f"Records updated: {stats['updated']}")
    print(f"Records skipped (no data): {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 60)


def main():
    """Main function"""
    # Check for dry-run mode
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    print("=" * 60)
    if dry_run:
        print("Metadata Repair Script (DRY-RUN MODE)")
    else:
        print("Metadata Repair Script")
    print("=" * 60)
    print()
    print(f"Database: {DB_NAME}")
    print(f"Host: {DB_HOST}:{DB_PORT}")
    print(f"User: {DB_USER}")
    print()

    # Create engine
    try:
        engine = create_engine(DATABASE_URL)
        logger.info(f"Connected to database: {DB_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    # Load mapper
    mapper_df = load_mapper()

    # Get incomplete metadata
    incomplete_df = get_incomplete_metadata(engine)

    if incomplete_df.empty:
        logger.info("No incomplete metadata records found!")
        print("\n✓ All metadata records are complete!")
        return

    print(f"\nFound {len(incomplete_df)} records with missing fields")
    print()

    if dry_run:
        print("DRY-RUN MODE: No changes will be made to the database")
        print()
    else:
        # Ask for confirmation
        response = input("Proceed with repair? (y/n): ").strip().lower()
        if response != 'y':
            logger.info("Operation cancelled by user")
            print("Operation cancelled.")
            return

    print()

    # Process each record
    stats = {
        'total': len(incomplete_df),
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }

    for idx, record in incomplete_df.iterrows():
        try:
            success = fix_metadata_record(engine, mapper_df, record, dry_run=dry_run)
            if success:
                stats['updated'] += 1
            else:
                stats['skipped'] += 1
        except Exception as e:
            logger.error(f"Error processing {record['run_id']}: {e}")
            stats['errors'] += 1

    # Print summary
    print_summary(stats, dry_run=dry_run)

    # Show sample of updated records
    print("\nVerifying updates...")
    verify_query = """
    SELECT
        run_id,
        acc_prvdr_code,
        rm_name,
        num_rows,
        start_date,
        end_date,
        submitted_date
    FROM metadata
    WHERE id IN :ids
    LIMIT 5
    """

    try:
        sample_ids = tuple(incomplete_df['id'].head(5).tolist())
        with engine.connect() as conn:
            result = conn.execute(text(verify_query.replace(':ids', str(sample_ids))))
            rows = result.fetchall()

            if rows:
                print("\nSample of updated records:")
                print("-" * 60)
                for row in rows:
                    print(f"Run ID: {row[0]}")
                    print(f"  Provider: {row[1]}")
                    print(f"  RM Name: {row[2] or 'NULL'}")
                    print(f"  Num Rows: {row[3] or 'NULL'}")
                    print(f"  Date Range: {row[4] or 'NULL'} to {row[5] or 'NULL'}")
                    print(f"  Submitted: {row[6] or 'NULL'}")
                    print()
    except Exception as e:
        logger.error(f"Error verifying updates: {e}")

    print("Done!")


if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Usage: python3 fix_metadata.py [OPTIONS]")
        print()
        print("Ensures all metadata fields are properly populated")
        print()
        print("Options:")
        print("  --dry-run, -n    Show what would be updated without making changes")
        print("  --help, -h       Show this help message")
        print()
        print("Examples:")
        print("  python3 fix_metadata.py              # Run normally")
        print("  python3 fix_metadata.py --dry-run    # Preview changes")
        print()
        sys.exit(0)

    main()
