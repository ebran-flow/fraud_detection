"""Debug script to examine the second Airtel format."""
import pdfplumber

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/uploaded_pdfs/682c8f6fcefaa.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    # Check first page
    page = pdf.pages[0]
    print("\n=== FIRST PAGE TEXT (first 1500 chars) ===")
    print(page.extract_text()[:1500])

    print("\n=== FIRST PAGE TABLES ===")
    tables = page.extract_tables()
    print(f"Number of tables on first page: {len(tables)}")

    if tables:
        print("\n=== FIRST TABLE (first 10 rows) ===")
        for i, row in enumerate(tables[0][:10]):
            print(f"Row {i}: {row}")

    # Check if there are more pages
    if len(pdf.pages) > 1:
        print(f"\n=== SECOND PAGE TEXT (first 1000 chars) ===")
        print(pdf.pages[1].extract_text()[:1000])

        tables_p2 = pdf.pages[1].extract_tables()
        if tables_p2:
            print("\n=== SECOND PAGE FIRST TABLE (first 5 rows) ===")
            for i, row in enumerate(tables_p2[0][:5]):
                print(f"Row {i}: {row}")
