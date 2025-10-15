#!/usr/bin/env python3
"""
Test PyMuPDF with different text extraction modes for better layout preservation
"""
import time
import fitz

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


def test_mode(pdf_path, mode, mode_name):
    """Test a specific PyMuPDF text extraction mode"""
    start = time.time()
    bad_pages = {}

    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text(mode)
        if not text:
            continue

        lines = text.split('\n')
        header_positions = []

        for line_num, line in enumerate(lines):
            if is_header_row(line):
                header_positions.append(line_num)

        page_index = page_num + 1
        if len(header_positions) > 1:
            bad_pages[page_index] = f"{len(header_positions)} headers"
        elif page_index > 1 and len(header_positions) == 1 and header_positions[0] != 0:
            bad_pages[page_index] = f"Header at line {header_positions[0]}"

    doc.close()
    elapsed = time.time() - start
    return elapsed, bad_pages


if __name__ == '__main__':
    print("PyMuPDF Text Extraction Mode Comparison")
    print(f"Testing: {pdf_path}")
    print("=" * 100)

    # Expected result from pdfplumber/pypdfium2
    expected_pages = 38

    modes = [
        ("text", "Plain text"),
        ("blocks", "Text blocks (preserves layout)"),
        ("words", "Word-by-word"),
        ("html", "HTML format"),
        ("dict", "Dictionary format"),
        ("rawdict", "Raw dictionary"),
        ("json", "JSON format"),
    ]

    results = []
    for mode, description in modes:
        print(f"\nTesting mode: {mode} - {description}")
        try:
            time_taken, bad_pages = test_mode(pdf_path, mode, description)
            accuracy = "✅ MATCH" if len(bad_pages) == expected_pages else f"❌ {len(bad_pages)} pages"
            print(f"  Time: {time_taken:.2f}s | Pages: {len(bad_pages)} | {accuracy}")
            results.append((mode, description, time_taken, len(bad_pages)))
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY:")
    print("=" * 100)
    print(f"{'Mode':<12} {'Description':<35} {'Time (s)':<12} {'Pages':<8} {'Accuracy'}")
    print("-" * 100)

    for mode, description, time_taken, page_count in results:
        accuracy = "✅ MATCH" if page_count == expected_pages else f"❌ OFF"
        print(f"{mode:<12} {description:<35} {time_taken:>8.2f}s    {page_count:<8} {accuracy}")

    print("\n" + "=" * 100)
    # Find accurate modes
    accurate = [(m, d, t, p) for m, d, t, p in results if p == expected_pages]
    if accurate:
        best = min(accurate, key=lambda x: x[2])
        print(f"BEST: {best[0]} mode - {best[2]:.2f}s with correct accuracy")
    else:
        print("No PyMuPDF mode matches pdfplumber accuracy - stick with pypdfium2")
