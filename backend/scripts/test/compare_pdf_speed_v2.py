#!/usr/bin/env python3
"""
Compare speed of PDF libraries with improved PyMuPDF row detection
"""
import os
import time
import fitz  # PyMuPDF
import pdfplumber

pdf_path = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/68cba9c59220d.pdf'


def is_header_row(row_text: str) -> bool:
    """Check if text looks like a table header row"""
    row_lower = row_text.lower()
    header_patterns = [
        'transaction id', 'transation id', 'date transaction',
        'date/time', 'transaction type', 'description',
        'from account', 'to account', 'mobile number',
    ]
    matches = sum(1 for pattern in header_patterns if pattern in row_lower)
    return matches >= 2


def test_pdfplumber(pdf_path):
    """Test pdfplumber speed"""
    start = time.time()
    bad_pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')
            header_positions = []

            for line_num, line in enumerate(lines):
                if is_header_row(line):
                    header_positions.append(line_num)

            if len(header_positions) > 1:
                bad_pages[page_num] = f"{len(header_positions)} headers"
            elif page_num > 1 and len(header_positions) == 1 and header_positions[0] != 0:
                bad_pages[page_num] = f"Header at line {header_positions[0]}"

    elapsed = time.time() - start
    return elapsed, len(bad_pages)


def test_pymupdf_sliding_window(pdf_path):
    """Test PyMuPDF with sliding window approach to detect headers"""
    start = time.time()
    bad_pages = {}

    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if not text:
            continue

        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Use sliding window of 10 lines to detect header patterns
        header_positions = []
        window_size = 10

        for i in range(len(lines) - window_size + 1):
            window = ' '.join(lines[i:i+window_size])
            if is_header_row(window):
                # Found header pattern, record the starting line
                header_positions.append(i)

        page_index = page_num + 1  # Convert to 1-indexed

        if len(header_positions) > 1:
            bad_pages[page_index] = f"{len(header_positions)} headers"
        elif page_index > 1 and len(header_positions) == 1 and header_positions[0] != 0:
            bad_pages[page_index] = f"Header at line {header_positions[0]}"

    doc.close()
    elapsed = time.time() - start
    return elapsed, len(bad_pages)


if __name__ == '__main__':
    print("PDF Speed Comparison Test (Improved)")
    print(f"Testing: {pdf_path}")
    print("=" * 80)

    # Test pdfplumber
    print("\n1. Testing pdfplumber...")
    plumber_time, plumber_bad_pages = test_pdfplumber(pdf_path)
    print(f"   Time: {plumber_time:.2f}s")
    print(f"   Found {plumber_bad_pages} manipulated pages")

    # Test PyMuPDF with sliding window
    print("\n2. Testing PyMuPDF (sliding window)...")
    fitz_time, fitz_bad_pages = test_pymupdf_sliding_window(pdf_path)
    print(f"   Time: {fitz_time:.2f}s")
    print(f"   Found {fitz_bad_pages} manipulated pages")

    # Comparison
    print("\n" + "=" * 80)
    print("RESULTS:")
    print(f"  pdfplumber:  {plumber_time:.2f}s ({plumber_bad_pages} pages)")
    print(f"  PyMuPDF:     {fitz_time:.2f}s ({fitz_bad_pages} pages)")
    if fitz_time > 0:
        speedup = plumber_time / fitz_time
        print(f"\n  PyMuPDF is {speedup:.1f}x FASTER than pdfplumber")
        print(f"  Time saved per PDF: {plumber_time - fitz_time:.2f}s")
