"""Debug script to examine statement structure."""
import pdfplumber
import pandas as pd

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/statements/68babf7f23139.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    # Check first page
    page = pdf.pages[0]
    print("\n=== FIRST PAGE TEXT ===")
    print(page.extract_text()[:1000])

    print("\n=== FIRST PAGE TABLES ===")
    tables = page.extract_tables()
    print(f"Number of tables on first page: {len(tables)}")

    if tables:
        print("\n=== FIRST TABLE (first 10 rows) ===")
        for i, row in enumerate(tables[0][:10]):
            print(f"Row {i}: {row}")

    # Check last page
    last_page = pdf.pages[-1]
    print(f"\n=== LAST PAGE (page {len(pdf.pages)}) ===")
    print(last_page.extract_text()[-500:])

    tables_last = last_page.extract_tables()
    if tables_last:
        print("\n=== LAST TABLE (last 5 rows) ===")
        for i, row in enumerate(tables_last[0][-5:]):
            print(f"Row {i}: {row}")
