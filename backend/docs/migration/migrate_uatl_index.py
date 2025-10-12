#!/usr/bin/env python3
"""
Migration Script: Remove unique constraint on (run_id, txn_id) and add index on txn_id

This allows duplicate transactions with the same txn_id within a run_id,
which is necessary for legitimate duplicate transactions in statements.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.db import SessionLocal
from sqlalchemy import text

def run_migration():
    """Run the migration"""
    db = SessionLocal()

    try:
        print("\n" + "="*70)
        print("UATL Raw Statements Index Migration")
        print("="*70 + "\n")

        # Check if unique constraint exists
        print("Checking current indexes...")
        result = db.execute(text("""
            SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'uatl_raw_statements'
            AND INDEX_NAME IN ('uq_uatl_run_txn', 'idx_uatl_txn_id')
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """))

        indexes = result.fetchall()

        has_unique_constraint = False
        has_txn_id_index = False

        for row in indexes:
            print(f"  - {row[0]}: unique={row[1]==0}, column={row[2]}")
            if row[0] == 'uq_uatl_run_txn':
                has_unique_constraint = True
            if row[0] == 'idx_uatl_txn_id':
                has_txn_id_index = True

        print()

        # Step 1: Drop unique constraint if it exists
        if has_unique_constraint:
            print("Dropping unique constraint 'uq_uatl_run_txn'...")
            db.execute(text("ALTER TABLE uatl_raw_statements DROP INDEX uq_uatl_run_txn"))
            print("  ✅ Unique constraint removed\n")
        else:
            print("  ⏭️  Unique constraint 'uq_uatl_run_txn' does not exist\n")

        # Step 2: Create index on txn_id if it doesn't exist
        if not has_txn_id_index:
            print("Creating index 'idx_uatl_txn_id' on txn_id...")
            db.execute(text("CREATE INDEX idx_uatl_txn_id ON uatl_raw_statements(txn_id)"))
            print("  ✅ Index created\n")
        else:
            print("  ⏭️  Index 'idx_uatl_txn_id' already exists\n")

        # Commit changes
        db.commit()

        # Verify
        print("Verifying changes...")
        result = db.execute(text("""
            SELECT INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'uatl_raw_statements'
            GROUP BY INDEX_NAME, NON_UNIQUE
            ORDER BY INDEX_NAME
        """))

        print("\nCurrent indexes on uatl_raw_statements:")
        for row in result.fetchall():
            unique_str = "UNIQUE" if row[1] == 0 else "INDEX"
            print(f"  - {row[0]} ({unique_str}): {row[2]}")

        print("\n" + "="*70)
        print("✅ Migration completed successfully!")
        print("="*70 + "\n")

        return 0

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}\n")
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    exit(run_migration())
