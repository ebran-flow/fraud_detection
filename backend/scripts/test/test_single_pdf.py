#!/usr/bin/env python3
"""
Test header manipulation detection on a single PDF
"""
import os
import pdfplumber

def is_header_row(row_text: str) -> bool:
    """Check if text looks like a table header row"""
    row_lower = row_text.lower()
    header_patterns = [
        'transaction id',
        'transation id',
        'date transaction',
        'date/time',
        'transaction type',
        'description',
        'from account',
        'to account',
        'mobile number',
    ]
    matches = sum(1 for pattern in header_patterns if pattern in row_lower)
    return matches >= 2


def check_pdf_detailed(pdf_path: str):
    """Scan PDF and show detailed header analysis"""
    print(f"Analyzing: {pdf_path}\n")
    print("=" * 100)

    bad_pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}\n")

        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                print(f"Page {page_num}: No text")
                continue

            lines = text.split('\n')
            header_positions = []

            for line_num, line in enumerate(lines):
                if is_header_row(line):
                    header_positions.append(line_num)

            # Show analysis
            if len(header_positions) > 1:
                print(f"🚨 Page {page_num}: {len(header_positions)} headers at positions {header_positions} - MANIPULATION!")
                bad_pages[page_num] = f"{len(header_positions)} headers"
                for pos in header_positions:
                    print(f"     Line {pos}: {lines[pos][:100]}")
            elif len(header_positions) == 1:
                pos = header_positions[0]
                if page_num > 1 and pos != 0:
                    print(f"🚨 Page {page_num}: Header at line {pos} (not first row) - MANIPULATION!")
                    bad_pages[page_num] = f"Header at line {pos}"
                    print(f"     Line {pos}: {lines[pos][:100]}")
                else:
                    status = "✅" if page_num == 1 or pos == 0 else "🚨"
                    print(f"{status} Page {page_num}: 1 header at line {pos} - {'OK' if status == '✅' else 'MANIPULATION'}")
            else:
                print(f"⚠️  Page {page_num}: No header found")

            print()

    print("=" * 100)
    print(f"\nSUMMARY:")
    print(f"  Total pages: {total_pages}")
    print(f"  Manipulated pages: {len(bad_pages)}")
    if bad_pages:
        print(f"\n  Flagged pages:")
        for page_num, reason in bad_pages.items():
            print(f"    Page {page_num}: {reason}")


if __name__ == '__main__':
    run_id = '68cba9c59220d'

    # Try multiple possible paths
    paths = [
        f'/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/{run_id}.pdf',
        f'/app/docs/data/UATL/extracted/{run_id}.pdf',
    ]

    pdf_path = None
    for path in paths:
        if os.path.exists(path):
            pdf_path = path
            break

    if pdf_path:
        check_pdf_detailed(pdf_path)
    else:
        print(f"PDF not found for run_id: {run_id}")
        print("Tried paths:")
        for path in paths:
            print(f"  - {path}")
