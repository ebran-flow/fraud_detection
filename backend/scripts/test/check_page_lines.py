#!/usr/bin/env python3
"""
Check what text is extracted from a specific page
"""
import pypdfium2 as pdfium

pdf_path = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/68a6b12818ebb.pdf'

pdf = pdfium.PdfDocument(pdf_path)
page = pdf[1]  # Page 2 (0-indexed)
textpage = page.get_textpage()
text = textpage.get_text_range()

lines = text.split('\n')

print(f"PDF: {pdf_path}")
print(f"Page: 2")
print(f"Total lines extracted: {len(lines)}")
print("\nFirst 10 lines:")
print("=" * 100)

for i, line in enumerate(lines[:10]):
    print(f"Line {i}: '{line}'")
    if not line.strip():
        print(f"         ^ EMPTY LINE")

print("\n" + "=" * 100)
print("\nNote: Line 0 is the FIRST line. If header is at line 1, it means there's")
print("      something (maybe blank) before it, which indicates manipulation.")
