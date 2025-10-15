#!/usr/bin/env python3
"""
Convert additional_metrics_results.json to CSV format for manual review
"""
import json
import csv
from datetime import datetime

# Load JSON results
with open('additional_metrics_results.json', 'r') as f:
    data = json.load(f)

# Create CSV with detailed results
output_file = 'additional_metrics_results.csv'

with open(output_file, 'w', newline='') as csvfile:
    fieldnames = [
        'run_id',
        'acc_number',
        'balance_match',
        'balance_diff_change_ratio',
        'transaction_count',
        # Transaction ID integrity
        'has_txn_id_gaps',
        'txn_id_gap_count',
        'has_duplicate_txn_ids',
        'duplicate_txn_id_count',
        'has_pattern_breaks',
        # Balance jumps
        'balance_jump_count',
        'max_balance_jump_ratio',
        # Timestamp anomalies
        'same_second_groups',
        'non_chronological_count',
        'business_hours_ratio',
        'weekend_ratio',
        # Amount patterns
        'round_number_ratio',
        'duplicate_amount_ratio',
        'benford_score',
        # PDF metadata
        'pdf_creation_date',
        'pdf_producer',
        'pdf_creator',
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for result in data['results']:
        row = {
            'run_id': result['run_id'],
            'acc_number': result.get('acc_number', ''),
            'balance_match': result.get('balance_match', ''),
            'balance_diff_change_ratio': result.get('balance_diff_change_ratio', 0),
            'transaction_count': result['transaction_count'],

            # Transaction ID integrity
            'has_txn_id_gaps': result['transaction_id_integrity']['has_gaps'],
            'txn_id_gap_count': result['transaction_id_integrity']['gap_count'],
            'has_duplicate_txn_ids': result['transaction_id_integrity']['has_duplicates'],
            'duplicate_txn_id_count': result['transaction_id_integrity']['duplicate_count'],
            'has_pattern_breaks': result['transaction_id_integrity']['has_pattern_breaks'],

            # Balance jumps
            'balance_jump_count': result['balance_jumps']['balance_jump_count'],
            'max_balance_jump_ratio': result['balance_jumps']['max_jump_ratio'],

            # Timestamp anomalies
            'same_second_groups': result['timestamp_anomalies']['same_second_groups'],
            'non_chronological_count': result['timestamp_anomalies']['non_chronological_count'],
            'business_hours_ratio': result['timestamp_anomalies']['business_hours_ratio'],
            'weekend_ratio': result['timestamp_anomalies']['weekend_ratio'],

            # Amount patterns
            'round_number_ratio': result['amount_patterns']['round_number_ratio'],
            'duplicate_amount_ratio': result['amount_patterns']['duplicate_amount_ratio'],
            'benford_score': result['amount_patterns']['benford_score'],

            # PDF metadata
            'pdf_creation_date': result['pdf_metadata'].get('creation_date', ''),
            'pdf_producer': result['pdf_metadata'].get('producer', ''),
            'pdf_creator': result['pdf_metadata'].get('creator', ''),
        }
        writer.writerow(row)

print(f"✅ Converted {len(data['results'])} results to CSV")
print(f"Output: {output_file}")
print()
print("Summary:")
print(f"  Total scanned: {data['total_scanned']}")
print(f"  Duration: {data['duration_seconds']:.1f} seconds")
print()
print("You can now review the CSV file in Excel or any spreadsheet application")
