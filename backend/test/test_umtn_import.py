#!/usr/bin/env python3
"""
Test UMTN Import - Non-interactive
Parses and imports a sample UMTN file to database
"""
import sys
from pathlib import Path
from sqlalchemy import text

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.parsers.umtn_parser import parse_umtn_excel
from app.services.db import SessionLocal
from app.services import crud_v2 as crud
from app.models.metadata import Metadata
from app.services.mapper import enrich_metadata_with_mapper


def main():
    """Test parsing and importing a UMTN file"""
    # Find first XLSX file
    extracted_dir = Path(__file__).parent / "docs" / "data" / "UMTN" / "extracted"
    xlsx_files = list(extracted_dir.glob("*.xlsx"))[:1]  # Get first file only

    if not xlsx_files:
        print("❌ No XLSX files found")
        return

    test_file = xlsx_files[0]
    run_id = test_file.stem

    print(f"\n{'='*70}")
    print(f"Testing UMTN Import")
    print(f"{'='*70}")
    print(f"File: {test_file.name}")
    print(f"Run ID: {run_id}")
    print(f"{'='*70}\n")

    # Parse file
    print("1. Parsing file...")
    try:
        raw_statements, metadata = parse_umtn_excel(str(test_file), run_id)
        print(f"   ✅ Parsed {len(raw_statements)} transactions")
        print(f"   - Account: {metadata['acc_number']}")
        print(f"   - Provider: {metadata['acc_prvdr_code']}")
        print(f"   - Balance range: {metadata['first_balance']} to {metadata['last_balance']}")
    except Exception as e:
        print(f"   ❌ Parse error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Import to database
    print(f"\n2. Importing to database...")
    db = SessionLocal()
    try:
        # Check if exists
        if crud.check_run_id_exists(db, run_id, 'UMTN'):
            print(f"   ⚠️  Run ID already exists, deleting...")
            db.execute(text("DELETE FROM umtn_raw_statements WHERE run_id = :run_id"), {"run_id": run_id})
            db.execute(text("DELETE FROM metadata WHERE run_id = :run_id AND acc_prvdr_code = 'UMTN'"), {"run_id": run_id})
            db.commit()

        # Enrich metadata
        metadata = enrich_metadata_with_mapper(metadata, run_id)

        # Create metadata
        print(f"   - Creating metadata...")
        metadata_obj = crud.create(db, Metadata, metadata)

        # Bulk insert raw statements
        print(f"   - Inserting {len(raw_statements)} transactions...")
        crud.bulk_create_raw(db, 'UMTN', raw_statements)

        db.commit()
        print(f"   ✅ Successfully imported to database")

        # Verify import
        print(f"\n3. Verifying import...")
        result = db.execute(text("SELECT COUNT(*) FROM umtn_raw_statements WHERE run_id = :run_id"), {"run_id": run_id})
        count = result.scalar()
        print(f"   - Records in umtn_raw_statements: {count}")

        result = db.execute(text("SELECT COUNT(*) FROM metadata WHERE run_id = :run_id AND acc_prvdr_code = 'UMTN'"), {"run_id": run_id})
        meta_count = result.scalar()
        print(f"   - Records in metadata: {meta_count}")

        if count == len(raw_statements) and meta_count == 1:
            print(f"\n✅ Import verification successful!")
        else:
            print(f"\n⚠️  Import verification mismatch")

    except Exception as e:
        db.rollback()
        print(f"   ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print(f"\n{'='*70}")
    print("Test complete")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
