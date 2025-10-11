"""
Streamlit UI for Airtel Statement Fraud Detection
Following DRY principles - all core logic in process_statements.py
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import tempfile
import logging
import json
import hashlib

# Add the fraud_detection directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all core functions from process_statements
from process_statements import (
    extract_data_from_pdf,
    compute_balance_summary,
    detect_duplicate_transactions,
    get_pdf_metadata,
    calculate_running_balance
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration
from config import (
    UPLOADED_PDF_PATH,
    RESULTS_PATH,
    DETAILED_SHEETS_PATH,
    GOOGLE_CREDENTIALS_FILE
)


# UI-specific helper functions

def load_existing_results():
    """Load existing results from balance_summary.csv if it exists."""
    csv_path = os.path.join(RESULTS_PATH, 'balance_summary.csv')
    if os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"Error loading existing results: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def save_results(df):
    """Save results to balance_summary.csv."""
    csv_path = os.path.join(RESULTS_PATH, 'balance_summary.csv')
    df.to_csv(csv_path, index=False)
    logger.info(f"Results saved to {csv_path}")


def process_single_pdf(uploaded_file, check_metadata=True, check_balance=True, check_duplicates=True):
    """
    Process a single uploaded PDF file.

    Args:
        uploaded_file: Streamlit uploaded file object
        check_metadata: Whether to extract metadata
        check_balance: Whether to calculate balance summary
        check_duplicates: Whether to detect duplicates

    Returns:
        dict: Summary dictionary with all requested checks
    """
    # Save uploaded file temporarily
    temp_path = os.path.join(UPLOADED_PDF_PATH, uploaded_file.name)
    with open(temp_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    try:
        # Extract run_id from filename
        file_run_id = uploaded_file.name.replace('.pdf', '')

        # Extract data from PDF (this handles both Format 1 and Format 2)
        df, acc_number = extract_data_from_pdf(temp_path)

        if df.empty:
            return {
                'run_id': file_run_id,
                'account_number': acc_number,
                'file_name': uploaded_file.name,
                'error': 'No transactions found'
            }

        # Initialize summary
        summary = {
            'run_id': file_run_id,
            'rm_name': '',  # Will be filled by mapper if available
            'account_number': acc_number,
            'file_name': uploaded_file.name,
            'newly_processed': True
        }

        # Calculate running balance (single source of truth)
        # This also marks duplicates and calculates row-by-row balance
        df_with_balance = calculate_running_balance(df)

        # Count duplicates from the is_duplicate column
        if check_duplicates:
            duplicate_count = df_with_balance['is_duplicate'].sum()
            summary['duplicate_count'] = int(duplicate_count)
        else:
            summary['duplicate_count'] = 0

        # Compute balance summary from the running balance data
        if check_balance:
            # Filter out duplicates for summary calculation
            df_no_dupes = df_with_balance[~df_with_balance['is_duplicate']].copy()

            # Detect format based on whether amounts are signed
            amounts_are_signed = (df_no_dupes['amount'] < 0).any()

            # Calculate opening balance (already done in calculate_running_balance, but recalculate for summary)
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
            charges = 0

            # Get final calculated and statement balances
            calculated_closing_balance = df_no_dupes.iloc[-1]['calculated_running_balance']
            stmt_closing_balance = df_no_dupes.iloc[-1]['balance']

            # Verify balance
            balance_diff = abs(calculated_closing_balance - stmt_closing_balance)
            balance_match = "Success" if balance_diff < 0.01 else "Failed"

            summary.update({
                'balance_match': balance_match,
                'opening_balance': opening_balance,
                'credits': credits,
                'debits': debits,
                'fees': fees,
                'charges': charges,
                'calculated_closing_balance': calculated_closing_balance,
                'stmt_closing_balance': stmt_closing_balance
            })
        else:
            summary.update({
                'balance_match': 'N/A',
                'opening_balance': 0,
                'credits': 0,
                'debits': 0,
                'fees': 0,
                'charges': 0,
                'calculated_closing_balance': 0,
                'stmt_closing_balance': 0
            })

        # Save detailed running balance sheet
        detailed_csv_filename = file_run_id + '_detailed.csv'
        detailed_csv_path = os.path.join(DETAILED_SHEETS_PATH, detailed_csv_filename)
        df_with_balance.to_csv(detailed_csv_path, index=False)
        logger.info(f"Saved detailed sheet: {detailed_csv_filename}")

        # Calculate row count and MD5 hash of the detailed sheet
        row_count = len(df_with_balance)

        # Calculate MD5 hash of the CSV content
        with open(detailed_csv_path, 'rb') as f:
            csv_content = f.read()
            md5_hash = hashlib.md5(csv_content).hexdigest()

        # Get the total number of balance_diff changes
        balance_diff_changes = df_with_balance['balance_diff_change_count'].max() if 'balance_diff_change_count' in df_with_balance.columns else 0

        # Calculate balance_diff change ratio (changes / total rows)
        # Low ratio indicates possible Airtel-side issues
        balance_diff_change_ratio = balance_diff_changes / row_count if row_count > 0 else 0

        # Determine verification status based on balance match and change ratio
        verification_status = "OK"
        verification_reason = ""

        if check_balance:
            if balance_match == "Success":
                verification_status = "Verified"
                verification_reason = "Balance matches perfectly"
            elif balance_match == "Failed":
                # Check if balance_diff changes are few compared to total rows
                # Threshold: if changes < 2% of total rows, likely Airtel issue
                if balance_diff_change_ratio < 0.02:  # Less than 2%
                    verification_status = "Needs Additional Verification"
                    verification_reason = f"Balance mismatch with only {int(balance_diff_changes)} change(s) out of {row_count} rows. Possible Airtel-side issue (missing transactions/dates)."
                else:
                    verification_status = "Failed Verification"
                    verification_reason = f"Balance mismatch with {int(balance_diff_changes)} change(s). Requires detailed review."
        else:
            verification_status = "Not Checked"
            verification_reason = "Balance check not performed"

        # Add detailed CSV info to summary
        summary['detailed_csv'] = detailed_csv_filename
        summary['sheet_row_count'] = row_count
        summary['sheet_md5'] = md5_hash
        summary['balance_diff_changes'] = int(balance_diff_changes)
        summary['balance_diff_change_ratio'] = round(balance_diff_change_ratio, 4)
        summary['verification_status'] = verification_status
        summary['verification_reason'] = verification_reason

        # Extract metadata if requested
        if check_metadata:
            metadata = get_pdf_metadata(temp_path)
            summary.update(metadata)
        else:
            summary.update({
                'title': 'N/A',
                'author': 'N/A',
                'has_author': 'No',
                'creator': 'N/A',
                'producer': 'N/A',
                'created_at': 'N/A',
                'modified_at': 'N/A',
                'has_modified_at': 'No'
            })

        summary['error'] = ''
        return summary

    except Exception as e:
        logger.error(f"Error processing {uploaded_file.name}: {e}")
        return {
            'run_id': uploaded_file.name.replace('.pdf', ''),
            'rm_name': '',
            'account_number': '',
            'file_name': uploaded_file.name,
            'duplicate_count': 0,
            'balance_match': 'Failed',
            'opening_balance': 0,
            'credits': 0,
            'debits': 0,
            'fees': 0,
            'charges': 0,
            'calculated_closing_balance': 0,
            'stmt_closing_balance': 0,
            'title': 'N/A',
            'author': 'N/A',
            'has_author': 'No',
            'creator': 'N/A',
            'producer': 'N/A',
            'created_at': 'N/A',
            'modified_at': 'N/A',
            'has_modified_at': 'No',
            'error': str(e)
        }


def process_uploaded_pdfs(uploaded_files, existing_df, check_metadata=True, check_balance=True, check_duplicates=True):
    """Process uploaded PDF files and return summary with newly processed files marked."""
    summaries = []
    newly_processed_files = []
    skipped_files = []

    for uploaded_file in uploaded_files:
        file_run_id = uploaded_file.name.replace('.pdf', '')

        # Check if already processed with all requested checks
        should_skip = False
        if not existing_df.empty and 'run_id' in existing_df.columns:
            existing_record = existing_df[existing_df['run_id'] == file_run_id]
            if not existing_record.empty:
                record = existing_record.iloc[0]

                # Check if all requested checks are complete
                balance_done = not check_balance or record.get('balance_match', 'N/A') not in ['N/A', '', None]
                metadata_done = not check_metadata or record.get('title', 'N/A') not in ['N/A', '', None]
                duplicates_done = not check_duplicates or 'duplicate_count' in record

                if balance_done and metadata_done and duplicates_done:
                    should_skip = True

        if should_skip:
            skipped_files.append(uploaded_file.name)
            continue

        # Process the file
        summary = process_single_pdf(uploaded_file, check_metadata, check_balance, check_duplicates)
        summaries.append(summary)
        newly_processed_files.append(uploaded_file.name)

    # Create DataFrame from new summaries
    new_df = pd.DataFrame(summaries) if summaries else pd.DataFrame()

    # Mark newly processed files
    if not new_df.empty:
        new_df['newly_processed'] = True

    # Combine with existing results
    if not existing_df.empty and not new_df.empty:
        # Update existing records or add new ones
        existing_df['newly_processed'] = False
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        # Drop duplicates, keeping the latest (new) version
        combined_df = combined_df.drop_duplicates(subset=['run_id'], keep='last')
    elif not new_df.empty:
        combined_df = new_df
    elif not existing_df.empty:
        existing_df['newly_processed'] = False
        combined_df = existing_df
    else:
        combined_df = pd.DataFrame()

    # Save updated results
    if not combined_df.empty:
        save_df = combined_df.drop(columns=['newly_processed'], errors='ignore')
        save_results(save_df)

    return combined_df, newly_processed_files, skipped_files


def generate_running_balance_analysis(pdf_path_or_file):
    """
    Generate running balance analysis for a PDF file.
    Uses calculate_running_balance from process_statements.py (single source of truth)

    Args:
        pdf_path_or_file: Either a file path (str) or uploaded file object

    Returns:
        tuple: (output_df, final_calc, final_stmt, difference, selected_file)
    """
    # Handle both file path and uploaded file object
    if isinstance(pdf_path_or_file, str):
        temp_path = pdf_path_or_file
        selected_file = os.path.basename(pdf_path_or_file)
        cleanup_needed = False
    else:
        selected_file = pdf_path_or_file.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_path_or_file.read())
            temp_path = tmp_file.name
        cleanup_needed = True

    try:
        # Extract data (handles both formats and applies business rules)
        df, acc_number = extract_data_from_pdf(temp_path)

        # Calculate running balance using the shared function
        # This is the single source of truth for balance calculation
        output_df = calculate_running_balance(df)

        # Select columns for output
        output_df = output_df[[
            'txn_date', 'txn_id', 'description', 'status',
            'amount', 'txn_direction', 'fee', 'balance',
            'calculated_running_balance', 'balance_diff', 'balance_diff_change_count',
            'is_duplicate', 'is_special_txn', 'special_txn_type'
        ]].copy()

        # Calculate statistics from non-duplicate rows
        df_no_dupes = output_df[~output_df['is_duplicate']].copy()
        final_calc = df_no_dupes.iloc[-1]['calculated_running_balance']
        final_stmt = df_no_dupes.iloc[-1]['balance']
        difference = final_stmt - final_calc

        return output_df, final_calc, final_stmt, difference, selected_file

    finally:
        if cleanup_needed:
            os.unlink(temp_path)


def export_to_google_sheets(df, sheet_name, credentials_file=None):
    """
    Export a DataFrame to Google Sheets.

    Args:
        df: DataFrame to export
        sheet_name: Name for the Google Sheet
        credentials_file: Path to Google service account credentials JSON file

    Returns:
        tuple: (success: bool, message: str, sheet_url: str)
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Check if credentials file exists
        if credentials_file is None:
            credentials_file = GOOGLE_CREDENTIALS_FILE

        if not os.path.exists(credentials_file):
            return False, "Google credentials file not found. Please add 'google_credentials.json' to the fraud_detection folder.", None

        # Define the scope
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Authenticate using service account
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(creds)

        # Create a new spreadsheet
        spreadsheet = client.create(sheet_name)
        worksheet = spreadsheet.sheet1

        # Convert DataFrame to list of lists for gspread
        data = [df.columns.tolist()] + df.values.tolist()

        # Update the worksheet
        worksheet.update(data, value_input_option='RAW')

        # Format header row
        worksheet.format('A1:Z1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
        })

        # Get the spreadsheet URL
        sheet_url = spreadsheet.url

        return True, f"Successfully exported to Google Sheets!", sheet_url

    except ImportError:
        return False, "Required packages not installed. Please run: pip install gspread google-auth google-auth-oauthlib google-auth-httplib2", None
    except Exception as e:
        return False, f"Error exporting to Google Sheets: {str(e)}", None


# Streamlit UI
st.set_page_config(page_title="Airtel Statement Fraud Detection", layout="wide")

st.title("🔍 Airtel Statement Fraud Detection")
st.markdown("Upload Airtel statement PDFs to parse transactions and verify balances")

# Load existing results
existing_results = load_existing_results()

# Show existing results count
if not existing_results.empty:
    st.info(f"📊 {len(existing_results)} statement(s) in database")

# Checkboxes for selecting checks
st.subheader("⚙️ Select Checks to Perform")
col1, col2 = st.columns(2)
with col1:
    check_metadata = st.checkbox("📋 Metadata Extraction", value=True, help="Extract PDF metadata (author, created date, etc.)")
with col2:
    check_balance = st.checkbox("💰 Balance Summary & Duplicate Detection", value=True, help="Calculate balance summary and detect duplicate transactions")

# Duplicate detection is always done with balance summary
check_duplicates = check_balance

# File uploader
uploaded_files = st.file_uploader(
    "Upload PDF Statement(s)",
    type=['pdf'],
    accept_multiple_files=True,
    help="Upload one or more Airtel statement PDFs"
)

if uploaded_files:
    st.info(f"📄 {len(uploaded_files)} file(s) uploaded")

    # Process button
    if st.button("🚀 Process Statements", type="primary"):
        with st.spinner("Processing statements..."):
            result_df, newly_processed, skipped = process_uploaded_pdfs(
                uploaded_files,
                existing_results,
                check_metadata=check_metadata,
                check_balance=check_balance,
                check_duplicates=check_duplicates
            )

            if not result_df.empty:
                # Show processing summary
                if newly_processed:
                    st.success(f"✅ Processed {len(newly_processed)} new statement(s)")
                if skipped:
                    st.warning(f"⏭️ Skipped {len(skipped)} already processed statement(s): {', '.join(skipped)}")

                # Display summary statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Statements", len(result_df))
                with col2:
                    success_count = (result_df['balance_match'] == 'Success').sum()
                    st.metric("Balance Match Success", success_count)
                with col3:
                    failed_count = (result_df['balance_match'] == 'Failed').sum()
                    st.metric("Balance Match Failed", failed_count)
                with col4:
                    if 'duplicate_count' in result_df.columns:
                        total_dupes = result_df['duplicate_count'].sum()
                        st.metric("Total Duplicates", int(total_dupes))

                # Display results table
                st.subheader("📊 Processing Results")

                # Store newly_processed status before dropping
                newly_processed_status = result_df['newly_processed'].copy() if 'newly_processed' in result_df.columns else pd.Series([False] * len(result_df))

                # Reorder columns for better readability
                column_order = [
                    'run_id', 'rm_name', 'account_number', 'file_name',
                    'balance_match', 'verification_status', 'verification_reason',
                    'sheet_row_count', 'duplicate_count', 'balance_diff_changes', 'balance_diff_change_ratio',
                    'calculated_closing_balance', 'stmt_closing_balance',
                    'opening_balance', 'credits', 'debits', 'fees', 'charges',
                    'detailed_csv', 'sheet_md5',
                    'title', 'author', 'has_author', 'creator', 'producer',
                    'created_at', 'modified_at', 'has_modified_at',
                    'error'
                ]

                # Keep only columns that exist in result_df
                available_columns = [col for col in column_order if col in result_df.columns]
                display_df = result_df[available_columns].copy()

                # Format numeric columns
                numeric_cols = ['opening_balance', 'credits', 'debits', 'fees', 'charges',
                               'calculated_closing_balance', 'stmt_closing_balance']
                for col in numeric_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f'{int(x):,}' if pd.notna(x) else '0')

                # Apply styling
                def highlight_balance_match(val):
                    if val == 'Success':
                        return 'background-color: #d4edda; color: #155724; font-weight: bold'
                    elif val == 'Failed':
                        return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                    return ''

                def highlight_duplicate_count(val):
                    try:
                        count = int(val) if pd.notna(val) else 0
                        if count == 0:
                            return 'background-color: #d4edda; color: #155724; font-weight: bold'
                        else:
                            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                    except:
                        return ''

                def highlight_verification_status(val):
                    if val == 'Verified':
                        return 'background-color: #d4edda; color: #155724; font-weight: bold'
                    elif val == 'Needs Additional Verification':
                        return 'background-color: #fff3cd; color: #856404; font-weight: bold'
                    elif val == 'Failed Verification':
                        return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                    return ''

                styled_df = display_df.style.apply(
                    lambda row: ['background-color: #fff3cd' if newly_processed_status.loc[row.name] else '' for _ in row],
                    axis=1
                ).applymap(
                    highlight_balance_match,
                    subset=['balance_match']
                )

                if 'duplicate_count' in display_df.columns:
                    styled_df = styled_df.applymap(
                        highlight_duplicate_count,
                        subset=['duplicate_count']
                    )

                if 'verification_status' in display_df.columns:
                    styled_df = styled_df.applymap(
                        highlight_verification_status,
                        subset=['verification_status']
                    )

                st.dataframe(styled_df, use_container_width=True, height=400)

                st.markdown("**Legend:** 🟨 Yellow = Newly processed or Needs Additional Verification | 🟩 Green = Verified/Success | 🟥 Red = Failed")

                # Download buttons section
                st.subheader("📥 Download Options")

                col1, col2 = st.columns(2)

                with col1:
                    # Download summary CSV
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download Summary CSV",
                        data=csv,
                        file_name=f"balance_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        help="Download the balance summary",
                        use_container_width=True
                    )

                with col2:
                    # Download detailed sheets selector
                    if 'detailed_csv' in result_df.columns:
                        available_detailed = result_df[result_df['detailed_csv'].notna()]['file_name'].tolist()
                        if available_detailed:
                            st.markdown("**Select statement to download detailed sheet:**")
                            selected_file = st.selectbox(
                                "Choose file",
                                available_detailed,
                                key="detailed_download_selector",
                                label_visibility="collapsed"
                            )

                            if selected_file:
                                selected_record = result_df[result_df['file_name'] == selected_file].iloc[0]
                                detailed_csv_name = selected_record['detailed_csv']
                                detailed_csv_path = os.path.join(DETAILED_SHEETS_PATH, detailed_csv_name)

                                if os.path.exists(detailed_csv_path):
                                    with open(detailed_csv_path, 'r') as f:
                                        detailed_csv_data = f.read()

                                    st.download_button(
                                        label=f"📊 Download Detailed Sheet",
                                        data=detailed_csv_data,
                                        file_name=detailed_csv_name,
                                        mime="text/csv",
                                        help=f"Download detailed transaction sheet for {selected_file}",
                                        use_container_width=True,
                                        key="download_detailed_btn"
                                    )

                # Show errors if any
                if 'error' in result_df.columns:
                    errors = result_df[result_df['error'] != '']
                    if not errors.empty:
                        st.subheader("⚠️ Errors")
                        st.dataframe(errors[['file_name', 'error']], use_container_width=True)

            else:
                st.error("❌ No statements could be processed")

elif not existing_results.empty:
    # Display existing results even when no new files are uploaded
    st.subheader("📊 All Processed Statements")

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Statements", len(existing_results))
    with col2:
        success_count = (existing_results['balance_match'] == 'Success').sum()
        st.metric("Balance Match Success", success_count)
    with col3:
        failed_count = (existing_results['balance_match'] == 'Failed').sum()
        st.metric("Balance Match Failed", failed_count)

    # Reorder columns for better readability
    column_order = [
        'run_id', 'rm_name', 'account_number', 'file_name',
        'balance_match', 'verification_status', 'verification_reason',
        'sheet_row_count', 'duplicate_count', 'balance_diff_changes', 'balance_diff_change_ratio',
        'calculated_closing_balance', 'stmt_closing_balance',
        'opening_balance', 'credits', 'debits', 'fees', 'charges',
        'detailed_csv', 'sheet_md5',
        'title', 'author', 'has_author', 'creator', 'producer',
        'created_at', 'modified_at', 'has_modified_at',
        'error'
    ]

    # Keep only columns that exist in existing_results
    available_columns = [col for col in column_order if col in existing_results.columns]
    display_df = existing_results[available_columns].copy()

    # Format numeric columns
    numeric_cols = ['opening_balance', 'credits', 'debits', 'fees', 'charges',
                   'calculated_closing_balance', 'stmt_closing_balance']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f'{int(x):,}' if pd.notna(x) else '0')

    # Apply styling
    def highlight_balance_match(val):
        if val == 'Success':
            return 'background-color: #d4edda; color: #155724; font-weight: bold'
        elif val == 'Failed':
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        return ''

    def highlight_duplicate_count(val):
        try:
            count = int(val) if pd.notna(val) else 0
            if count == 0:
                return 'background-color: #d4edda; color: #155724; font-weight: bold'
            else:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        except:
            return ''

    def highlight_verification_status(val):
        if val == 'Verified':
            return 'background-color: #d4edda; color: #155724; font-weight: bold'
        elif val == 'Needs Additional Verification':
            return 'background-color: #fff3cd; color: #856404; font-weight: bold'
        elif val == 'Failed Verification':
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        return ''

    styled_df = display_df.style.applymap(
        highlight_balance_match,
        subset=['balance_match']
    )

    if 'duplicate_count' in display_df.columns:
        styled_df = styled_df.applymap(
            highlight_duplicate_count,
            subset=['duplicate_count']
        )

    if 'verification_status' in display_df.columns:
        styled_df = styled_df.applymap(
            highlight_verification_status,
            subset=['verification_status']
        )

    st.dataframe(styled_df, use_container_width=True, height=400)

    st.markdown("**Legend:** 🟨 Yellow = Needs Additional Verification | 🟩 Green = Verified/Success | 🟥 Red = Failed")

    # Download buttons section (always visible)
    st.divider()
    st.subheader("📥 Download Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Summary CSV**")
        # Check if summary CSV exists
        summary_csv_path = os.path.join(RESULTS_PATH, 'balance_summary.csv')
        if os.path.exists(summary_csv_path) and not existing_results.empty:
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📄 Download Summary CSV",
                data=csv,
                file_name=f"balance_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download the balance summary",
                use_container_width=True,
                key="existing_summary_download"
            )
        else:
            st.info("No summary available yet. Process statements to generate summary.")

    with col2:
        st.markdown("**Detailed Transaction Sheets**")
        # Get all available detailed sheets from the folder
        available_detailed_files = []
        if os.path.exists(DETAILED_SHEETS_PATH):
            available_detailed_files = [f for f in os.listdir(DETAILED_SHEETS_PATH) if f.endswith('_detailed.csv')]

        if available_detailed_files:
            # Create a mapping of filename to display name
            file_display_mapping = {}
            for detailed_file in available_detailed_files:
                # Extract run_id from filename (remove _detailed.csv)
                run_id = detailed_file.replace('_detailed.csv', '')
                # Try to find corresponding statement in results
                if not existing_results.empty and 'run_id' in existing_results.columns:
                    matching = existing_results[existing_results['run_id'] == run_id]
                    if not matching.empty:
                        display_name = matching.iloc[0]['file_name']
                    else:
                        display_name = f"{run_id}.pdf"
                else:
                    display_name = f"{run_id}.pdf"
                file_display_mapping[display_name] = detailed_file

            selected_display_name = st.selectbox(
                "Choose file",
                list(file_display_mapping.keys()),
                key="detailed_download_selector_existing",
                label_visibility="collapsed"
            )

            if selected_display_name:
                detailed_csv_name = file_display_mapping[selected_display_name]
                detailed_csv_path = os.path.join(DETAILED_SHEETS_PATH, detailed_csv_name)

                if os.path.exists(detailed_csv_path):
                    with open(detailed_csv_path, 'r') as f:
                        detailed_csv_data = f.read()

                    st.download_button(
                        label=f"📊 Download Detailed Sheet",
                        data=detailed_csv_data,
                        file_name=detailed_csv_name,
                        mime="text/csv",
                        help=f"Download detailed transaction sheet for {selected_display_name}",
                        use_container_width=True,
                        key="download_detailed_btn_existing"
                    )
        else:
            st.info("No detailed sheets available yet. Process statements to generate detailed sheets.")

    # Clear All Database Section
    st.divider()
    st.subheader("🗑️ Clear All Database")
    st.caption("Remove all processed statements from the database")

    if 'confirm_clear' not in st.session_state:
        st.session_state.confirm_clear = False

    if st.session_state.confirm_clear:
        st.warning("⚠️ This will permanently delete ALL records!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete All", key="confirm_yes", type="primary", use_container_width=True):
                try:
                    csv_path = os.path.join(RESULTS_PATH, 'balance_summary.csv')
                    empty_df = pd.DataFrame(columns=[
                        'run_id', 'rm_name', 'account_number', 'file_name',
                        'balance_match', 'verification_status', 'verification_reason',
                        'sheet_row_count', 'duplicate_count', 'balance_diff_changes', 'balance_diff_change_ratio',
                        'calculated_closing_balance', 'stmt_closing_balance',
                        'opening_balance', 'credits', 'debits', 'fees', 'charges',
                        'detailed_csv', 'sheet_md5',
                        'title', 'author', 'has_author', 'creator', 'producer',
                        'created_at', 'modified_at', 'has_modified_at',
                        'error'
                    ])
                    empty_df.to_csv(csv_path, index=False)
                    st.session_state.confirm_clear = False
                    st.success("✅ Database cleared successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error clearing database: {e}")
                    st.session_state.confirm_clear = False
        with col2:
            if st.button("❌ Cancel", key="confirm_no", type="secondary", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()
    else:
        if st.button("🗑️ Clear All Database", type="secondary"):
            st.session_state.confirm_clear = True
            st.rerun()

else:
    st.info("👆 Please upload PDF statement(s) to begin")

# Sidebar with instructions
with st.sidebar:
    st.header("📖 Instructions")
    st.markdown("""
    1. **Upload PDFs**: Click the upload button and select one or multiple Airtel statement PDFs
    2. **Select Checks**: Choose which checks to perform (metadata, balance, duplicates)
    3. **Process**: Click the "Process Statements" button
    4. **Review**: Check the summary table for balance verification results
    5. **Download**: Download the results as CSV for further analysis

    ### Supported Formats
    - **Format 1**: AIRTEL MONEY STATEMENT (with Credit/Debit column)
    - **Format 2**: USER STATEMENT (with signed amounts)

    ### Balance Verification
    - **Success**: Calculated balance matches statement
    - **Failed**: Balance mismatch detected

    Both formats are automatically detected and processed correctly.
    """)
