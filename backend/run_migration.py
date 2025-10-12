#!/usr/bin/env python3
"""
Run database migration to add new metadata columns and populate existing data
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine
from app.services.mapper import load_mapper

def add_columns():
    """Add new columns to metadata table after pdf_format"""
    print("\n" + "=" * 60)
    print("Step 1: Adding new columns to metadata table")
    print("=" * 60)

    columns_to_add = [
        ("format", "VARCHAR(20)", "Format of the statement (e.g., format_1, format_2, excel)"),
        ("mime", "VARCHAR(50)", "MIME type (e.g., application/pdf, text/csv)"),
        ("submitted_date", "DATE", "From mapper.csv using run_id → created_date"),
        ("start_date", "DATE", "min(txn_date) from raw_statements"),
        ("end_date", "DATE", "max(txn_date) from raw_statements"),
        ("requestor", "VARCHAR(255)", "Email ID from Airtel format 1"),
    ]

    with engine.connect() as conn:
        for col_name, col_type, description in columns_to_add:
            try:
                print(f"  Adding column: {col_name} ({col_type}) AFTER pdf_format...")
                conn.execute(text(f"""
                    ALTER TABLE metadata
                    ADD COLUMN {col_name} {col_type} COMMENT '{description}' AFTER pdf_format
                """))
                conn.commit()
                print(f"    ✓ Success")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"    ℹ Column already exists, skipping")
                else:
                    print(f"    ⚠ Error: {e}")

        # Add index on submitted_date
        try:
            print(f"  Adding index on submitted_date...")
            conn.execute(text("CREATE INDEX idx_submitted_date ON metadata(submitted_date)"))
            conn.commit()
            print(f"    ✓ Success")
        except Exception as e:
            if "Duplicate key name" in str(e):
                print(f"    ℹ Index already exists, skipping")
            else:
                print(f"    ⚠ Error: {e}")

    print("✅ Column addition completed!")

def run_sql_migration():
    """Execute the migration SQL file to populate data"""
    print("\n" + "=" * 60)
    print("Step 2: Populating data from existing columns")
    print("=" * 60)

    migration_file = Path(__file__).parent / 'migrations' / 'add_metadata_columns.sql'

    if not migration_file.exists():
        print(f"Error: Migration file not found at {migration_file}")
        return False

    print(f"Reading migration from: {migration_file}")
    with open(migration_file, 'r') as f:
        sql_content = f.read()

    # Split by semicolons and execute each statement
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

    print(f"\nExecuting {len(statements)} SQL statements...")

    with engine.connect() as conn:
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
            try:
                # Truncate long statements for display
                display_stmt = statement.replace('\n', ' ')[:100]
                print(f"  [{i}/{len(statements)}] {display_stmt}...")
                result = conn.execute(text(statement))
                conn.commit()
                if result.rowcount > 0:
                    print(f"    ✓ Success ({result.rowcount} rows affected)")
                else:
                    print(f"    ✓ Success")
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"    ⚠ Warning: {error_msg}")
                # Continue with other statements even if one fails

    print("\n✅ SQL migration completed!")
    return True

def populate_submitted_dates():
    """Populate submitted_date from mapper.csv"""
    print("\n" + "=" * 60)
    print("Step 3: Populate submitted_date from mapper.csv")
    print("=" * 60)

    print("Loading mapper.csv...")
    mapper_df = load_mapper()

    if mapper_df.empty:
        print("⚠ Warning: mapper.csv is empty or not found")
        return 0

    print(f"Found {len(mapper_df)} records in mapper.csv")

    # Filter to only records with created_date
    mapper_df = mapper_df[mapper_df['created_date'].notna()]
    print(f"Records with created_date: {len(mapper_df)}")

    if len(mapper_df) == 0:
        print("No records to update")
        return 0

    updated_count = 0

    with engine.connect() as conn:
        for idx, row in mapper_df.iterrows():
            run_id = row['run_id']
            created_date = row['created_date']

            try:
                # Parse the date if it's a string
                if isinstance(created_date, str):
                    created_date = datetime.strptime(created_date, '%Y-%m-%d').date()

                # Update metadata table
                result = conn.execute(
                    text("""
                        UPDATE metadata
                        SET submitted_date = :created_date
                        WHERE run_id = :run_id
                          AND submitted_date IS NULL
                    """),
                    {"run_id": run_id, "created_date": created_date}
                )

                if result.rowcount > 0:
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"  Updated {updated_count} records...")
                        conn.commit()

            except Exception as e:
                print(f"  ⚠ Error updating {run_id}: {e}")

        conn.commit()

    print(f"✅ Updated submitted_date for {updated_count} records")
    return updated_count

def verify_migration():
    """Verify that columns were added and data was populated"""
    print("\n" + "=" * 60)
    print("Verification: Checking migration results")
    print("=" * 60)

    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN format IS NOT NULL THEN 1 ELSE 0 END) as has_format,
                SUM(CASE WHEN mime IS NOT NULL THEN 1 ELSE 0 END) as has_mime,
                SUM(CASE WHEN submitted_date IS NOT NULL THEN 1 ELSE 0 END) as has_submitted_date,
                SUM(CASE WHEN start_date IS NOT NULL THEN 1 ELSE 0 END) as has_start_date,
                SUM(CASE WHEN end_date IS NOT NULL THEN 1 ELSE 0 END) as has_end_date
            FROM metadata
        """))
        row = result.fetchone()

        if row:
            print(f"\nTotal metadata records: {row[0]}")
            print(f"  - Records with format: {row[1]} ({row[1]*100//row[0] if row[0] > 0 else 0}%)")
            print(f"  - Records with mime: {row[2]} ({row[2]*100//row[0] if row[0] > 0 else 0}%)")
            print(f"  - Records with submitted_date: {row[3]} ({row[3]*100//row[0] if row[0] > 0 else 0}%)")
            print(f"  - Records with start_date: {row[4]} ({row[4]*100//row[0] if row[0] > 0 else 0}%)")
            print(f"  - Records with end_date: {row[5]} ({row[5]*100//row[0] if row[0] > 0 else 0}%)")

        # Check unified_statements view
        result = conn.execute(text("SELECT COUNT(*) FROM unified_statements LIMIT 1"))
        print(f"\n✅ unified_statements view is working")

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Add Metadata Columns")
    print("=" * 60)
    print("\nThis migration will:")
    print("  1. Add 6 new columns to metadata table")
    print("  2. Populate format from pdf_format")
    print("  3. Populate mime from pdf_path")
    print("  4. Populate start_date/end_date from raw_statements")
    print("  5. Populate submitted_date from mapper.csv")
    print("  6. Update unified_statements view")
    print("\nNote: pdf_format column will be kept (can be dropped after confirmation)")
    print("=" * 60)

    input("\nPress Enter to continue or Ctrl+C to cancel...")

    # Run migration steps
    add_columns()              # Step 1: Add columns via Python
    run_sql_migration()        # Step 2: Populate data via SQL
    populate_submitted_dates() # Step 3: Populate submitted_date from mapper.csv
    verify_migration()         # Step 4: Verify results

    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Restart your FastAPI server")
    print("  2. Test the UI to verify all columns are populated")
    print("  3. If everything looks good, run the following to drop pdf_format:")
    print("     ALTER TABLE metadata DROP COLUMN pdf_format;")
    print("=" * 60)
