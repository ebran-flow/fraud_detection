#!/usr/bin/env python3
"""
Check UMTN File Fields
Examines multiple UMTN files to understand field structure
"""
import sys
from pathlib import Path
import pandas as pd
import xlrd3 as xlrd

sys.path.insert(0, str(Path(__file__).parent))


def jsonify_worksheet(worksheet):
    """Convert xlrd worksheet to list of dictionaries"""
    rows_dict = []
    header = [cell.value for cell in worksheet.row(0)]
    for row_idx in range(1, min(worksheet.nrows, 6)):  # Get first 5 rows
        row_dict = {}
        NUMBER_TYPE = 2
        for col_idx, cell in enumerate(worksheet.row(row_idx)):
            cell_value = str(int(float(cell.value))) if cell.ctype == NUMBER_TYPE else cell.value
            row_dict[header[col_idx]] = cell_value
        rows_dict.append(row_dict)
    return header, rows_dict


def check_xlsx_file(file_path):
    """Check XLSX file structure"""
    print(f"\n{'='*70}")
    print(f"XLSX File: {Path(file_path).name}")
    print(f"{'='*70}")

    try:
        with open(file_path, 'rb') as f:
            file_contents = f.read()

        workbook = xlrd.open_workbook(file_contents=file_contents)
        sheet_name = workbook.sheet_names()[0]
        loaded_sheet = workbook.sheet_by_name(sheet_name)
        headers, rows = jsonify_worksheet(loaded_sheet)

        print(f"Columns: {headers}")
        print(f"\nFirst 3 rows:")
        for i, row in enumerate(rows[:3], 1):
            print(f"\n  Row {i}:")
            for col in headers:
                print(f"    {col}: {row.get(col, 'N/A')}")

        return headers
    except Exception as e:
        print(f"Error reading XLSX: {e}")
        return None


def check_csv_file(file_path):
    """Check CSV file structure"""
    print(f"\n{'='*70}")
    print(f"CSV File: {Path(file_path).name}")
    print(f"{'='*70}")

    try:
        df = pd.read_csv(file_path, nrows=3)
        headers = df.columns.tolist()

        print(f"Columns: {headers}")
        print(f"\nFirst 3 rows:")
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            print(f"\n  Row {i}:")
            for col in headers:
                print(f"    {col}: {row[col]}")

        return headers
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None


def main():
    """Check multiple UMTN files"""
    extracted_dir = Path(__file__).parent / "docs" / "data" / "UMTN" / "extracted"

    # Get sample files
    xlsx_files = list(extracted_dir.glob("*.xlsx"))[:3]
    csv_files = list(extracted_dir.glob("*.csv"))[:3]

    print(f"\n{'#'*70}")
    print(f"# Checking UMTN File Structure")
    print(f"# XLSX files: {len(xlsx_files)}, CSV files: {len(csv_files)}")
    print(f"{'#'*70}")

    all_headers = set()

    # Check XLSX files
    for file_path in xlsx_files:
        headers = check_xlsx_file(str(file_path))
        if headers:
            all_headers.update(headers)

    # Check CSV files
    for file_path in csv_files:
        headers = check_csv_file(str(file_path))
        if headers:
            all_headers.update(headers)

    # Summary
    print(f"\n{'='*70}")
    print(f"Summary: All Unique Columns Found")
    print(f"{'='*70}")
    for col in sorted(all_headers):
        print(f"  - {col}")
    print()


if __name__ == '__main__':
    main()
