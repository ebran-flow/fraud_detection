#!/usr/bin/env python3
"""
Test the speed of importing Airtel PDFs with current pdfplumber-based parser
This will help us understand if switching to pypdfium2 will provide significant benefits
"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from app.services.parsers.pdf_utils import extract_data_from_pdf

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3307')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def test_import_speed(sample_size=10):
    """Test import speed on a sample of Airtel PDFs"""
    print('=' * 80)
    print(f'TESTING PDF IMPORT SPEED (Sample size: {sample_size})')
    print('=' * 80)
    print()

    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/fraud_detection'
    )

    with engine.connect() as conn:
        # Get sample of Airtel PDFs
        result = conn.execute(text(f"""
            SELECT pdf_path, run_id, format
            FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            AND pdf_path IS NOT NULL
            ORDER BY RAND()
            LIMIT {sample_size}
        """))

        pdfs = list(result)
        print(f'Found {len(pdfs)} PDFs to test')
        print()

    # Test each PDF
    total_time = 0
    total_transactions = 0
    total_pages = 0
    results = []

    for idx, (pdf_path, run_id, pdf_format) in enumerate(pdfs, 1):
        # Fix path if needed
        if pdf_path and not os.path.exists(pdf_path):
            alt_path = pdf_path.replace('/app/', '/home/ebran/Developer/projects/airtel_fraud_detection/backend/')
            if os.path.exists(alt_path):
                pdf_path = alt_path

        if not os.path.exists(pdf_path):
            print(f'[{idx}/{len(pdfs)}] ⚠️  PDF not found: {run_id}')
            continue

        print(f'[{idx}/{len(pdfs)}] Processing: {run_id} ({pdf_format})')

        try:
            start = time.time()
            df, acc_number, quality_issues, header_rows = extract_data_from_pdf(pdf_path)
            elapsed = time.time() - start

            # Get page count
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)

            total_time += elapsed
            total_transactions += len(df)
            total_pages += page_count

            print(f'  ✅ {elapsed:.2f}s | {len(df)} transactions | {page_count} pages | {elapsed/page_count:.3f}s/page')

            results.append({
                'run_id': run_id,
                'format': pdf_format,
                'time': elapsed,
                'transactions': len(df),
                'pages': page_count,
                'time_per_page': elapsed/page_count,
                'quality_issues': quality_issues,
                'header_rows': header_rows
            })

        except Exception as e:
            print(f'  ❌ Error: {str(e)[:80]}')
            continue

    # Summary statistics
    print()
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'Total PDFs processed: {len(results)}')
    print(f'Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)')
    print(f'Average time per PDF: {total_time/len(results):.2f}s')
    print(f'Total transactions extracted: {total_transactions}')
    print(f'Total pages processed: {total_pages}')
    print(f'Average time per page: {total_time/total_pages:.3f}s')
    print(f'Processing speed: {total_pages/total_time:.2f} pages/second')
    print()

    # Extrapolate to full dataset
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total
            FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            AND pdf_path IS NOT NULL
        """))
        total_pdfs = result.fetchone()[0]

    estimated_time = (total_time / len(results)) * total_pdfs
    print('=' * 80)
    print('EXTRAPOLATION TO FULL DATASET')
    print('=' * 80)
    print(f'Total Airtel PDFs in database: {total_pdfs}')
    print(f'Estimated total processing time: {estimated_time:.0f}s ({estimated_time/3600:.1f} hours)')
    print()

    # Breakdown by format
    format_1 = [r for r in results if r['format'] == 'format_1']
    format_2 = [r for r in results if r['format'] == 'format_2']

    if format_1:
        avg_time_f1 = sum(r['time'] for r in format_1) / len(format_1)
        print(f'Format 1: {len(format_1)} PDFs, avg {avg_time_f1:.2f}s/PDF')

    if format_2:
        avg_time_f2 = sum(r['time'] for r in format_2) / len(format_2)
        print(f'Format 2: {len(format_2)} PDFs, avg {avg_time_f2:.2f}s/PDF')

    return results

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample-size', type=int, default=10, help='Number of PDFs to test')
    args = parser.parse_args()

    results = test_import_speed(args.sample_size)
