"""
Processor Service
Handles processing logic: duplicate detection, balance verification, fraud checks
Reads from raw_statements and creates processed_statements and summary records
Supports multi-provider with factory pattern
"""
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
import pandas as pd

from ..models.metadata import Metadata
from ..models.summary import Summary
from . import crud_v2 as crud
from .provider_factory import ProviderFactory
from .balance_utils import (
    is_amount_signed,
    calculate_opening_balance,
    apply_transaction_to_balance,
    calculate_total_credits_debits
)

logger = logging.getLogger(__name__)


def process_statement(db: Session, run_id: str) -> Dict[str, Any]:
    """
    Process a statement: detect duplicates, verify balances, create processed records
    Supports multi-provider using factory pattern

    Args:
        db: Database session
        run_id: Statement run_id to process

    Returns:
        Processing result summary
    """
    logger.info(f"Processing statement: {run_id}")

    try:
        # Load metadata first to get provider_code
        metadata = crud.get_metadata_by_run_id(db, run_id)
        if not metadata:
            raise ValueError(f"No metadata found for run_id: {run_id}")

        provider_code = metadata.acc_prvdr_code
        logger.info(f"Processing {provider_code} statement: {run_id}")

        # Load raw statements using provider-specific model
        raw_statements = crud.get_raw_statements_by_run_id(db, run_id, provider_code)
        if not raw_statements:
            raise ValueError(f"No raw statements found for run_id: {run_id}")

        # Convert to DataFrame for processing
        df = pd.DataFrame([stmt.__dict__ for stmt in raw_statements])

        # Update metadata with start_date and end_date from transaction dates
        if len(df) > 0 and 'txn_date' in df.columns:
            # Filter out None/NaT values
            valid_dates = df['txn_date'].dropna()
            if len(valid_dates) > 0:
                metadata.start_date = valid_dates.min().date() if hasattr(valid_dates.min(), 'date') else valid_dates.min()
                metadata.end_date = valid_dates.max().date() if hasattr(valid_dates.max(), 'date') else valid_dates.max()
                logger.info(f"Updated metadata dates for {run_id}: start={metadata.start_date}, end={metadata.end_date}")

        # Get balance field for provider
        balance_field = ProviderFactory.get_balance_field(provider_code)

        # Detect duplicates
        df = detect_duplicates(df)

        # Detect special transactions
        df = detect_special_transactions(df)

        # Calculate running balance and differences
        df = calculate_running_balance(df, metadata.pdf_format, provider_code, balance_field)

        # Create processed statements
        processed_statements = []
        for idx, row in df.iterrows():
            processed_stmt = {
                'raw_id': row['id'],
                'run_id': run_id,
                'acc_number': row['acc_number'],
                'txn_id': row['txn_id'],
                'txn_date': row['txn_date'],
                'txn_type': row.get('txn_type'),
                'description': row['description'],
                'status': row['status'],
                'amount': float(row['amount']) if row['amount'] is not None else None,
                'fee': float(row['fee']) if row['fee'] is not None else 0.0,
                'is_duplicate': bool(row.get('is_duplicate', False)),
                'is_special_txn': bool(row.get('is_special_txn', False)),
                'special_txn_type': row.get('special_txn_type'),
                'calculated_running_balance': float(row['calculated_running_balance']) if pd.notna(row.get('calculated_running_balance')) else None,
                'balance_diff': float(row['balance_diff']) if pd.notna(row.get('balance_diff')) else None,
                'balance_diff_change_count': int(row.get('balance_diff_change_count', 0)),
            }

            # Add balance field (provider-specific)
            if balance_field in row and pd.notna(row[balance_field]):
                processed_stmt['balance'] = float(row[balance_field])
            else:
                processed_stmt['balance'] = None

            processed_statements.append(processed_stmt)

        # Bulk insert processed statements (provider-specific table)
        crud.bulk_create_processed(db, provider_code, processed_statements)

        # Generate summary
        summary_data = generate_summary(df, metadata, run_id, provider_code, balance_field)

        # Update metadata with actual first and last balance from processed data
        if len(df) > 0:
            metadata.last_balance = float(df.iloc[-1][balance_field])
            metadata.first_balance = float(df.iloc[0][balance_field])

        # Check if summary exists, update or create
        existing_summary = crud.get_summary_by_run_id(db, run_id)
        if existing_summary:
            # Update existing
            for key, value in summary_data.items():
                setattr(existing_summary, key, value)
        else:
            # Create new
            crud.create(db, Summary, summary_data)

        db.commit()

        result = {
            'run_id': run_id,
            'provider_code': provider_code,
            'status': 'success',
            'processed_count': len(processed_statements),
            'duplicate_count': int(df['is_duplicate'].sum()),
            'balance_match': summary_data['balance_match'],
            'verification_status': summary_data['verification_status'],
        }

        logger.info(f"Processing complete for {run_id} ({provider_code}): {result}")
        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing statement {run_id}: {e}")
        raise


def detect_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect duplicate transactions based on:
    - Same transaction ID (txn_id)
    - Same transaction date
    - Same amount
    - Same description

    Note: If txn_id is different, transactions are considered separate even if other fields match
    """
    df['is_duplicate'] = False

    # Mark duplicates based on txn_id AND other fields
    # This ensures transactions with different IDs are not marked as duplicates
    duplicate_mask = df.duplicated(subset=['txn_id', 'txn_date', 'amount', 'description'], keep='first')
    df.loc[duplicate_mask, 'is_duplicate'] = True

    duplicate_count = duplicate_mask.sum()
    if duplicate_count > 0:
        logger.info(f"Detected {duplicate_count} duplicate transactions")

    return df


def detect_special_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect special transactions:
    - Commission Disbursement
    - Deallocation Transfer
    - Transaction Reversal
    - Rollback
    """
    df['is_special_txn'] = False
    df['special_txn_type'] = None

    # Commission Disbursement (exact pattern only, not "Received From ... Commissions Disbursement Wallet")
    # Pattern: "Commission Disbursement -" (starts with this exact phrase)
    commission_mask = df['description'].str.match(r'^Commission Disbursement\s*', case=False, na=False)
    df.loc[commission_mask, 'is_special_txn'] = True
    df.loc[commission_mask, 'special_txn_type'] = 'Commission Disbursement'

    # Deallocation Transfer
    dealloc_mask = df['description'].str.contains('Deallocation', case=False, na=False)
    df.loc[dealloc_mask, 'is_special_txn'] = True
    df.loc[dealloc_mask, 'special_txn_type'] = 'Deallocation Transfer'

    # Rollback
    rollback_mask = df['description'].str.contains('Rollback', case=False, na=False)
    df.loc[rollback_mask, 'is_special_txn'] = True
    df.loc[rollback_mask, 'special_txn_type'] = 'Rollback'

    special_count = df['is_special_txn'].sum()
    if special_count > 0:
        logger.info(f"Detected {special_count} special transactions")

    return df


def optimize_same_timestamp_transactions(df: pd.DataFrame, pdf_format: int, balance_field: str) -> pd.DataFrame:
    """
    For same-timestamp transactions in Format 1, find the correct order by testing permutations
    """
    from itertools import permutations

    # Sort by timestamp and balance descending as initial ordering
    df = df.sort_values(['txn_date', balance_field], ascending=[True, False]).reset_index(drop=True)

    # Detect if amounts are signed (CSV) or unsigned (PDF)
    amounts_are_signed = is_amount_signed(df, pdf_format, 'UATL')

    # Group by timestamp and optimize each group
    optimized_groups = []
    prev_running_balance = 0

    for txn_date, group in df.groupby('txn_date', sort=False):
        # If only one transaction at this timestamp, no need to optimize
        if len(group) == 1:
            optimized_groups.append(group)
            continue

        # Get the previous running balance
        if len(optimized_groups) == 0:
            # For first group, use descending balance order
            optimized_group = group.sort_values(balance_field, ascending=False).reset_index(drop=True)
        else:
            # For groups > 6, use descending balance order (too many permutations)
            if len(group) > 6:
                optimized_group = group.sort_values(balance_field, ascending=False).reset_index(drop=True)
            else:
                # Try all permutations to find the best order
                prev_running_balance = optimized_groups[-1].iloc[-1][balance_field]
                best_order = None
                best_score = -1

                indices = list(range(len(group)))
                for perm in permutations(indices):
                    test_df = group.iloc[list(perm)].reset_index(drop=True)
                    score = 0
                    running_bal = prev_running_balance

                    for i in range(len(test_df)):
                        row = test_df.iloc[i]

                        # Apply transaction to get expected balance
                        expected_bal = apply_transaction_to_balance(
                            running_bal,
                            row['amount'],
                            row['fee'],
                            str(row.get('txn_direction', '')),
                            amounts_are_signed,
                            pdf_format,
                            str(row.get('description', ''))
                        )

                        # Check if it matches the row's statement balance
                        if abs(expected_bal - float(row[balance_field])) < 0.01:
                            score += 1

                        # Update running balance to this row's statement balance
                        running_bal = float(row[balance_field])

                    if score > best_score:
                        best_score = score
                        best_order = test_df

                optimized_group = best_order if best_order is not None else group

        optimized_groups.append(optimized_group)

    # Recombine all groups
    return pd.concat(optimized_groups, ignore_index=True)


def calculate_running_balance(df: pd.DataFrame, pdf_format: int, provider_code: str, balance_field: str) -> pd.DataFrame:
    """
    Calculate running balance and compare with statement balance
    Track balance differences and change counts
    Supports different balance fields per provider (UATL: 'balance', UMTN: 'float_balance')
    """
    # For Format 1, optimize same-timestamp transaction ordering
    if pdf_format == 1:
        df = optimize_same_timestamp_transactions(df, pdf_format, balance_field)

    df['calculated_running_balance'] = None
    df['balance_diff'] = None
    df['balance_diff_change_count'] = 0

    if df.empty:
        return df

    # Determine if amounts are signed or unsigned
    amounts_signed = is_amount_signed(df, pdf_format, provider_code)

    # Calculate opening balance from first transaction
    first_row = df.iloc[0]
    first_balance = first_row[balance_field]
    first_amount = first_row['amount']
    first_fee = first_row['fee']
    first_direction = str(first_row.get('txn_direction', ''))
    first_description = str(first_row.get('description', ''))

    opening_balance = calculate_opening_balance(
        first_balance, first_amount, first_fee, first_direction, amounts_signed, pdf_format, first_description
    )

    # Calculate running balance for each transaction
    running_balance = opening_balance
    prev_diff = None
    change_count = 0

    for idx in range(len(df)):
        row = df.iloc[idx]

        # Handle Commission Disbursement specially (moves money between Regular Biz and Commission wallets)
        if row.get('is_special_txn', False) and row.get('special_txn_type') == 'Commission Disbursement':
            # For Commission Disbursement: invert the amount (debit = add, credit = subtract)
            # This maintains the running balance for the Regular Biz wallet
            inverted_amount = -float(row['amount'])  # Invert: if debited, add; if credited, subtract
            running_balance = running_balance + inverted_amount
            logger.debug(f"Commission Disbursement: inverted amount {row['amount']} → {inverted_amount}, running balance = {running_balance}")

            # The balance shown is for Commission wallet, so copy balance_diff from previous row
            balance_diff = prev_diff if prev_diff is not None else 0.0
            df.at[df.index[idx], 'calculated_running_balance'] = running_balance
            df.at[df.index[idx], 'balance_diff'] = balance_diff

        # For other special transactions (Deallocation, Reversal, Rollback),
        # copy both calculated_running_balance and balance_diff from previous row
        elif row.get('is_special_txn', False):
            # Don't update running_balance - keep it the same
            # Copy balance_diff from previous row as well
            logger.debug(f"Skipping balance calculation for special transaction: {row.get('special_txn_type')}")
            df.at[df.index[idx], 'calculated_running_balance'] = running_balance
            balance_diff = prev_diff if prev_diff is not None else 0.0
            df.at[df.index[idx], 'balance_diff'] = balance_diff

        else:
            # Apply transaction to running balance for normal transactions
            running_balance = apply_transaction_to_balance(
                running_balance,
                row['amount'],
                row['fee'],
                str(row.get('txn_direction', '')),
                amounts_signed,
                pdf_format,
                str(row.get('description', ''))
            )

            df.at[df.index[idx], 'calculated_running_balance'] = running_balance

            # Calculate difference from statement balance
            stmt_balance = float(row[balance_field])
            balance_diff = running_balance - stmt_balance
            df.at[df.index[idx], 'balance_diff'] = balance_diff

        # Track balance difference changes
        if prev_diff is not None and abs(balance_diff - prev_diff) > 0.01:
            change_count += 1

        df.at[df.index[idx], 'balance_diff_change_count'] = change_count
        prev_diff = balance_diff

    return df


def generate_summary(df: pd.DataFrame, metadata: Metadata, run_id: str, provider_code: str, balance_field: str) -> Dict[str, Any]:
    """
    Generate summary record from processed data
    Supports different balance fields per provider
    """
    # Calculate totals using centralized utility
    credits, debits = calculate_total_credits_debits(df, metadata.pdf_format, provider_code)
    fees = float(df['fee'].sum())
    charges = 0.0  # Can be calculated separately if needed

    # Get calculated closing balance
    calculated_closing_balance = float(df.iloc[-1]['calculated_running_balance']) if len(df) > 0 else 0.0

    # Get statement closing balance using provider-specific field
    stmt_closing_balance = float(df.iloc[-1][balance_field]) if len(df) > 0 else 0.0

    # Determine balance match
    balance_diff = abs(calculated_closing_balance - stmt_closing_balance)
    balance_match = 'Success' if balance_diff < 0.01 else 'Failed'

    # Verification status
    duplicate_count = int(df['is_duplicate'].sum())
    balance_diff_changes = int(df.iloc[-1]['balance_diff_change_count']) if len(df) > 0 else 0
    balance_diff_change_ratio = balance_diff_changes / len(df) if len(df) > 0 else 0.0

    if balance_match == 'Success' and duplicate_count == 0:
        verification_status = 'PASS'
        verification_reason = 'Balance matches and no duplicates detected'
    elif balance_match == 'Failed':
        verification_status = 'FAIL'
        verification_reason = f'Balance mismatch: calculated={calculated_closing_balance:.2f}, statement={stmt_closing_balance:.2f}'
    elif duplicate_count > 0:
        verification_status = 'WARNING'
        verification_reason = f'Found {duplicate_count} duplicate transactions'
    else:
        verification_status = 'PASS'
        verification_reason = 'Passed with minor issues'

    # Get first and last balance from actual processed data
    first_balance = float(df.iloc[0][balance_field]) if len(df) > 0 else 0.0
    last_balance = float(df.iloc[-1][balance_field]) if len(df) > 0 else 0.0

    summary = {
        'run_id': run_id,
        'acc_number': metadata.acc_number,
        'acc_prvdr_code': metadata.acc_prvdr_code,
        'rm_name': metadata.rm_name,
        'num_rows': len(df),
        'sheet_md5': metadata.sheet_md5,
        'summary_opening_balance': metadata.summary_opening_balance,
        'summary_closing_balance': metadata.summary_closing_balance,
        'first_balance': first_balance,
        'last_balance': last_balance,
        'duplicate_count': duplicate_count,
        'balance_match': balance_match,
        'verification_status': verification_status,
        'verification_reason': verification_reason,
        'credits': credits,
        'debits': debits,
        'fees': fees,
        'charges': charges,
        'calculated_closing_balance': calculated_closing_balance,
        'balance_diff_changes': balance_diff_changes,
        'balance_diff_change_ratio': balance_diff_change_ratio,
        'meta_title': metadata.meta_title,
        'meta_author': metadata.meta_author,
        'meta_producer': metadata.meta_producer,
        'meta_created_at': metadata.meta_created_at,
        'meta_modified_at': metadata.meta_modified_at,
    }

    return summary


def batch_process_statements(db: Session, run_ids: List[str]) -> Dict[str, Any]:
    """
    Process multiple statements
    Skips statements that have already been processed (have existing summary)
    """
    results = {}
    for run_id in run_ids:
        try:
            # Check if statement is already processed
            existing_summary = db.query(Summary).filter(Summary.run_id == run_id).first()
            if existing_summary:
                logger.info(f"Statement {run_id} already processed, skipping")
                results[run_id] = {
                    'run_id': run_id,
                    'status': 'skipped',
                    'message': 'Statement already processed',
                    'processed_count': 0,
                    'duplicate_count': existing_summary.duplicate_count,
                    'balance_match': existing_summary.balance_match,
                    'verification_status': existing_summary.verification_status
                }
                continue

            # Process the statement
            result = process_statement(db, run_id)
            results[run_id] = result
        except Exception as e:
            logger.error(f"Error processing {run_id}: {e}")
            results[run_id] = {
                'run_id': run_id,
                'status': 'error',
                'message': str(e)
            }
    return results
