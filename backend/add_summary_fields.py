#!/usr/bin/env python3
"""
Add summary fields to metadata table
Extracts: Email Address, Customer Name, Mobile Number, Statement Period, Request Date
From Airtel Format 1 PDFs
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine

def add_summary_columns():
    """Add summary fields columns to metadata table"""
    print("=" * 60)
    print("Adding Summary Fields to Metadata Table")
    print("=" * 60)
    print("\nThis will add the following columns after stmt_closing_balance:")
    print("  - summary_email_address (VARCHAR(255))")
    print("  - summary_customer_name (VARCHAR(255))")
    print("  - summary_mobile_number (VARCHAR(50))")
    print("  - summary_statement_period (VARCHAR(100))")
    print("  - summary_request_date (DATE)")
    print("=" * 60)

    with engine.connect() as conn:
        # Check if columns already exist
        print("\nChecking existing columns...")
        result = conn.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'fraud_detection'
              AND TABLE_NAME = 'metadata'
              AND COLUMN_NAME IN (
                  'summary_email_address',
                  'summary_customer_name',
                  'summary_mobile_number',
                  'summary_statement_period',
                  'summary_request_date'
              )
        """))
        existing_columns = [row[0] for row in result]

        columns_to_add = [
            ('summary_email_address', 'VARCHAR(255)', 'Email Address from Airtel Format 1'),
            ('summary_customer_name', 'VARCHAR(255)', 'Customer Name from Airtel Format 1'),
            ('summary_mobile_number', 'VARCHAR(50)', 'Mobile Number from Airtel Format 1'),
            ('summary_statement_period', 'VARCHAR(100)', 'Statement Period from Airtel Format 1'),
            ('summary_request_date', 'DATE', 'Request Date from Airtel Format 1'),
        ]

        # Add each column if it doesn't exist
        for col_name, col_type, description in columns_to_add:
            if col_name in existing_columns:
                print(f"  ⚠ Column '{col_name}' already exists, skipping...")
            else:
                print(f"\nAdding column: {col_name}")
                conn.execute(text(f"""
                    ALTER TABLE metadata
                    ADD COLUMN {col_name} {col_type} COMMENT '{description}'
                    AFTER stmt_closing_balance
                """))
                conn.commit()
                print(f"  ✓ Added {col_name}")

        # Verify columns were added
        print("\nVerifying columns...")
        result = conn.execute(text("""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'fraud_detection'
              AND TABLE_NAME = 'metadata'
              AND COLUMN_NAME IN (
                  'summary_email_address',
                  'summary_customer_name',
                  'summary_mobile_number',
                  'summary_statement_period',
                  'summary_request_date'
              )
            ORDER BY ORDINAL_POSITION
        """))

        print("\nSummary fields in metadata table:")
        for row in result:
            print(f"  {row[0]:30s} {row[1]:20s} - {row[2]}")

    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\nThese fields will be automatically populated for new Airtel Format 1 uploads.")
    print("To populate existing records, you would need to re-parse the original PDFs.")

if __name__ == "__main__":
    add_summary_columns()
