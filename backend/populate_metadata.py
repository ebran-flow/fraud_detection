#!/usr/bin/env python3
"""
Populate existing metadata columns with data
Run this if columns already exist but are empty
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

def populate_format():
    """Populate format column from pdf_format"""
    print("\n" + "=" * 60)
    print("Step 1: Populate format from pdf_format")
    print("=" * 60)

    with engine.connect() as conn:
        # For UATL: format_1 or format_2
        result = conn.execute(text("""
            UPDATE metadata
            SET format = CASE
                WHEN acc_prvdr_code = 'UATL' AND pdf_format = 1 THEN 'format_1'
                WHEN acc_prvdr_code = 'UATL' AND pdf_format = 2 THEN 'format_2'
                WHEN acc_prvdr_code = 'UMTN' THEN 'excel'
                ELSE NULL
            END
            WHERE format IS NULL
        """))
        conn.commit()
        print(f"  ✓ Updated {result.rowcount} records")

def populate_mime():
    """Populate mime column from pdf_path"""
    print("\n" + "=" * 60)
    print("Step 2: Populate mime from pdf_path")
    print("=" * 60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE metadata
            SET mime = CASE
                WHEN pdf_path LIKE '%.pdf' THEN 'application/pdf'
                WHEN pdf_path LIKE '%.csv' THEN 'text/csv'
                WHEN pdf_path LIKE '%.xlsx' THEN 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                WHEN pdf_path LIKE '%.xls' THEN 'application/vnd.ms-excel'
                ELSE 'application/octet-stream'
            END
            WHERE mime IS NULL AND pdf_path IS NOT NULL
        """))
        conn.commit()
        print(f"  ✓ Updated {result.rowcount} records")

def populate_dates():
    """Populate start_date and end_date from raw_statements"""
    print("\n" + "=" * 60)
    print("Step 3: Populate start_date and end_date from raw_statements")
    print("=" * 60)

    with engine.connect() as conn:
        # For UATL
        print("  Processing UATL statements...")
        result = conn.execute(text("""
            UPDATE metadata m
            JOIN (
                SELECT
                    run_id,
                    DATE(MIN(txn_date)) as min_date,
                    DATE(MAX(txn_date)) as max_date
                FROM uatl_raw_statements
                WHERE txn_date IS NOT NULL
                GROUP BY run_id
            ) r ON m.run_id = r.run_id
            SET
                m.start_date = r.min_date,
                m.end_date = r.max_date
            WHERE m.acc_prvdr_code = 'UATL'
              AND r.min_date IS NOT NULL
        """))
        conn.commit()
        print(f"    ✓ Updated {result.rowcount} UATL records")

        # For UMTN
        print("  Processing UMTN statements...")
        result = conn.execute(text("""
            UPDATE metadata m
            JOIN (
                SELECT
                    run_id,
                    DATE(MIN(txn_date)) as min_date,
                    DATE(MAX(txn_date)) as max_date
                FROM umtn_raw_statements
                WHERE txn_date IS NOT NULL
                GROUP BY run_id
            ) r ON m.run_id = r.run_id
            SET
                m.start_date = r.min_date,
                m.end_date = r.max_date
            WHERE m.acc_prvdr_code = 'UMTN'
              AND r.min_date IS NOT NULL
        """))
        conn.commit()
        print(f"    ✓ Updated {result.rowcount} UMTN records")

def populate_submitted_date():
    """Populate submitted_date from mapper.csv"""
    print("\n" + "=" * 60)
    print("Step 4: Populate submitted_date from mapper.csv")
    print("=" * 60)

    print("  Loading mapper.csv...")
    mapper_df = load_mapper()

    if mapper_df.empty:
        print("  ⚠ Warning: mapper.csv is empty or not found")
        return 0

    print(f"  Found {len(mapper_df)} records in mapper.csv")

    # Filter to only records with created_date
    mapper_df = mapper_df[mapper_df['created_date'].notna()]
    print(f"  Records with created_date: {len(mapper_df)}")

    if len(mapper_df) == 0:
        print("  No records to update")
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
                    """),
                    {"run_id": run_id, "created_date": created_date}
                )

                if result.rowcount > 0:
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"    Updated {updated_count} records...")
                        conn.commit()

            except Exception as e:
                print(f"    ⚠ Error updating {run_id}: {e}")

        conn.commit()

    print(f"  ✓ Updated {updated_count} records")
    return updated_count

def verify_population():
    """Verify that data was populated"""
    print("\n" + "=" * 60)
    print("Verification: Checking populated data")
    print("=" * 60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN format IS NOT NULL THEN 1 ELSE 0 END) as has_format,
                SUM(CASE WHEN mime IS NOT NULL THEN 1 ELSE 0 END) as has_mime,
                SUM(CASE WHEN submitted_date IS NOT NULL THEN 1 ELSE 0 END) as has_submitted_date,
                SUM(CASE WHEN start_date IS NOT NULL THEN 1 ELSE 0 END) as has_start_date,
                SUM(CASE WHEN end_date IS NOT NULL THEN 1 ELSE 0 END) as has_end_date,
                SUM(CASE WHEN requestor IS NOT NULL THEN 1 ELSE 0 END) as has_requestor
            FROM metadata
        """))
        row = result.fetchone()

        if row:
            total = row[0]
            print(f"\nTotal metadata records: {total}")
            if total > 0:
                print(f"  - Records with format: {row[1]} ({row[1]*100//total}%)")
                print(f"  - Records with mime: {row[2]} ({row[2]*100//total}%)")
                print(f"  - Records with submitted_date: {row[3]} ({row[3]*100//total}%)")
                print(f"  - Records with start_date: {row[4]} ({row[4]*100//total}%)")
                print(f"  - Records with end_date: {row[5]} ({row[5]*100//total}%)")
                print(f"  - Records with requestor: {row[6]} ({row[6]*100//total if total > 0 else 0}%)")

        # Show sample data
        print("\nSample records:")
        result = conn.execute(text("""
            SELECT run_id, format, mime, submitted_date, start_date, end_date, requestor
            FROM metadata
            LIMIT 5
        """))
        for row in result:
            print(f"  {row[0]}: format={row[1]}, mime={row[2]}, submitted={row[3]}, start={row[4]}, end={row[5]}, requestor={row[6]}")

if __name__ == "__main__":
    print("=" * 60)
    print("Populate Metadata Columns")
    print("=" * 60)
    print("\nThis script will populate existing empty columns with data.")
    print("=" * 60)

    input("\nPress Enter to continue or Ctrl+C to cancel...")

    populate_format()
    populate_mime()
    populate_dates()
    populate_submitted_date()
    verify_population()

    print("\n" + "=" * 60)
    print("✅ POPULATION COMPLETED!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Restart your FastAPI server")
    print("  2. Check the UI to verify all data is showing")
    print("=" * 60)
