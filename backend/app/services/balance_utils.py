"""
Balance Calculation Utilities
Separate logic for Format 1 and Format 2 to avoid confusion and bugs
"""
import logging
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# FORMAT 1 LOGIC (PDF with unsigned amounts + direction OR CSV with signed amounts)
# ============================================================================

def calculate_implicit_fees_format1(amount: float, description: str) -> float:
    """
    Calculate implicit fees and cashbacks for Format 1.

    Format 1 specifics:
    - IND02 transactions have 0.5% commission not shown in fee field
    - Merchant Payment Other Single Step has 4% cashback

    Args:
        amount: Transaction amount (signed for CSV, unsigned for PDF)
        description: Transaction description

    Returns:
        Additional fee/cashback (positive = fee to deduct, negative = cashback to add)
    """
    additional_fee = 0.0

    # IND02: 0.5% commission
    if description and 'IND02' in description.upper() and 'IND01' not in description.upper():
        additional_fee += abs(amount) * 0.005
        logger.debug(f"IND02 commission: {abs(amount) * 0.005:.2f}")

    # Merchant Payment Other Single Step: 4% cashback
    if description and 'MERCHANT PAYMENT OTHER SINGLE STEP' in description.upper():
        cashback = abs(amount) * 0.04
        additional_fee -= cashback
        logger.debug(f"Merchant Payment cashback: {cashback:.2f}")

    return additional_fee


def calculate_opening_balance_format1_pdf(first_balance: float, first_amount: float,
                                          first_fee: float, first_direction: str,
                                          first_description: str = '') -> float:
    """
    Calculate opening balance for Format 1 PDF (unsigned amounts).

    Logic: Opening = Balance ± amount ± fee ± implicit_fees (based on direction)
    - Credit: Opening = Balance - amount - fee + implicit_fees
    - Debit:  Opening = Balance + amount + fee + implicit_fees

    Args:
        first_balance: Balance shown in first transaction
        first_amount: Amount (unsigned)
        first_fee: Fee
        first_direction: 'credit', 'debit', 'cr', 'dr'
        first_description: Description for detecting implicit fees

    Returns:
        Opening balance
    """
    direction = str(first_direction).lower()
    first_balance = float(first_balance)
    first_amount = float(first_amount)
    first_fee = float(first_fee)

    additional_fee = calculate_implicit_fees_format1(first_amount, first_description)

    if direction in ['credit', 'cr']:
        return first_balance - first_amount - first_fee + additional_fee
    else:  # debit/dr
        return first_balance + first_amount + first_fee + additional_fee


def calculate_opening_balance_format1_csv(first_balance: float, first_amount: float,
                                          first_fee: float, first_description: str = '') -> float:
    """
    Calculate opening balance for Format 1 CSV (signed amounts).

    Logic: Opening = Balance - amount - fee + implicit_fees
    - Amount is already signed (positive=credit, negative=debit)
    - Fees are separate

    Args:
        first_balance: Balance shown in first transaction
        first_amount: Amount (signed)
        first_fee: Fee
        first_description: Description for detecting implicit fees

    Returns:
        Opening balance
    """
    first_balance = float(first_balance)
    first_amount = float(first_amount)
    first_fee = float(first_fee)

    additional_fee = calculate_implicit_fees_format1(first_amount, first_description)

    return first_balance - first_amount - first_fee + additional_fee


def apply_transaction_format1_pdf(balance: float, amount: float, fee: float,
                                  direction: str, description: str = '') -> float:
    """
    Apply transaction to balance for Format 1 PDF (unsigned amounts).

    Logic: New Balance = Balance ± amount - fee - implicit_fees (based on direction)
    - Credit: Balance = Balance + amount - fee - implicit_fees
    - Debit:  Balance = Balance - amount - fee - implicit_fees

    Args:
        balance: Current balance
        amount: Amount (unsigned)
        fee: Fee
        direction: 'credit', 'debit', 'cr', 'dr'
        description: Description for detecting implicit fees

    Returns:
        New balance
    """
    direction = str(direction).lower()
    balance = float(balance)
    amount = float(amount)
    fee = float(fee)

    additional_fee = calculate_implicit_fees_format1(amount, description)

    if direction in ['credit', 'cr']:
        return balance + amount - fee - additional_fee
    else:  # debit/dr
        return balance - amount - fee - additional_fee


def apply_transaction_format1_csv(balance: float, amount: float, fee: float,
                                  description: str = '') -> float:
    """
    Apply transaction to balance for Format 1 CSV (signed amounts).

    Logic: New Balance = Balance + amount - fee - implicit_fees
    - Amount is already signed (positive=credit, negative=debit)
    - Fees are separate

    Args:
        balance: Current balance
        amount: Amount (signed)
        fee: Fee
        description: Description for detecting implicit fees

    Returns:
        New balance
    """
    balance = float(balance)
    amount = float(amount)
    fee = float(fee)

    additional_fee = calculate_implicit_fees_format1(amount, description)

    return balance + amount - fee - additional_fee


# ============================================================================
# FORMAT 2 LOGIC (PDF/CSV with signed amounts, fees included)
# ============================================================================

def calculate_opening_balance_format2(first_balance: float, first_amount: float) -> float:
    """
    Calculate opening balance for Format 2 (signed amounts, fees included).

    Logic: Opening = Balance - amount
    - Amount is signed (positive=credit, negative=debit)
    - Fees are already included in the amount
    - No implicit fees/cashbacks to calculate

    Args:
        first_balance: Balance shown in first transaction
        first_amount: Amount (signed, fees included)

    Returns:
        Opening balance
    """
    first_balance = float(first_balance)
    first_amount = float(first_amount)

    return first_balance - first_amount


def apply_transaction_format2(balance: float, amount: float) -> float:
    """
    Apply transaction to balance for Format 2 (signed amounts, fees included).

    Logic: New Balance = Balance + amount
    - Amount is signed (positive=credit, negative=debit)
    - Fees are already included in the amount
    - No implicit fees/cashbacks to calculate

    Args:
        balance: Current balance
        amount: Amount (signed, fees included)

    Returns:
        New balance
    """
    balance = float(balance)
    amount = float(amount)

    return balance + amount


# ============================================================================
# MTN LOGIC (similar to Format 2 but uses float_balance field)
# ============================================================================

def calculate_opening_balance_mtn(first_balance: float, first_amount: float) -> float:
    """
    Calculate opening balance for MTN (same as Format 2).

    Logic: Opening = Balance - amount

    Args:
        first_balance: Float balance from first transaction
        first_amount: Amount (signed, fees included)

    Returns:
        Opening balance
    """
    return calculate_opening_balance_format2(first_balance, first_amount)


def apply_transaction_mtn(balance: float, amount: float) -> float:
    """
    Apply transaction to balance for MTN (same as Format 2).

    Logic: New Balance = Balance + amount

    Args:
        balance: Current balance
        amount: Amount (signed, fees included)

    Returns:
        New balance
    """
    return apply_transaction_format2(balance, amount)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_format1_csv(df: pd.DataFrame, pdf_format: int) -> bool:
    """
    Determine if this is Format 1 CSV (signed amounts).

    Args:
        df: DataFrame with transaction data
        pdf_format: PDF format (1 or 2)

    Returns:
        True if Format 1 CSV (has negative amounts), False otherwise
    """
    if pdf_format == 1 and not df.empty:
        return (df['amount'] < 0).any()
    return False


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
    # Format 2 and MTN have signed amounts
    if pdf_format == 2 or provider_code == 'UMTN':
        credits = float(df[df['amount'] > 0]['amount'].sum())
        debits = float(abs(df[df['amount'] < 0]['amount'].sum()))
    # Format 1 CSV has signed amounts
    elif is_format1_csv(df, pdf_format):
        credits = float(df[df['amount'] > 0]['amount'].sum())
        debits = float(abs(df[df['amount'] < 0]['amount'].sum()))
    # Format 1 PDF has unsigned amounts with direction
    else:
        credits = float(df[df['txn_direction'].str.lower().isin(['credit', 'cr'])]['amount'].sum())
        debits = float(df[df['txn_direction'].str.lower().isin(['debit', 'dr'])]['amount'].sum())

    return credits, debits
