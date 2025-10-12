#!/usr/bin/env python3
"""
Reorder metadata columns to place new columns after pdf_format
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine

def reorder_columns():
    """Reorder columns to place new columns after pdf_format"""
    print("=" * 60)
    print("Reordering Metadata Columns")
    print("=" * 60)
    print("\nThis will reorder columns to appear after pdf_format:")
    print("  - format")
    print("  - mime")
    print("  - submitted_date")
    print("  - start_date")
    print("  - end_date")
    print("  - requestor")
    print("=" * 60)

    input("\nPress Enter to continue or Ctrl+C to cancel...")

    columns_to_reorder = [
        ("format", "VARCHAR(20)", "Format of the statement (e.g., format_1, format_2, excel)"),
        ("mime", "VARCHAR(50)", "MIME type (e.g., application/pdf, text/csv)"),
        ("submitted_date", "DATE", "From mapper.csv using run_id → created_date"),
        ("start_date", "DATE", "min(txn_date) from raw_statements"),
        ("end_date", "DATE", "max(txn_date) from raw_statements"),
        ("requestor", "VARCHAR(255)", "Email ID from Airtel format 1"),
    ]

    with engine.connect() as conn:
        # Track the previous column name for ordering
        after_column = "pdf_format"

        for col_name, col_type, description in columns_to_reorder:
            try:
                print(f"\nReordering column: {col_name}")

                # Step 1: Rename to temp name
                print(f"  Step 1: Renaming {col_name} to {col_name}_temp...")
                conn.execute(text(f"""
                    ALTER TABLE metadata
                    CHANGE COLUMN {col_name} {col_name}_temp {col_type} COMMENT '{description}'
                """))
                conn.commit()

                # Step 2: Add new column after the previous column (to maintain order)
                print(f"  Step 2: Adding {col_name} AFTER {after_column}...")
                conn.execute(text(f"""
                    ALTER TABLE metadata
                    ADD COLUMN {col_name} {col_type} COMMENT '{description}' AFTER {after_column}
                """))
                conn.commit()

                # Step 3: Copy data from temp to new column
                print(f"  Step 3: Copying data from {col_name}_temp to {col_name}...")
                conn.execute(text(f"""
                    UPDATE metadata
                    SET {col_name} = {col_name}_temp
                """))
                conn.commit()

                # Step 4: Drop temp column
                print(f"  Step 4: Dropping {col_name}_temp...")
                conn.execute(text(f"""
                    ALTER TABLE metadata
                    DROP COLUMN {col_name}_temp
                """))
                conn.commit()

                print(f"  ✓ Successfully reordered {col_name}")

                # Update after_column for next iteration
                after_column = col_name

            except Exception as e:
                print(f"  ⚠ Error reordering {col_name}: {e}")
                conn.rollback()

    # Verify final column order
    print("\n" + "=" * 60)
    print("Verification: Current column order")
    print("=" * 60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COLUMN_NAME, ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'fraud_detection'
              AND TABLE_NAME = 'metadata'
            ORDER BY ORDINAL_POSITION
        """))

        print("\nColumn order:")
        for row in result:
            print(f"  {row[1]:2d}. {row[0]}")

    print("\n" + "=" * 60)
    print("✅ Column reordering completed!")
    print("=" * 60)

if __name__ == "__main__":
    reorder_columns()
