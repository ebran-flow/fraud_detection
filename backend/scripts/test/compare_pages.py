#!/usr/bin/env python3
"""
Compare page structure between clean and flagged pages
"""
import pypdfium2 as pdfium

# Check clean statement
clean_pdf = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/6875f5c56cfaa.pdf'
# Check flagged statement
flagged_pdf = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/data/UATL/extracted/68a6b12818ebb.pdf'

def check_page(pdf_path, page_num):
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[page_num - 1]  # Convert to 0-indexed
    textpage = page.get_textpage()
    text = textpage.get_text_range()
    lines = text.split('\n')

    print(f"\n{'='*100}")
    print(f"PDF: {pdf_path.split('/')[-1]}")
    print(f"Page: {page_num}")
    print(f"Total lines: {len(lines)}")
    print(f"\nFirst 5 lines:")
    print("-" * 100)
    for i in range(min(5, len(lines))):
        print(f"Line {i}: '{lines[i][:80]}'")

print("COMPARISON: Clean vs Flagged PDFs")
print("=" * 100)

# Check page 2 of both
check_page(clean_pdf, 2)
check_page(flagged_pdf, 2)

# Check page 3 to see pattern
check_page(clean_pdf, 3)
check_page(flagged_pdf, 3)

print("\n" + "=" * 100)
print("ANALYSIS:")
print("If clean PDFs also have page numbers at Line 0, then this is a FALSE POSITIVE")
print("We should skip checking header position on pages 2+ if Line 0 looks like a page number")
