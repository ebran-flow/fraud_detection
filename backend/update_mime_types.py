#!/usr/bin/env python3
"""
Update MIME types in metadata table based on pdf_path file extensions
This will update ALL records, not just ones with NULL mime
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine

def update_mime_types():
    """Update mime column from pdf_path for ALL records"""
    print("\n" + "=" * 60)
    print("Update MIME types from pdf_path")
    print("=" * 60)

    with engine.connect() as conn:
        # First, show current state
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN mime IS NULL THEN 1 ELSE 0 END) as null_mime,
                SUM(CASE WHEN mime IS NOT NULL THEN 1 ELSE 0 END) as has_mime
            FROM metadata
            WHERE pdf_path IS NOT NULL
        """))
        row = result.fetchone()
        print(f"\nCurrent state:")
        print(f"  Total records with pdf_path: {row[0]}")
        print(f"  Records with NULL mime: {row[1]}")
        print(f"  Records with mime value: {row[2]}")

        # Update ALL records based on file extension
        print(f"\nUpdating MIME types for ALL records...")
        result = conn.execute(text("""
            UPDATE metadata
            SET mime = CASE
                WHEN pdf_path LIKE '%.pdf' THEN 'application/pdf'
                WHEN pdf_path LIKE '%.csv' THEN 'text/csv'
                WHEN pdf_path LIKE '%.xlsx' THEN 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                WHEN pdf_path LIKE '%.xls' THEN 'application/vnd.ms-excel'
                ELSE 'application/octet-stream'
            END
            WHERE pdf_path IS NOT NULL
        """))
        conn.commit()
        print(f"  ✓ Updated {result.rowcount} records")

        # Show breakdown by MIME type
        print(f"\nMIME type distribution:")
        result = conn.execute(text("""
            SELECT mime, COUNT(*) as count
            FROM metadata
            WHERE mime IS NOT NULL
            GROUP BY mime
            ORDER BY count DESC
        """))
        for row in result:
            print(f"  - {row[0]}: {row[1]} records")

def verify_update():
    """Verify that MIME types were updated"""
    print("\n" + "=" * 60)
    print("Verification: Sample records")
    print("=" * 60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT run_id, acc_prvdr_code, pdf_path, mime
            FROM metadata
            WHERE pdf_path IS NOT NULL
            LIMIT 10
        """))
        for row in result:
            print(f"\n  Run ID: {row[0]}")
            print(f"    Provider: {row[1]}")
            print(f"    Path: {row[2]}")
            print(f"    MIME: {row[3]}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Update MIME types in metadata')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print("=" * 60)
    print("Update MIME Types in Metadata")
    print("=" * 60)
    print("\nThis script will update MIME types for ALL records")
    print("based on the file extension in pdf_path.")
    print("=" * 60)

    if not args.yes:
        input("\nPress Enter to continue or Ctrl+C to cancel...")

    update_mime_types()
    verify_update()

    print("\n" + "=" * 60)
    print("✅ MIME TYPE UPDATE COMPLETED!")
    print("=" * 60)
    print("\nThe unified_statements view should now show MIME types.")
    print("You may need to restart your FastAPI server.")
    print("=" * 60)
