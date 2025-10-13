#!/usr/bin/env python3
"""
Comprehensive UMTN Testing
Test balance logic across all months and file formats
"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parsers.umtn_parser import parse_umtn_excel
from app.services.db import SessionLocal
from app.services import crud_v2 as crud
from app.services.processor import process_statement
from app.models.metadata import Metadata
from app.services.mapper import enrich_metadata_with_mapper
from sqlalchemy import text


def main():
    """Comprehensive UMTN testing"""
    print(f"\n{'='*80}")
    print("COMPREHENSIVE UMTN TESTING")
    print(f"{'='*80}\n")

    # Step 1: Read mapper.csv and filter UMTN files
    print("Step 1: Analyzing mapper.csv...")
    print("-" * 80)

    mapper_path = Path(__file__).parent.parent / "docs" / "data" / "statements" / "mapper.csv"
    df_mapper = pd.read_csv(mapper_path)

    # Filter for UMTN with score_calc_success
    umtn_files = df_mapper[
        (df_mapper['acc_prvdr_code'] == 'UMTN') &
        (df_mapper['lambda_status'] == 'score_calc_success')
    ].copy()

    print(f"Total UMTN files with score_calc_success: {len(umtn_files)}")

    # Extract month from created_date
    umtn_files['created_date'] = pd.to_datetime(umtn_files['created_date'])
    umtn_files['month'] = umtn_files['created_date'].dt.to_period('M')

    # Group by month
    months = umtn_files['month'].value_counts().sort_index()
    print(f"\nFiles by month:")
    for month, count in months.items():
        print(f"  {month}: {count} files")

    # Step 2: Sample files per month
    print(f"\n{'='*80}")
    print("Step 2: Sampling files (2 XLSX + 2 CSV per month)...")
    print("-" * 80)

    extracted_dir = Path(__file__).parent.parent / "docs" / "data" / "UMTN" / "extracted"
    samples = []

    for month in months.index:
        month_files = umtn_files[umtn_files['month'] == month]
        print(f"\n{month}:")

        # Get available file types
        xlsx_count = 0
        csv_count = 0

        for _, row in month_files.iterrows():
            run_id = row['run_id']

            # Check for XLSX file
            xlsx_file = extracted_dir / f"{run_id}.xlsx"
            if xlsx_file.exists() and xlsx_count < 2:
                samples.append({
                    'month': str(month),
                    'run_id': run_id,
                    'file_path': str(xlsx_file),
                    'file_type': 'xlsx',
                    'acc_number': row['acc_number']
                })
                xlsx_count += 1
                print(f"  ✓ XLSX: {run_id}")

            # Check for CSV file
            csv_file = extracted_dir / f"{run_id}.csv"
            if csv_file.exists() and csv_count < 2:
                samples.append({
                    'month': str(month),
                    'run_id': run_id,
                    'file_path': str(csv_file),
                    'file_type': 'csv',
                    'acc_number': row['acc_number']
                })
                csv_count += 1
                print(f"  ✓ CSV: {run_id}")

            if xlsx_count >= 2 and csv_count >= 2:
                break

        if xlsx_count < 2 or csv_count < 2:
            print(f"  ⚠️  Warning: Only found {xlsx_count} XLSX and {csv_count} CSV files")

    print(f"\n{'='*80}")
    print(f"Total samples: {len(samples)} files")
    print(f"{'='*80}\n")

    # Step 3: Process each sample and check for format variations
    print("Step 3: Processing samples and checking formats...")
    print("-" * 80)

    db = SessionLocal()
    results = []
    format_variations = defaultdict(list)

    try:
        for i, sample in enumerate(samples, 1):
            print(f"\n[{i}/{len(samples)}] Processing {sample['month']} - {sample['file_type'].upper()}: {sample['run_id']}")
            print("  " + "-" * 76)

            try:
                # Parse file and check headers
                raw_statements, metadata = parse_umtn_excel(sample['file_path'], sample['run_id'])

                if not raw_statements:
                    print(f"  ✗ No transactions parsed")
                    results.append({
                        **sample,
                        'status': 'FAILED',
                        'error': 'No transactions parsed'
                    })
                    continue

                # Check headers/columns
                first_txn = raw_statements[0]
                columns = sorted(first_txn.keys())
                column_signature = ','.join(columns)
                format_variations[column_signature].append(sample['run_id'])

                print(f"  Columns: {len(columns)} fields")

                # Enrich metadata
                metadata = enrich_metadata_with_mapper(metadata, sample['run_id'])

                # Delete existing data if any
                db.execute(text("DELETE FROM umtn_processed_statements WHERE run_id = :run_id"), {"run_id": sample['run_id']})
                db.execute(text("DELETE FROM umtn_raw_statements WHERE run_id = :run_id"), {"run_id": sample['run_id']})
                db.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {"run_id": sample['run_id']})
                db.execute(text("DELETE FROM metadata WHERE run_id = :run_id"), {"run_id": sample['run_id']})
                db.commit()

                # Import to database
                metadata_obj = crud.create(db, Metadata, metadata)
                crud.bulk_create_raw(db, 'UMTN', raw_statements)

                print(f"  ✓ Imported {len(raw_statements)} transactions")

                # Process statement
                result = process_statement(db, sample['run_id'])

                # Report results
                print(f"  Balance Match: {result['balance_match']}")
                print(f"  Verification: {result['verification_status']}")
                print(f"  Processed: {result['processed_count']} transactions")
                print(f"  Duplicates: {result['duplicate_count']}")

                results.append({
                    **sample,
                    'status': result['verification_status'],
                    'balance_match': result['balance_match'],
                    'txn_count': result['processed_count'],
                    'duplicates': result['duplicate_count'],
                    'columns': len(columns)
                })

            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    **sample,
                    'status': 'ERROR',
                    'error': str(e)
                })

    finally:
        db.close()

    # Step 4: Summary report
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}\n")

    # Overall statistics
    total = len(results)
    passed = sum(1 for r in results if r.get('status') == 'PASS')
    failed = sum(1 for r in results if r.get('status') == 'FAIL')
    errors = sum(1 for r in results if r.get('status') == 'ERROR')

    print(f"Total Samples: {total}")
    print(f"  ✓ Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"  ✗ Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"  ⚠ Errors: {errors} ({errors/total*100:.1f}%)")

    # By file type
    print(f"\nBy File Type:")
    for file_type in ['xlsx', 'csv']:
        type_results = [r for r in results if r.get('file_type') == file_type]
        if type_results:
            type_passed = sum(1 for r in type_results if r.get('status') == 'PASS')
            print(f"  {file_type.upper()}: {type_passed}/{len(type_results)} passed")

    # By month
    print(f"\nBy Month:")
    month_groups = defaultdict(list)
    for r in results:
        month_groups[r['month']].append(r)

    for month in sorted(month_groups.keys()):
        month_results = month_groups[month]
        month_passed = sum(1 for r in month_results if r.get('status') == 'PASS')
        print(f"  {month}: {month_passed}/{len(month_results)} passed")

    # Format variations
    print(f"\n{'='*80}")
    print("FORMAT VARIATIONS")
    print(f"{'='*80}\n")

    if len(format_variations) == 1:
        print("✓ All files have identical column structure!")
        print(f"  Columns: {list(format_variations.keys())[0]}")
    else:
        print(f"⚠ Found {len(format_variations)} different column structures:")
        for i, (columns, run_ids) in enumerate(format_variations.items(), 1):
            print(f"\n  Format {i} ({len(run_ids)} files):")
            print(f"    Columns: {columns}")
            print(f"    Sample run_ids: {', '.join(run_ids[:3])}")

    # Failed cases
    failed_results = [r for r in results if r.get('status') in ['FAIL', 'ERROR']]
    if failed_results:
        print(f"\n{'='*80}")
        print("FAILED CASES")
        print(f"{'='*80}\n")
        for r in failed_results:
            print(f"{r['run_id']} ({r['file_type'].upper()}):")
            print(f"  Status: {r['status']}")
            if 'error' in r:
                print(f"  Error: {r['error']}")
            print()

    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
