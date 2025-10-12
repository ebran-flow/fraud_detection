#!/usr/bin/env python3
"""
Reimport statements from a summary CSV file (without deleting first)
"""
import os
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal
from app.services.parsers import get_parser
from app.services.mapper import enrich_metadata_with_mapper
from app.services import crud_v2 as crud
from app.models.metadata import Metadata

def main():
    csv_path = "/home/ebran/Downloads/summary_selected_90_statements.csv"
    extracted_dir = "/home/ebran/Developer/projects/airtel_fraud_detection/docs/data/UATL/extracted"

    # Read run_ids from CSV
    run_ids = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_ids.append(row['run_id'])

    print(f"\n{'='*80}")
    print(f"Reimporting {len(run_ids)} statements")
    print(f"{'='*80}\n")

    success = 0
    failed = 0
    skipped = 0

    for i, run_id in enumerate(run_ids, 1):
        # Find file
        file_path = None
        for ext in ['.pdf', '.csv', '.csv.gz']:
            path = os.path.join(extracted_dir, f"{run_id}{ext}")
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            print(f"[{i}/{len(run_ids)}] ✗ File not found for {run_id}")
            failed += 1
            continue

        print(f"[{i}/{len(run_ids)}] Importing {os.path.basename(file_path)}...")

        db = SessionLocal()
        try:
            # Check if already exists
            if crud.check_run_id_exists(db, run_id, 'UATL'):
                print(f"  ⊘ Already exists, skipping")
                skipped += 1
                db.close()
                continue

            # Parse file
            parser = get_parser('UATL', file_path)
            raw_statements, metadata = parser(file_path, run_id)

            # Enrich metadata
            metadata = enrich_metadata_with_mapper(metadata, run_id)

            # Add MIME type
            file_ext = os.path.splitext(file_path)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.csv': 'text/csv',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            metadata['mime'] = mime_types.get(file_ext, 'application/octet-stream')

            # Insert into database
            metadata_obj = crud.create(db, Metadata, metadata)
            crud.bulk_create_raw(db, 'UATL', raw_statements)

            db.commit()
            print(f"  ✓ Success ({len(raw_statements)} transactions)")
            success += 1

        except Exception as e:
            db.rollback()
            print(f"  ✗ Failed: {e}")
            failed += 1
        finally:
            db.close()

    print(f"\n{'='*80}")
    print(f"Import Complete:")
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
