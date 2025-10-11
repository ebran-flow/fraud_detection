#!/usr/bin/env python3
"""
Batch process all statements from mapper.csv for a specific month.
"""
import os
import sys
import pandas as pd
from datetime import datetime
import logging
import hashlib

# Add the fraud_detection directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_statements import (
    extract_data_from_pdf,
    calculate_running_balance,
    get_pdf_metadata
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_process.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import configuration
from config import (
    MAPPER_CSV,
    STATEMENTS_ARCHIVE_DIR as STATEMENTS_DIR,
    RESULTS_PATH,
    DETAILED_SHEETS_PATH,
    BATCH_RESULTS_PATH
)


def process_statement(run_id, rm_name, acc_number):
    """
    Process a single statement and return summary.
    Saves detailed sheets to detailed_sheets folder (same as UI).

    Returns:
        dict: Summary with verification status
    """
    summary = {
        'run_id': run_id,
        'rm_name': rm_name,
        'account_number': acc_number,
        'file_name': f"{run_id}.pdf",
        'verification_status': '',
        'verification_reason': '',
        'balance_match': '',
        'sheet_row_count': 0,
        'duplicate_count': 0,
        'balance_diff_changes': 0,
        'balance_diff_change_ratio': 0.0,
        'calculated_closing_balance': 0,
        'stmt_closing_balance': 0,
        'opening_balance': 0,
        'credits': 0,
        'debits': 0,
        'fees': 0,
        'charges': 0,
        'detailed_csv': '',
        'sheet_md5': '',
        'title': '',
        'author': '',
        'has_author': '',
        'creator': '',
        'producer': '',
        'created_at': '',
        'modified_at': '',
        'has_modified_at': '',
        'error': ''
    }

    # Check if PDF exists
    pdf_path = os.path.join(STATEMENTS_DIR, f"{run_id}.pdf")
    if not os.path.exists(pdf_path):
        summary['verification_status'] = "Statement Not Found"
        summary['verification_reason'] = f"PDF file not found in {STATEMENTS_DIR}"
        logger.warning(f"Statement not found: {run_id}.pdf")
        return summary

    try:
        # Get PDF metadata
        metadata = get_pdf_metadata(pdf_path)
        summary.update({
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'has_author': metadata.get('has_author', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'created_at': metadata.get('created_at', ''),
            'modified_at': metadata.get('modified_at', ''),
            'has_modified_at': metadata.get('has_modified_at', '')
        })

        # Extract data from PDF
        df, acc_num = extract_data_from_pdf(pdf_path)

        if df.empty:
            summary['verification_status'] = "Statement Read Failed"
            summary['verification_reason'] = "No transactions found in PDF"
            summary['error'] = "No transactions extracted"
            logger.error(f"No transactions found in {run_id}.pdf")
            return summary

        # Calculate running balance
        df_with_balance = calculate_running_balance(df)

        # Save detailed sheet (same as UI)
        detailed_csv_path = os.path.join(DETAILED_SHEETS_PATH, f"{run_id}_detailed.csv")
        df_with_balance.to_csv(detailed_csv_path, index=False)

        # Calculate row count and MD5 hash
        row_count = len(df_with_balance)
        with open(detailed_csv_path, 'rb') as f:
            csv_content = f.read()
            md5_hash = hashlib.md5(csv_content).hexdigest()

        summary['detailed_csv'] = f"{run_id}_detailed.csv"
        summary['sheet_md5'] = md5_hash

        # Count duplicates
        duplicate_count = df_with_balance['is_duplicate'].sum()
        summary['duplicate_count'] = int(duplicate_count)
        summary['sheet_row_count'] = row_count

        # Filter out duplicates for balance calculation
        df_no_dupes = df_with_balance[~df_with_balance['is_duplicate']].copy()

        # Detect format
        amounts_are_signed = (df_no_dupes['amount'] < 0).any()

        # Calculate opening balance
        first_balance = df_no_dupes.iloc[0]['balance']
        first_amount = df_no_dupes.iloc[0]['amount']
        first_fee = df_no_dupes.iloc[0]['fee']

        if amounts_are_signed:
            # Format 2
            opening_balance = first_balance - first_amount
            credits = df_no_dupes[df_no_dupes['amount'] > 0]['amount'].sum()
            debits = abs(df_no_dupes[df_no_dupes['amount'] < 0]['amount'].sum())
        else:
            # Format 1
            first_direction = df_no_dupes.iloc[0]['txn_direction'].lower()
            if first_direction == 'credit':
                opening_balance = first_balance - first_amount - first_fee
            else:
                opening_balance = first_balance + first_amount + first_fee
            credits = df_no_dupes[df_no_dupes['txn_direction'].str.lower() == 'credit']['amount'].sum()
            debits = df_no_dupes[df_no_dupes['txn_direction'].str.lower() == 'debit']['amount'].sum()

        fees = df_no_dupes['fee'].sum()
        charges = 0  # Charges column for consistency with UI

        # Get final balances
        calculated_closing_balance = df_no_dupes.iloc[-1]['calculated_running_balance']
        stmt_closing_balance = df_no_dupes.iloc[-1]['balance']

        # Verify balance
        balance_diff = abs(calculated_closing_balance - stmt_closing_balance)
        balance_match = "Success" if balance_diff < 0.01 else "Failed"

        # Get balance_diff changes
        balance_diff_changes = df_with_balance['balance_diff_change_count'].max()
        balance_diff_change_ratio = balance_diff_changes / row_count if row_count > 0 else 0

        # Determine verification status
        if balance_match == "Success":
            verification_status = "Verified"
            verification_reason = "Balance matches perfectly"
        elif balance_match == "Failed":
            if balance_diff_change_ratio < 0.02:  # Less than 2%
                verification_status = "Needs Additional Verification"
                verification_reason = f"Balance mismatch with only {int(balance_diff_changes)} change(s) out of {row_count} rows. Possible Airtel-side issue."
            else:
                verification_status = "Failed Verification"
                verification_reason = f"Balance mismatch with {int(balance_diff_changes)} change(s). Requires detailed review."

        # Update summary
        summary.update({
            'verification_status': verification_status,
            'verification_reason': verification_reason,
            'balance_match': balance_match,
            'opening_balance': opening_balance,
            'credits': credits,
            'debits': debits,
            'fees': fees,
            'charges': charges,
            'calculated_closing_balance': calculated_closing_balance,
            'stmt_closing_balance': stmt_closing_balance,
            'balance_diff_changes': int(balance_diff_changes),
            'balance_diff_change_ratio': round(balance_diff_change_ratio, 4)
        })

        logger.info(f"✅ Processed {run_id}.pdf - Status: {verification_status}")
        return summary

    except Exception as e:
        summary['verification_status'] = "Statement Read Failed"
        summary['verification_reason'] = f"Error processing PDF: {str(e)}"
        summary['error'] = str(e)
        logger.error(f"❌ Error processing {run_id}.pdf: {e}")
        return summary


def main(year_month="202509"):
    """
    Main function to process all statements for a given month.
    Updates balance_summary.csv after each statement is processed (same as UI).

    Args:
        year_month: YYYYMM format (e.g., "202509" for September 2025)
    """
    logger.info(f"Starting batch processing for {year_month}")

    # Path to balance summary CSV (same as UI)
    summary_csv_path = os.path.join(RESULTS_PATH, 'balance_summary.csv')

    # Load existing summary if it exists
    if os.path.exists(summary_csv_path):
        existing_summary = pd.read_csv(summary_csv_path)
        logger.info(f"Loaded existing balance_summary.csv with {len(existing_summary)} records")
    else:
        existing_summary = pd.DataFrame()
        logger.info("No existing balance_summary.csv found, will create new one")

    # Read mapper.csv
    try:
        mapper_df = pd.read_csv(MAPPER_CSV)
        logger.info(f"Loaded {len(mapper_df)} records from mapper.csv")
    except Exception as e:
        logger.error(f"Failed to read mapper.csv: {e}")
        return

    # Filter for Airtel (UATL) only
    mapper_df = mapper_df[mapper_df['acc_prvdr_code'] == 'UATL'].copy()
    logger.info(f"Filtered to {len(mapper_df)} Airtel (UATL) records")

    # Filter for the specified month
    mapper_df['created_date'] = pd.to_datetime(mapper_df['created_date'])
    mapper_df['year_month'] = mapper_df['created_date'].dt.strftime('%Y%m')

    filtered_df = mapper_df[mapper_df['year_month'] == year_month].copy()
    logger.info(f"Found {len(filtered_df)} Airtel statements for {year_month}")

    if filtered_df.empty:
        logger.warning(f"No statements found for {year_month}")
        return

    # Skip already processed statements
    if not existing_summary.empty:
        processed_run_ids = existing_summary['run_id'].tolist()
        before_skip = len(filtered_df)
        filtered_df = filtered_df[~filtered_df['run_id'].isin(processed_run_ids)]
        skipped = before_skip - len(filtered_df)
        logger.info(f"Skipping {skipped} already processed statements")
        logger.info(f"Remaining to process: {len(filtered_df)}")

    if filtered_df.empty:
        logger.info(f"All statements for {year_month} have already been processed")
        return

    # Process each statement and update balance_summary.csv after each one
    batch_results = []
    total = len(filtered_df)
    processed_count = 0

    for idx, row in filtered_df.iterrows():
        run_id = row['run_id']
        rm_name = row.get('rm_name', '')
        acc_number = row.get('acc_number', '')

        logger.info(f"Processing {processed_count + 1}/{total}: {run_id}")

        # Process the statement
        summary = process_statement(run_id, rm_name, acc_number)
        batch_results.append(summary)

        # Update balance_summary.csv after each statement (same as UI)
        if not existing_summary.empty and run_id in existing_summary['run_id'].values:
            # Update existing record
            existing_summary.loc[existing_summary['run_id'] == run_id] = pd.Series(summary)
        else:
            # Append new record
            existing_summary = pd.concat([existing_summary, pd.DataFrame([summary])], ignore_index=True)

        # Save updated summary
        existing_summary.to_csv(summary_csv_path, index=False)

        processed_count += 1

    logger.info(f"All statements processed and saved to {summary_csv_path}")

    # Also save batch-specific results for reference
    batch_results_df = pd.DataFrame(batch_results)
    batch_output_file = os.path.join(BATCH_RESULTS_PATH, f"batch_results_{year_month}.csv")
    batch_results_df.to_csv(batch_output_file, index=False)
    logger.info(f"Batch-specific results saved to {batch_output_file}")

    # Print summary statistics
    print("\n" + "="*80)
    print(f"BATCH PROCESSING SUMMARY - {year_month}")
    print("="*80)
    print(f"Total statements processed: {len(batch_results_df)}")
    print(f"Verified: {(batch_results_df['verification_status'] == 'Verified').sum()}")
    print(f"Needs Additional Verification: {(batch_results_df['verification_status'] == 'Needs Additional Verification').sum()}")
    print(f"Failed Verification: {(batch_results_df['verification_status'] == 'Failed Verification').sum()}")
    print(f"Statement Not Found: {(batch_results_df['verification_status'] == 'Statement Not Found').sum()}")
    print(f"Statement Read Failed: {(batch_results_df['verification_status'] == 'Statement Read Failed').sum()}")
    print("="*80)
    print(f"\nBalance summary: {summary_csv_path}")
    print(f"Batch results: {batch_output_file}")
    print(f"Detailed sheets: {DETAILED_SHEETS_PATH}")
    print(f"Log file: batch_process.log")


if __name__ == "__main__":
    # Default to September 2025
    year_month = sys.argv[1] if len(sys.argv) > 1 else "202509"
    main(year_month)
