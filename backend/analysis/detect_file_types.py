#!/usr/bin/env python3
"""
Detect Actual File Types
Distinguish real CSV files from XLSX files with .csv extension
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def detect_file_type(file_path):
    """
    Detect actual file type by reading magic bytes

    Returns: 'xlsx', 'csv', 'unknown'
    """
    try:
        with open(file_path, 'rb') as f:
            # Read first few bytes
            magic = f.read(8)

            # XLSX files start with PK (ZIP signature)
            if magic[:2] == b'PK':
                return 'xlsx'

            # CSV files are text, try reading as text
            f.seek(0)
            try:
                # Try to read first line as text
                first_line = f.read(200).decode('utf-8', errors='strict')
                # If it looks like CSV (has commas and no binary), it's CSV
                if ',' in first_line and '\x00' not in first_line:
                    return 'csv'
            except UnicodeDecodeError:
                pass

            return 'unknown'
    except Exception as e:
        return f'error: {e}'


def main():
    """Detect file types in extracted directory"""
    extracted_dir = Path(__file__).parent.parent / "docs" / "data" / "UMTN" / "extracted"

    print(f"\n{'='*80}")
    print("DETECTING FILE TYPES")
    print(f"{'='*80}\n")

    # Get all CSV files
    csv_files = list(extracted_dir.glob("*.csv"))
    print(f"Found {len(csv_files)} files with .csv extension")

    # Sample and detect
    sample_size = 50
    samples = csv_files[:sample_size] if len(csv_files) > sample_size else csv_files

    print(f"Sampling {len(samples)} files...\n")

    actual_csv = 0
    actual_xlsx = 0
    unknown = 0

    print(f"{'Filename':<20} {'Extension':<10} {'Actual Type':<15}")
    print("-" * 80)

    for file_path in samples:
        actual_type = detect_file_type(file_path)
        print(f"{file_path.name:<20} {'.csv':<10} {actual_type:<15}")

        if actual_type == 'csv':
            actual_csv += 1
        elif actual_type == 'xlsx':
            actual_xlsx += 1
        else:
            unknown += 1

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Files with .csv extension that are actually:")
    print(f"  CSV:  {actual_csv}/{len(samples)} ({actual_csv/len(samples)*100:.1f}%)")
    print(f"  XLSX: {actual_xlsx}/{len(samples)} ({actual_xlsx/len(samples)*100:.1f}%)")
    print(f"  Unknown: {unknown}/{len(samples)}")
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    main()
