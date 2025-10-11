"""
Balance Calculation Utilities
Centralizes logic for handling signed/unsigned amounts and balance calculations
Following DRY principle to avoid duplication across processor and parsers
"""
import logging
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)


def is_amount_signed(df: pd.DataFrame, pdf_format: int, provider_code: str) -> bool:
    """
    Determine if amounts in the dataframe are signed or unsigned.

    Args:
        df: DataFrame with transaction data
        pdf_format: PDF format (1 or 2)
        provider_code: Provider code (UATL or UMTN)

    Returns:
        True if amounts are signed (Format 2, UMTN, or CSV Format 1)
        False if amounts are unsigned (PDF Format 1)
    """
    if pdf_format == 2 or provider_code == 'UMTN':
        return True

    if pdf_format == 1 and not df.empty:
        # Check if amounts have negative values (indicates signed amounts from CSV)
        return (df['amount'] < 0).any()

    return False


def calculate_opening_balance(first_balance: float, first_amount: float, first_fee: float,
                              first_direction: str, is_signed: bool, pdf_format: int) -> float:
    """
    Calculate opening balance from first transaction.

    Args:
        first_balance: Balance from first transaction
        first_amount: Amount from first transaction
        first_fee: Fee from first transaction
        first_direction: Transaction direction ('credit', 'debit', 'cr', 'dr')
        is_signed: Whether amounts are signed
        pdf_format: PDF format (1 or 2)

    Returns:
        Calculated opening balance
    """
    direction = str(first_direction).lower()

    if is_signed:
        # Signed amounts
        if pdf_format == 2:
            # Format 2: fees already included in signed amount, don't subtract separately
            return first_balance - first_amount
        else:
            # Format 1 CSV: fees separate, subtract both
            return first_balance - first_amount - first_fee
    else:
        # Unsigned amounts (Format 1 PDF): use direction
        if direction in ['credit', 'cr']:
            return first_balance - first_amount - first_fee
        else:  # debit/dr
            return first_balance + first_amount + first_fee


def apply_transaction_to_balance(balance: float, amount: float, fee: float,
                                 direction: str, is_signed: bool, pdf_format: int = 1) -> float:
    """
    Apply a single transaction to running balance.

    Args:
        balance: Current balance
        amount: Transaction amount
        fee: Transaction fee
        direction: Transaction direction ('credit', 'debit', 'cr', 'dr')
        is_signed: Whether amounts are signed
        pdf_format: PDF format (1 or 2)

    Returns:
        New balance after applying transaction
    """
    direction = str(direction).lower()

    if is_signed:
        # Signed amounts
        if pdf_format == 2:
            # Format 2: fees already included in signed amount, just add amount
            return balance + amount
        else:
            # Format 1 CSV: fees separate, add amount and subtract fee
            return balance + amount - fee
    else:
        # Unsigned amounts (Format 1 PDF): use direction
        if direction in ['credit', 'cr']:
            return balance + amount - fee
        else:  # debit/dr
            return balance - amount - fee


def calculate_total_credits_debits(df: pd.DataFrame, pdf_format: int,
                                   provider_code: str) -> Tuple[float, float]:
    """
    Calculate total credits and debits from dataframe.

    Args:
        df: DataFrame with transaction data
        pdf_format: PDF format (1 or 2)
        provider_code: Provider code (UATL or UMTN)

    Returns:
        Tuple of (total_credits, total_debits)
    """
    is_signed = is_amount_signed(df, pdf_format, provider_code)

    if is_signed:
        # Signed amounts: positive = credit, negative = debit
        credits = float(df[df['amount'] > 0]['amount'].sum())
        debits = float(abs(df[df['amount'] < 0]['amount'].sum()))
    else:
        # Unsigned amounts: use direction column
        credits = float(df[df['txn_direction'].str.lower().isin(['credit', 'cr'])]['amount'].sum())
        debits = float(df[df['txn_direction'].str.lower().isin(['debit', 'dr'])]['amount'].sum())

    return credits, debits
