#!/usr/bin/env python3
"""
Delete and reimport statements from a summary CSV file
Deletes: raw_uatl_statements, metadata, processed_uatl_statements, summary
Then reimports the original files
"""
import os
import sys
import csv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine, SessionLocal
from app.services.parsers import get_parser
from app.services.mapper import enrich_metadata_with_mapper
from app.services import crud_v2 as crud
from app.models.metadata import Metadata

def get_run_ids_from_csv(csv_path: str) -> list:
    """Extract run_ids from summary CSV file"""
    run_ids = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_ids.append(row['run_id'])
    return run_ids

def get_file_paths_for_run_ids(run_ids: list) -> dict:
    """Get original file paths for run_ids - look in extracted folder"""
    file_paths = {}
    extracted_dir = "/home/ebran/Developer/projects/airtel_fraud_detection/docs/data/UATL/extracted"

    for run_id in run_ids:
        # Look for files with this run_id in the extracted folder
        possible_extensions = ['.pdf', '.csv', '.csv.gz']
        for ext in possible_extensions:
            file_path = os.path.join(extracted_dir, f"{run_id}{ext}")
            if os.path.exists(file_path):
                file_paths[run_id] = {
                    'path': file_path,
                    'mime': 'application/pdf' if ext == '.pdf' else 'text/csv'
                }
                break

    return file_paths

def delete_data_for_run_ids(run_ids: list):
    """Delete all related data for run_ids"""
    print(f"\n{'='*80}")
    print(f"Deleting data for {len(run_ids)} run_ids")
    print(f"{'='*80}\n")

    with engine.connect() as conn:
        for i, run_id in enumerate(run_ids, 1):
            print(f"[{i}/{len(run_ids)}] Deleting data for run_id: {run_id}")

            try:
                # Delete from uatl_processed_statements
                result = conn.execute(text("""
                    DELETE FROM uatl_processed_statements WHERE run_id = :run_id
                """), {"run_id": run_id})
                print(f"  ✓ Deleted {result.rowcount} UATL processed statements")

                # Delete from uatl_raw_statements
                result = conn.execute(text("""
                    DELETE FROM uatl_raw_statements WHERE run_id = :run_id
                """), {"run_id": run_id})
                print(f"  ✓ Deleted {result.rowcount} UATL raw statements")

                # Delete from summary
                result = conn.execute(text("""
                    DELETE FROM summary WHERE run_id = :run_id
                """), {"run_id": run_id})
                print(f"  ✓ Deleted {result.rowcount} summary records")

                # Delete from metadata
                result = conn.execute(text("""
                    DELETE FROM metadata WHERE run_id = :run_id
                """), {"run_id": run_id})
                print(f"  ✓ Deleted {result.rowcount} metadata records")

                conn.commit()

            except Exception as e:
                print(f"  ✗ Error deleting {run_id}: {e}")
                conn.rollback()

def reimport_files(file_paths: dict):
    """Reimport files using their original paths"""
    print(f"\n{'='*80}")
    print(f"Reimporting {len(file_paths)} files")
    print(f"{'='*80}\n")

    success_count = 0
    failed_count = 0

    for i, (run_id, info) in enumerate(file_paths.items(), 1):
        file_path = info['path']
        mime_type = info['mime']

        print(f"[{i}/{len(file_paths)}] Reimporting: {file_path}")

        if not os.path.exists(file_path):
            print(f"  ✗ File not found: {file_path}")
            failed_count += 1
            continue

        try:
            # Determine provider from mime or path
            provider = 'UATL'  # Default for this batch

            # Get parser for this file
            parser = get_parser(provider, file_path)

            # Parse file
            db = SessionLocal()
            try:
                raw_statements, metadata = parser(file_path, run_id)

                # Enrich metadata with mapper data
                metadata = enrich_metadata_with_mapper(metadata, run_id)

                # Add MIME type
                file_ext = os.path.splitext(file_path)[1].lower()
                mime_types = {
                    '.pdf': 'application/pdf',
                    '.csv': 'text/csv',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.xls': 'application/vnd.ms-excel'
                }
                metadata['mime'] = mime_types.get(file_ext, 'application/octet-stream')

                # Ensure provider code
                provider_code = metadata.get('acc_prvdr_code', provider)

                # Insert into database
                metadata_obj = crud.create(db, Metadata, metadata)
                crud.bulk_create_raw(db, provider_code, raw_statements)

                db.commit()
                print(f"  ✓ Imported successfully: {run_id} ({len(raw_statements)} transactions)")
                success_count += 1

            except Exception as e:
                db.rollback()
                print(f"  ✗ Import failed: {e}")
                failed_count += 1
            finally:
                db.close()

        except Exception as e:
            print(f"  ✗ Error importing {file_path}: {e}")
            failed_count += 1

    print(f"\n{'='*80}")
    print(f"Import Summary:")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*80}")

def main():
    csv_path = "/home/ebran/Downloads/summary_selected_90_statements.csv"

    print(f"\n{'='*80}")
    print(f"Delete and Reimport Script")
    print(f"{'='*80}")
    print(f"CSV File: {csv_path}")

    # Step 1: Extract run_ids
    print(f"\nStep 1: Extracting run_ids from CSV...")
    run_ids = get_run_ids_from_csv(csv_path)
    print(f"  ✓ Found {len(run_ids)} run_ids")

    # Step 2: Get file paths before deletion
    print(f"\nStep 2: Getting file paths from metadata...")
    file_paths = get_file_paths_for_run_ids(run_ids)
    print(f"  ✓ Found {len(file_paths)} file paths")

    # Show missing file paths
    missing = set(run_ids) - set(file_paths.keys())
    if missing:
        print(f"  ⚠ Warning: {len(missing)} run_ids have no metadata:")
        for run_id in list(missing)[:5]:
            print(f"    - {run_id}")
        if len(missing) > 5:
            print(f"    ... and {len(missing) - 5} more")

    # Confirmation
    print(f"\n{'='*80}")
    print(f"WARNING: This will DELETE all data for {len(run_ids)} run_ids!")
    print(f"Tables affected:")
    print(f"  - raw_uatl_statements")
    print(f"  - processed_uatl_statements")
    print(f"  - metadata")
    print(f"  - summary")
    print(f"{'='*80}")

    response = input("\nProceed with deletion and reimport? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return

    # Step 3: Delete data
    delete_data_for_run_ids(run_ids)

    # Step 4: Reimport files
    if file_paths:
        reimport_files(file_paths)
    else:
        print("\nNo files to reimport (no file paths found)")

    print(f"\n{'='*80}")
    print(f"✅ Process complete!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
