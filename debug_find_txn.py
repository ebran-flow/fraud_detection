"""Find where the 11:45 and 11:46 transactions are."""
import pdfplumber

pdf_path = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/statements/68babf7f23139.pdf"

search_times = ['11:45', '11:46']

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        for search_time in search_times:
            if search_time in text and '31-08-25' in text:
                print(f"\n=== Found {search_time} on page {i+1} ===")
                # Find the lines containing the time
                lines = text.split('\n')
                for j, line in enumerate(lines):
                    if search_time in line and '31-08-25' in line:
                        print(f"Line {j}: {line}")
                        # Print context
                        if j > 0:
                            print(f"Before: {lines[j-1]}")
                        if j < len(lines) - 1:
                            print(f"After: {lines[j+1]}")
