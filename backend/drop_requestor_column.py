#!/usr/bin/env python3
"""
Drop requestor column from metadata table
(Replaced by summary_email_address)
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine

def drop_requestor_column():
    """Drop requestor column from metadata table"""
    print("=" * 60)
    print("Dropping 'requestor' Column from Metadata Table")
    print("=" * 60)
    print("\nThis column has been replaced by 'summary_email_address'")
    print("=" * 60)

    with engine.connect() as conn:
        # Check if column exists
        print("\nChecking if 'requestor' column exists...")
        result = conn.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'fraud_detection'
              AND TABLE_NAME = 'metadata'
              AND COLUMN_NAME = 'requestor'
        """))

        exists = result.fetchone()

        if not exists:
            print("  ⚠ Column 'requestor' does not exist. Nothing to drop.")
        else:
            print("  ✓ Column 'requestor' found")

            # Drop the column
            print("\nDropping column 'requestor'...")
            conn.execute(text("""
                ALTER TABLE metadata
                DROP COLUMN requestor
            """))
            conn.commit()
            print("  ✓ Column 'requestor' dropped successfully")

        # Verify it's gone
        print("\nVerifying column was dropped...")
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'fraud_detection'
              AND TABLE_NAME = 'metadata'
              AND COLUMN_NAME = 'requestor'
        """))

        count = result.fetchone()[0]

        if count == 0:
            print("  ✓ Confirmed: 'requestor' column no longer exists")
        else:
            print("  ⚠ Warning: 'requestor' column still exists")

    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\nThe 'requestor' field is now handled by 'summary_email_address'")

if __name__ == "__main__":
    drop_requestor_column()
