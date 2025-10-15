#!/usr/bin/env python3
"""
Convert header_manipulation_results.json to CSV format for manual review
"""
import json
import csv
from datetime import datetime

# Load JSON results
with open('header_manipulation_results.json', 'r') as f:
    data = json.load(f)

# Create CSV with detailed results
output_file = 'header_manipulation_results.csv'

with open(output_file, 'w', newline='') as csvfile:
    fieldnames = [
        'run_id',
        'acc_number',
        'balance_match',
        'balance_diff_change_ratio',
        'is_manipulated',
        'manipulated_pages_count',
        'total_pages',
        'bad_pages_summary',
        'pdf_path',
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for result in data['results']:
        # Create summary of bad pages
        bad_pages_summary = []
        for page_num, reason in result['bad_pages'].items():
            bad_pages_summary.append(f"P{page_num}:{reason}")

        row = {
            'run_id': result['run_id'],
            'acc_number': result['acc_number'],
            'balance_match': result['balance_match'],
            'balance_diff_change_ratio': result['balance_diff_change_ratio'],
            'is_manipulated': 'YES' if result['is_manipulated'] else 'NO',
            'manipulated_pages_count': result['manipulated_pages_count'],
            'total_pages': result['total_pages'],
            'bad_pages_summary': '; '.join(bad_pages_summary) if bad_pages_summary else '',
            'pdf_path': result['pdf_path'],
        }
        writer.writerow(row)

print(f"✅ Converted {len(data['results'])} results to CSV")
print(f"Output: {output_file}")
print()
print("Summary:")
print(f"  Total scanned: {data['total_scanned']}")
print(f"  Manipulated: {data['manipulated_statements']}")
print(f"  Clean: {data['clean_statements']}")
print(f"  File not found: {data['file_not_found']}")
print()
print("You can now review the CSV file in Excel or any spreadsheet application")
