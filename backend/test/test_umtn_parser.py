#!/usr/bin/env python3
"""
Test UMTN Parser
Tests parsing and importing UMTN (MTN) statements
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.parsers.umtn_parser import parse_umtn_excel
from app.services.db import SessionLocal
from app.services import crud_v2 as crud
from app.models.metadata import Metadata
from app.services.mapper import enrich_metadata_with_mapper


def test_parse_umtn_file(file_path: str, run_id: str):
    """Test parsing a single UMTN file"""
    print(f"\n{'='*70}")
    print(f"Testing UMTN Parser")
    print(f"{'='*70}")
    print(f"File: {file_path}")
    print(f"Run ID: {run_id}")
    print(f"{'='*70}\n")

    try:
        # Parse file
        print("Parsing file...")
        raw_statements, metadata = parse_umtn_excel(file_path, run_id)

        print(f"✅ Successfully parsed file")
        print(f"   - Transactions: {len(raw_statements)}")
        print(f"   - Account Number: {metadata.get('acc_number')}")
        print(f"   - Provider: {metadata.get('acc_prvdr_code')}")
        print(f"   - Format: {metadata.get('format')}")
        print(f"   - First Balance: {metadata.get('first_balance')}")
        print(f"   - Last Balance: {metadata.get('last_balance')}")

        # Show sample transactions
        print(f"\nSample Transactions (first 3):")
        for i, stmt in enumerate(raw_statements[:3]):
            print(f"\n  Transaction {i+1}:")
            print(f"    - Date: {stmt['txn_date']}")
            print(f"    - Type: {stmt['txn_type']}")
            print(f"    - Amount: {stmt['amount']}")
            print(f"    - Fee: {stmt['fee']}")
            print(f"    - Float Balance: {stmt['float_balance']}")
            print(f"    - From: {stmt['from_acc']}")
            print(f"    - To: {stmt['to_acc']}")

        return raw_statements, metadata

    except Exception as e:
        print(f"❌ Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_import_to_db(run_id: str, raw_statements, metadata):
    """Test importing parsed data to database"""
    print(f"\n{'='*70}")
    print(f"Testing Database Import")
    print(f"{'='*70}\n")

    db = SessionLocal()
    try:
        # Check if already exists
        if crud.check_run_id_exists(db, run_id, 'UMTN'):
            print(f"⚠️  Run ID {run_id} already exists in database")
            response = input("Delete existing and re-import? (y/n): ").strip().lower()
            if response != 'y':
                print("Skipping import")
                return False

            # Delete existing
            print("Deleting existing records...")
            db.execute(text(f"DELETE FROM umtn_raw_statements WHERE run_id = :run_id"), {"run_id": run_id})
            db.execute(text(f"DELETE FROM metadata WHERE run_id = :run_id"), {"run_id": run_id})
            db.commit()

        # Enrich metadata with mapper data
        print("Enriching metadata with mapper data...")
        metadata = enrich_metadata_with_mapper(metadata, run_id)

        # Create metadata
        print("Creating metadata record...")
        metadata_obj = crud.create(db, Metadata, metadata)
        print(f"✅ Created metadata: ID={metadata_obj.id}")

        # Bulk insert raw statements
        print(f"Inserting {len(raw_statements)} transactions...")
        crud.bulk_create_raw(db, 'UMTN', raw_statements)
        print(f"✅ Inserted {len(raw_statements)} transactions")

        db.commit()
        print(f"\n✅ Successfully imported {run_id} to database")
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error importing to database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Main test function"""
    # Test files
    import os
    extracted_dir = Path(__file__).parent / "docs" / "data" / "UMTN" / "extracted"

    # Find first XLSX and CSV file
    xlsx_files = list(extracted_dir.glob("*.xlsx"))
    csv_files = list(extracted_dir.glob("*.csv"))

    if not xlsx_files and not csv_files:
        print("❌ No UMTN files found in extracted directory")
        return

    # Test XLSX file if available
    if xlsx_files:
        test_file = xlsx_files[0]
        run_id = test_file.stem

        raw_statements, metadata = test_parse_umtn_file(str(test_file), run_id)

        if raw_statements and metadata:
            # Ask to import
            response = input("\nImport to database? (y/n): ").strip().lower()
            if response == 'y':
                test_import_to_db(run_id, raw_statements, metadata)

    # Test CSV file
    if csv_files:
        print(f"\n{'='*70}")
        print("Testing CSV file...")
        print(f"{'='*70}")

        test_file = csv_files[0]
        run_id = test_file.stem + "_csv"

        raw_statements, metadata = test_parse_umtn_file(str(test_file), run_id)

        if raw_statements and metadata:
            response = input("\nImport to database? (y/n): ").strip().lower()
            if response == 'y':
                test_import_to_db(run_id, raw_statements, metadata)


if __name__ == '__main__':
    from sqlalchemy import text
    main()
