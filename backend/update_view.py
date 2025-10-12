#!/usr/bin/env python3
"""
Update unified_statements view to include new metadata columns
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine

def update_view():
    """Recreate unified_statements view with new columns"""
    print("=" * 60)
    print("Update unified_statements View")
    print("=" * 60)

    with engine.connect() as conn:
        print("\nDropping existing view...")
        conn.execute(text("DROP VIEW IF EXISTS unified_statements"))
        conn.commit()
        print("  ✓ Dropped")

        print("\nCreating new view with updated columns...")
        conn.execute(text("""
            CREATE VIEW unified_statements AS
            SELECT
                m.id as metadata_id,
                m.run_id,
                m.acc_number,
                m.acc_prvdr_code,
                m.format,
                m.mime,
                m.submitted_date,
                m.start_date,
                m.end_date,
                m.rm_name,
                m.num_rows,
                m.parsing_status,
                m.parsing_error,
                m.created_at as imported_at,
                -- Consolidated status field
                CASE
                    -- Import failed (parsing error)
                    WHEN m.parsing_status = 'FAILED' THEN 'IMPORT_FAILED'
                    -- Not yet processed
                    WHEN s.id IS NULL THEN 'IMPORTED'
                    -- Processed with verification FAIL
                    WHEN s.verification_status = 'FAIL' AND s.balance_match = 'Failed' THEN 'FLAGGED'
                    WHEN s.verification_status = 'FAIL' THEN 'VERIFICATION_FAILED'
                    -- Processed with verification PASS but balance issues
                    WHEN s.verification_status = 'PASS' AND s.balance_match = 'Failed' THEN 'VERIFIED_WITH_WARNINGS'
                    -- Processed successfully
                    WHEN s.verification_status = 'PASS' THEN 'VERIFIED'
                    -- Fallback
                    ELSE 'IMPORTED'
                END as status,
                -- Keep old fields for compatibility
                CASE
                    WHEN s.id IS NOT NULL THEN 'PROCESSED'
                    ELSE 'IMPORTED'
                END as processing_status,
                s.verification_status,
                s.verification_reason,
                s.balance_match,
                s.duplicate_count,
                s.created_at as processed_at,
                s.balance_diff_changes,
                s.balance_diff_change_ratio,
                s.calculated_closing_balance,
                m.stmt_closing_balance,
                m.meta_title,
                m.meta_author,
                m.meta_producer,
                m.meta_created_at,
                m.meta_modified_at
            FROM metadata m
            LEFT JOIN summary s ON m.run_id = s.run_id
            ORDER BY m.created_at DESC
        """))
        conn.commit()
        print("  ✓ Created")

        # Verify the view
        print("\nVerifying view...")
        result = conn.execute(text("SELECT COUNT(*) FROM unified_statements"))
        count = result.fetchone()[0]
        print(f"  ✓ View created successfully with {count} records")

        # Show sample
        print("\nSample records:")
        result = conn.execute(text("""
            SELECT metadata_id, run_id, format, mime, submitted_date, start_date, end_date, rm_name
            FROM unified_statements
            LIMIT 3
        """))
        for row in result:
            print(f"  {row[1]}: format={row[2]}, mime={row[3]}, submitted={row[4]}, start={row[5]}, end={row[6]}, rm_name={row[7]}")

    print("\n" + "=" * 60)
    print("✅ View updated successfully!")
    print("=" * 60)
    print("\nYou can now restart your FastAPI server and the UI should work.")

if __name__ == "__main__":
    update_view()
