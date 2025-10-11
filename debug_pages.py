"""Check what's on the pages after 75."""
import pdfplumber

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/statements/68babf7f23139.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    # Check page 75 (index 74)
    print("\n=== PAGE 75 ===")
    page = pdf.pages[74]
    text = page.extract_text()
    print(text[-1000:])

    # Check if there's a page 76
    if len(pdf.pages) > 75:
        print("\n=== PAGE 76 ===")
        page = pdf.pages[75]
        text = page.extract_text()
        print(text)
