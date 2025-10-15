#!/usr/bin/env python3
"""
Compare all available PDF libraries for speed and accuracy
"""
import time
import fitz  # PyMuPDF
import pdfplumber
import pypdfium2 as pdfium
from pdfminer.high_level import extract_text_to_fp
from io import StringIO

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


def analyze_text_lines(lines, page_num):
    """Common analysis logic for all libraries"""
    header_positions = []
    for line_num, line in enumerate(lines):
        if is_header_row(line):
            header_positions.append(line_num)

    is_bad = False
    if len(header_positions) > 1:
        is_bad = True
    elif page_num > 1 and len(header_positions) == 1 and header_positions[0] != 0:
        is_bad = True

    return is_bad, header_positions


def test_pdfplumber(pdf_path):
    """Test pdfplumber (baseline)"""
    start = time.time()
    bad_pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')
            is_bad, positions = analyze_text_lines(lines, page_num)
            if is_bad:
                bad_pages[page_num] = positions

    elapsed = time.time() - start
    return elapsed, bad_pages


def test_pymupdf(pdf_path):
    """Test PyMuPDF with layout mode"""
    start = time.time()
    bad_pages = {}

    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Try "blocks" mode which preserves layout better
        text = page.get_text("text")
        if not text:
            continue

        lines = text.split('\n')
        page_index = page_num + 1
        is_bad, positions = analyze_text_lines(lines, page_index)
        if is_bad:
            bad_pages[page_index] = positions

    doc.close()
    elapsed = time.time() - start
    return elapsed, bad_pages


def test_pypdfium2(pdf_path):
    """Test pypdfium2"""
    start = time.time()
    bad_pages = {}

    pdf = pdfium.PdfDocument(pdf_path)
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        if not text:
            continue

        lines = text.split('\n')
        page_index = page_num + 1
        is_bad, positions = analyze_text_lines(lines, page_index)
        if is_bad:
            bad_pages[page_index] = positions

    elapsed = time.time() - start
    return elapsed, bad_pages


def test_pdfminer(pdf_path):
    """Test pdfminer.six"""
    start = time.time()
    bad_pages = {}

    # pdfminer doesn't have easy page-by-page extraction, skip for now
    # This would require more complex implementation
    elapsed = time.time() - start
    return elapsed, {}


if __name__ == '__main__':
    print("PDF Library Comparison Test")
    print(f"Testing: {pdf_path}")
    print("=" * 100)

    results = []

    # Test 1: pdfplumber (baseline)
    print("\n1. Testing pdfplumber (baseline)...")
    try:
        time1, pages1 = test_pdfplumber(pdf_path)
        print(f"   ✅ Time: {time1:.2f}s | Found {len(pages1)} manipulated pages")
        results.append(("pdfplumber", time1, len(pages1), pages1))
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: PyMuPDF
    print("\n2. Testing PyMuPDF (fitz)...")
    try:
        time2, pages2 = test_pymupdf(pdf_path)
        print(f"   ✅ Time: {time2:.2f}s | Found {len(pages2)} manipulated pages")
        results.append(("PyMuPDF", time2, len(pages2), pages2))
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: pypdfium2
    print("\n3. Testing pypdfium2...")
    try:
        time3, pages3 = test_pypdfium2(pdf_path)
        print(f"   ✅ Time: {time3:.2f}s | Found {len(pages3)} manipulated pages")
        results.append(("pypdfium2", time3, len(pages3), pages3))
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY:")
    print("=" * 100)
    print(f"{'Library':<15} {'Time (s)':<12} {'Pages Found':<15} {'vs pdfplumber':<20} {'Speedup':<10}")
    print("-" * 100)

    baseline_time = results[0][1] if results else 0
    baseline_pages = results[0][3] if results else {}

    for name, time_taken, page_count, pages in results:
        speedup = baseline_time / time_taken if time_taken > 0 else 0

        # Check accuracy
        if name == "pdfplumber":
            accuracy = "baseline"
        else:
            # Check if same pages detected
            same_pages = set(pages.keys()) == set(baseline_pages.keys())
            accuracy = "✅ SAME" if same_pages else f"❌ DIFF ({len(set(pages.keys()) - set(baseline_pages.keys()))} extra, {len(set(baseline_pages.keys()) - set(pages.keys()))} missing)"

        print(f"{name:<15} {time_taken:>8.2f}s    {page_count:<15} {accuracy:<20} {speedup:>6.1f}x")

    print("\n" + "=" * 100)
    print("RECOMMENDATION:")

    # Find fastest accurate option
    accurate_options = []
    for name, time_taken, page_count, pages in results:
        if name == "pdfplumber":
            continue
        if set(pages.keys()) == set(baseline_pages.keys()):
            accurate_options.append((name, time_taken, baseline_time / time_taken))

    if accurate_options:
        best = min(accurate_options, key=lambda x: x[1])
        print(f"  Use {best[0]} - {best[2]:.1f}x faster with same accuracy as pdfplumber")
    else:
        print(f"  Stick with pdfplumber - other libraries have different results")
