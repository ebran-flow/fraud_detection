#!/usr/bin/env python3
"""
Debug text extraction differences between pdfplumber and PyMuPDF
"""
import fitz
import pdfplumber

pdf_path = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/68cba9c59220d.pdf'

print("Comparing text extraction from page 3 (known manipulation page)")
print("=" * 100)

# pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[2]  # Page 3 (0-indexed)
    plumber_text = page.extract_text()
    plumber_lines = plumber_text.split('\n') if plumber_text else []

print("\n1. PDFPLUMBER - First 10 lines:")
print("-" * 100)
for i, line in enumerate(plumber_lines[:10]):
    print(f"Line {i}: {line[:120]}")

# PyMuPDF
doc = fitz.open(pdf_path)
page = doc[2]  # Page 3
fitz_text = page.get_text()
fitz_lines = fitz_text.split('\n') if fitz_text else []
doc.close()

print("\n2. PYMUPDF - First 10 lines:")
print("-" * 100)
for i, line in enumerate(fitz_lines[:10]):
    print(f"Line {i}: {line[:120]}")

print("\n" + "=" * 100)
print("ANALYSIS:")
print(f"  pdfplumber lines: {len(plumber_lines)}")
print(f"  PyMuPDF lines: {len(fitz_lines)}")

# Check if header is detected
def is_header_row(row_text: str) -> bool:
    row_lower = row_text.lower()
    header_patterns = [
        'transaction id', 'transation id', 'date transaction',
        'date/time', 'transaction type', 'description',
        'from account', 'to account', 'mobile number',
    ]
    matches = sum(1 for pattern in header_patterns if pattern in row_lower)
    return matches >= 2

print("\nHeader detection in pdfplumber lines:")
for i, line in enumerate(plumber_lines[:10]):
    if is_header_row(line):
        print(f"  Line {i}: HEADER DETECTED - {line[:100]}")

print("\nHeader detection in PyMuPDF lines:")
for i, line in enumerate(fitz_lines[:10]):
    if is_header_row(line):
        print(f"  Line {i}: HEADER DETECTED - {line[:100]}")
