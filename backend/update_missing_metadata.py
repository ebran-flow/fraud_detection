#!/usr/bin/env python3
"""
Update missing rm_name and submitted_date in metadata table
Uses mapper.csv as the source of truth
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

def check_missing_fields():
    """Check how many records have missing fields"""
    print("\n" + "=" * 60)
    print("Checking missing fields in metadata")
    print("=" * 60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN rm_name IS NULL THEN 1 ELSE 0 END) as missing_rm_name,
                SUM(CASE WHEN submitted_date IS NULL THEN 1 ELSE 0 END) as missing_submitted_date,
                SUM(CASE WHEN rm_name IS NULL OR submitted_date IS NULL THEN 1 ELSE 0 END) as missing_either
            FROM metadata
        """))
        row = result.fetchone()

        print(f"\nCurrent state:")
        print(f"  Total records: {row[0]}")
        print(f"  Missing rm_name: {row[1]}")
        print(f"  Missing submitted_date: {row[2]}")
        print(f"  Missing either field: {row[3]}")

        return row[1], row[2], row[3]

def update_missing_rm_name():
    """Update missing rm_name from mapper.csv"""
    print("\n" + "=" * 60)
    print("Updating missing rm_name from mapper.csv")
    print("=" * 60)

    print("  Loading mapper.csv...")
    mapper_df = load_mapper()

    if mapper_df.empty:
        print("  ⚠ Warning: mapper.csv is empty or not found")
        return 0

    # Filter to only records with rm_name
    mapper_df = mapper_df[mapper_df['rm_name'].notna()]
    print(f"  Records with rm_name in mapper: {len(mapper_df)}")

    if len(mapper_df) == 0:
        print("  No records to update")
        return 0

    updated_count = 0

    with engine.connect() as conn:
        for idx, row in mapper_df.iterrows():
            run_id = row['run_id']
            rm_name = row['rm_name']

            try:
                # Update metadata table where rm_name is NULL
                result = conn.execute(
                    text("""
                        UPDATE metadata
                        SET rm_name = :rm_name
                        WHERE run_id = :run_id
                          AND (rm_name IS NULL OR rm_name = '')
                    """),
                    {"run_id": run_id, "rm_name": rm_name}
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

def update_missing_submitted_date():
    """Update missing submitted_date from mapper.csv"""
    print("\n" + "=" * 60)
    print("Updating missing submitted_date from mapper.csv")
    print("=" * 60)

    print("  Loading mapper.csv...")
    mapper_df = load_mapper()

    if mapper_df.empty:
        print("  ⚠ Warning: mapper.csv is empty or not found")
        return 0

    # Filter to only records with created_date
    mapper_df = mapper_df[mapper_df['created_date'].notna()]
    print(f"  Records with created_date in mapper: {len(mapper_df)}")

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

                # Update metadata table where submitted_date is NULL
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
                        print(f"    Updated {updated_count} records...")
                        conn.commit()

            except Exception as e:
                print(f"    ⚠ Error updating {run_id}: {e}")

        conn.commit()

    print(f"  ✓ Updated {updated_count} records")
    return updated_count

def verify_updates():
    """Verify that updates were successful"""
    print("\n" + "=" * 60)
    print("Verification: After update")
    print("=" * 60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN rm_name IS NULL THEN 1 ELSE 0 END) as missing_rm_name,
                SUM(CASE WHEN submitted_date IS NULL THEN 1 ELSE 0 END) as missing_submitted_date,
                SUM(CASE WHEN rm_name IS NOT NULL THEN 1 ELSE 0 END) as has_rm_name,
                SUM(CASE WHEN submitted_date IS NOT NULL THEN 1 ELSE 0 END) as has_submitted_date
            FROM metadata
        """))
        row = result.fetchone()

        print(f"\nFinal state:")
        print(f"  Total records: {row[0]}")
        print(f"  Still missing rm_name: {row[1]}")
        print(f"  Still missing submitted_date: {row[2]}")
        print(f"  Records with rm_name: {row[3]} ({row[3]*100//row[0] if row[0] > 0 else 0}%)")
        print(f"  Records with submitted_date: {row[4]} ({row[4]*100//row[0] if row[0] > 0 else 0}%)")

        # Show sample data
        print("\nSample updated records:")
        result = conn.execute(text("""
            SELECT run_id, acc_number, rm_name, submitted_date
            FROM metadata
            WHERE rm_name IS NOT NULL OR submitted_date IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 5
        """))
        for row in result:
            print(f"  {row[0]}: acc={row[1]}, rm={row[2]}, submitted={row[3]}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Update missing rm_name and submitted_date in metadata')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--rm-name-only', action='store_true', help='Only update rm_name')
    parser.add_argument('--submitted-date-only', action='store_true', help='Only update submitted_date')
    args = parser.parse_args()

    print("=" * 60)
    print("Update Missing Metadata Fields")
    print("=" * 60)
    print("\nThis script will update missing rm_name and submitted_date")
    print("in the metadata table using data from mapper.csv.")
    print("=" * 60)

    missing_rm, missing_submitted, missing_either = check_missing_fields()

    if missing_either == 0:
        print("\n✓ No missing fields found. Nothing to update.")
        sys.exit(0)

    if not args.yes:
        input("\nPress Enter to continue or Ctrl+C to cancel...")

    # Update fields based on flags
    if args.rm_name_only:
        update_missing_rm_name()
    elif args.submitted_date_only:
        update_missing_submitted_date()
    else:
        # Update both by default
        update_missing_rm_name()
        update_missing_submitted_date()

    verify_updates()

    print("\n" + "=" * 60)
    print("✅ UPDATE COMPLETED!")
    print("=" * 60)
    print("\nThe metadata table has been updated with missing fields.")
    print("You may need to restart your FastAPI server.")
    print("=" * 60)
