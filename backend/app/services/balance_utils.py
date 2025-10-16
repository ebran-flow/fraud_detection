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

def calculate_implicit_fees_format1(amount: float, description: str,
                                   apply_cashback: bool = True,
                                   apply_ind02_commission: bool = True) -> float:
    """
    Calculate implicit fees and cashbacks for Format 1.

    Format 1 specifics:
    - IND02 transactions have 0.5% commission not shown in fee field (if apply_ind02_commission=True)
    - Merchant Payment Other Single Step has 4% cashback (if apply_cashback=True)

    Args:
        amount: Transaction amount (signed for CSV, unsigned for PDF)
        description: Transaction description
        apply_cashback: Whether to apply 4% cashback on Merchant Payment Other Single Step
                       (Some statements don't apply this inline - it's handled separately)
        apply_ind02_commission: Whether to apply 0.5% commission on IND02 transactions
                               (Some statements have explicit fees instead of implicit commission)

    Returns:
        Additional fee/cashback (positive = fee to deduct, negative = cashback to add)
    """
    additional_fee = 0.0

    # IND02: 0.5% commission (conditional)
    if apply_ind02_commission and description and 'IND02' in description.upper() and 'IND01' not in description.upper():
        additional_fee += abs(amount) * 0.005
        logger.debug(f"IND02 commission: {abs(amount) * 0.005:.2f}")

    # Merchant Payment Other Single Step: 4% cashback (conditional)
    if apply_cashback and description and 'MERCHANT PAYMENT OTHER SINGLE STEP' in description.upper():
        cashback = abs(amount) * 0.04
        additional_fee -= cashback
        logger.debug(f"Merchant Payment cashback: {cashback:.2f}")

    return additional_fee


def detect_uses_implicit_cashback(transactions: list) -> bool:
    """
    Detect if statement applies implicit 4% cashback on Merchant Payment Other Single Step.

    Some Airtel statements don't apply the 4% cashback inline - it's handled separately
    or in commission wallets. This function tests ALL merchant payment transactions
    to determine the statement's behavior.

    Args:
        transactions: List of transaction dicts with keys:
                     - amount: float (signed)
                     - fee: float
                     - balance: float (stated balance)
                     - description: str

    Returns:
        True if implicit cashback should be applied, False otherwise
    """
    merchant_txns_tested = 0
    votes_for_implicit = 0
    votes_against_implicit = 0

    prev_balance = None
    for txn in transactions:
        if prev_balance is None:
            prev_balance = txn.get('balance')
            continue

        # Only test on Merchant Payment Other Single Step transactions
        description = txn.get('description', '')
        if 'MERCHANT PAYMENT OTHER SINGLE STEP' not in description.upper():
            prev_balance = txn.get('balance')
            continue

        amount = float(txn.get('amount', 0))
        fee = float(txn.get('fee', 0))
        stated_balance = float(txn.get('balance', 0))

        # Calculate WITH 4% cashback (current logic)
        cashback = abs(amount) * 0.04
        # For format_2: balance + amount - (-cashback) = balance + amount + cashback
        calc_with_cashback = prev_balance + amount - (-cashback)

        # Calculate WITHOUT cashback
        calc_without_cashback = prev_balance + amount

        # Check which matches better (allow 0.01 tolerance for float comparison)
        diff_with = abs(stated_balance - calc_with_cashback)
        diff_without = abs(stated_balance - calc_without_cashback)

        if diff_with < diff_without - 0.01:  # Clearly better with cashback
            votes_for_implicit += 1
            logger.debug(f"TXN {txn.get('txn_id', '?')}: WITH cashback matches better (diff: {diff_with:.2f} vs {diff_without:.2f})")
        elif diff_without < diff_with - 0.01:  # Clearly better without cashback
            votes_against_implicit += 1
            logger.debug(f"TXN {txn.get('txn_id', '?')}: WITHOUT cashback matches better (diff: {diff_without:.2f} vs {diff_with:.2f})")
        # If both are similar, don't count it

        merchant_txns_tested += 1
        prev_balance = stated_balance

    # Simple majority voting: if more transactions use implicit cashback, enable it
    # Otherwise, default to disabled
    if merchant_txns_tested == 0:
        logger.debug(f"No merchant payment transactions found - defaulting to NO implicit cashback")
        return False

    if votes_for_implicit + votes_against_implicit == 0:
        logger.debug(f"No clear votes for/against implicit cashback - defaulting to NO implicit cashback")
        return False

    # Simple majority: enable if more votes FOR than AGAINST
    uses_implicit = votes_for_implicit > votes_against_implicit
    logger.info(f"Implicit cashback detection: {votes_for_implicit} for, {votes_against_implicit} against (tested {merchant_txns_tested} txns) -> {'ENABLED' if uses_implicit else 'DISABLED'}")

    return uses_implicit


def detect_uses_implicit_ind02_commission(transactions: list) -> bool:
    """
    Detect if statement applies implicit 0.5% commission on IND02 transactions.

    Some Airtel statements don't apply the 0.5% commission inline - it's handled separately
    or in commission wallets. This function tests ALL IND02 transactions
    to determine the statement's behavior.

    Args:
        transactions: List of transaction dicts with keys:
                     - amount: float (signed)
                     - fee: float
                     - balance: float (stated balance)
                     - description: str

    Returns:
        True if implicit commission should be applied, False otherwise
    """
    ind02_txns_tested = 0
    votes_for_implicit = 0
    votes_against_implicit = 0

    prev_balance = None
    for txn in transactions:
        if prev_balance is None:
            prev_balance = txn.get('balance')
            continue

        # Only test on IND02 transactions (exclude IND01)
        description = txn.get('description', '')
        if 'IND02' not in description.upper() or 'IND01' in description.upper():
            prev_balance = txn.get('balance')
            continue

        amount = float(txn.get('amount', 0))
        fee = float(txn.get('fee', 0))
        stated_balance = float(txn.get('balance', 0))

        # Calculate WITH 0.5% commission
        commission = abs(amount) * 0.005
        # Commission is a fee that reduces balance: balance + amount - commission
        calc_with_commission = prev_balance + amount - commission

        # Calculate WITHOUT commission
        calc_without_commission = prev_balance + amount

        # Check which matches better (allow 0.01 tolerance for float comparison)
        diff_with = abs(stated_balance - calc_with_commission)
        diff_without = abs(stated_balance - calc_without_commission)

        if diff_with < diff_without - 0.01:  # Clearly better with commission
            votes_for_implicit += 1
            logger.debug(f"TXN {txn.get('txn_id', '?')}: WITH commission matches better (diff: {diff_with:.2f} vs {diff_without:.2f})")
        elif diff_without < diff_with - 0.01:  # Clearly better without commission
            votes_against_implicit += 1
            logger.debug(f"TXN {txn.get('txn_id', '?')}: WITHOUT commission matches better (diff: {diff_without:.2f} vs {diff_with:.2f})")
        # If both are similar, don't count it

        ind02_txns_tested += 1
        prev_balance = stated_balance

    # Simple majority voting: if more transactions use implicit commission, enable it
    # Otherwise, default to disabled
    if ind02_txns_tested == 0:
        logger.debug(f"No IND02 transactions found - defaulting to NO implicit commission")
        return False

    if votes_for_implicit + votes_against_implicit == 0:
        logger.debug(f"No clear votes for/against implicit IND02 commission - defaulting to NO implicit commission")
        return False

    # Simple majority: enable if more votes FOR than AGAINST
    uses_implicit = votes_for_implicit > votes_against_implicit
    logger.info(f"Implicit IND02 commission detection: {votes_for_implicit} for, {votes_against_implicit} against (tested {ind02_txns_tested} txns) -> {'ENABLED' if uses_implicit else 'DISABLED'}")

    return uses_implicit


def calculate_opening_balance_format1_pdf(first_balance: float, first_amount: float,
                                          first_fee: float, first_direction: str,
                                          first_description: str = '',
                                          apply_cashback: bool = True,
                                          apply_ind02_commission: bool = True) -> float:
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
        apply_cashback: Whether to apply 4% cashback on Merchant Payment
        apply_ind02_commission: Whether to apply 0.5% commission on IND02

    Returns:
        Opening balance
    """
    direction = str(first_direction).lower()
    first_balance = float(first_balance)
    first_amount = float(first_amount)
    first_fee = float(first_fee)

    additional_fee = calculate_implicit_fees_format1(first_amount, first_description,
                                                     apply_cashback, apply_ind02_commission)

    if direction in ['credit', 'cr']:
        return first_balance - first_amount - first_fee + additional_fee
    else:  # debit/dr
        return first_balance + first_amount + first_fee + additional_fee


def calculate_opening_balance_format1_csv(first_balance: float, first_amount: float,
                                          first_fee: float, first_description: str = '',
                                          apply_cashback: bool = True,
                                          apply_ind02_commission: bool = True) -> float:
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
        apply_cashback: Whether to apply 4% cashback on Merchant Payment
        apply_ind02_commission: Whether to apply 0.5% commission on IND02

    Returns:
        Opening balance
    """
    first_balance = float(first_balance)
    first_amount = float(first_amount)
    first_fee = float(first_fee)

    additional_fee = calculate_implicit_fees_format1(first_amount, first_description,
                                                     apply_cashback, apply_ind02_commission)

    return first_balance - first_amount - first_fee + additional_fee


def apply_transaction_format1_pdf(balance: float, amount: float, fee: float,
                                  direction: str, description: str = '',
                                  apply_cashback: bool = True,
                                  apply_ind02_commission: bool = True) -> float:
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
        apply_cashback: Whether to apply 4% cashback on Merchant Payment
        apply_ind02_commission: Whether to apply 0.5% commission on IND02

    Returns:
        New balance
    """
    direction = str(direction).lower()
    balance = float(balance)
    amount = float(amount)
    fee = float(fee)

    additional_fee = calculate_implicit_fees_format1(amount, description,
                                                     apply_cashback, apply_ind02_commission)

    if direction in ['credit', 'cr']:
        return balance + amount - fee - additional_fee
    else:  # debit/dr
        return balance - amount - fee - additional_fee


def apply_transaction_format1_csv(balance: float, amount: float, fee: float,
                                  description: str = '',
                                  apply_cashback: bool = True,
                                  apply_ind02_commission: bool = True) -> float:
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
        apply_cashback: Whether to apply 4% cashback on Merchant Payment
        apply_ind02_commission: Whether to apply 0.5% commission on IND02

    Returns:
        New balance
    """
    balance = float(balance)
    amount = float(amount)
    fee = float(fee)

    additional_fee = calculate_implicit_fees_format1(amount, description,
                                                     apply_cashback, apply_ind02_commission)

    return balance + amount - fee - additional_fee


# ============================================================================
# FORMAT 2 LOGIC (PDF/CSV with signed amounts, fees included)
# ============================================================================

def calculate_opening_balance_format2(first_balance: float, first_amount: float,
                                      first_description: str = '',
                                      apply_cashback: bool = True,
                                      apply_ind02_commission: bool = True) -> float:
    """
    Calculate opening balance for Format 2 (signed amounts, fees included).

    Logic: Opening = Balance - amount - implicit_fees
    - Amount is signed (positive=credit, negative=debit)
    - Fees are already included in the amount
    - Implicit fees/cashbacks apply (IND02, Merchant Payment)

    Args:
        first_balance: Balance shown in first transaction
        first_amount: Amount (signed, fees included)
        first_description: Description for detecting implicit fees
        apply_cashback: Whether to apply 4% cashback on Merchant Payment
        apply_ind02_commission: Whether to apply 0.5% commission on IND02

    Returns:
        Opening balance
    """
    first_balance = float(first_balance)
    first_amount = float(first_amount)

    # Calculate implicit fees (applies to all Airtel formats)
    additional_fee = calculate_implicit_fees_format1(first_amount, first_description,
                                                     apply_cashback, apply_ind02_commission)

    # For signed amounts: negative = debit (reduces balance), positive = credit (increases balance)
    # Additional_fee is positive for fees (reduce balance), negative for cashback (increase balance)
    return first_balance - first_amount - additional_fee


def apply_transaction_format2(balance: float, amount: float, description: str = '',
                              apply_cashback: bool = True,
                              apply_ind02_commission: bool = True) -> float:
    """
    Apply transaction to balance for Format 2 (signed amounts, fees included).

    Logic: New Balance = Balance + amount - implicit_fees
    - Amount is signed (positive=credit, negative=debit)
    - Fees are already included in the amount
    - Implicit fees/cashbacks apply (IND02, Merchant Payment)

    Args:
        balance: Current balance
        amount: Amount (signed, fees included)
        description: Description for detecting implicit fees
        apply_cashback: Whether to apply 4% cashback on Merchant Payment
        apply_ind02_commission: Whether to apply 0.5% commission on IND02

    Returns:
        New balance
    """
    balance = float(balance)
    amount = float(amount)

    # Calculate implicit fees (applies to all Airtel formats)
    additional_fee = calculate_implicit_fees_format1(amount, description,
                                                     apply_cashback, apply_ind02_commission)

    # For signed amounts: negative = debit (reduces balance), positive = credit (increases balance)
    # Additional_fee is positive for fees (reduce balance), negative for cashback (increase balance)
    return balance + amount - additional_fee


# ============================================================================
# MTN LOGIC (transaction-type-specific balance calculation)
# ============================================================================

def calculate_opening_balance_mtn(first_balance: float, first_amount: float,
                                   first_txn_type: str, first_fee: float = 0) -> float:
    """
    Calculate opening balance for MTN.

    MTN Logic (based on transaction type):
    - CASH_OUT: Agent gives cash, receives mobile money -> balance increases
      Opening = Balance - amount + fee
    - CASH_IN: Agent receives cash, pays mobile money -> balance decreases
      Opening = Balance + amount + fee
    - BILL PAYMENT: Agent pays bill -> balance decreases
      Opening = Balance + amount + fee
    - TRANSFER: Amount is signed
      Opening = Balance - amount + fee

    Note: Fees reduce balance, commission/tax don't affect float_balance

    Args:
        first_balance: Float balance from first transaction
        first_amount: Transaction amount
        first_txn_type: Transaction type (CASH_OUT, CASH_IN, BILL PAYMENT, TRANSFER, etc.)
        first_fee: Transaction fee (default 0)

    Returns:
        Opening balance
    """
    first_balance = float(first_balance)
    first_amount = float(first_amount)
    first_fee = float(first_fee) if first_fee else 0.0
    txn_type = str(first_txn_type).upper()

    if txn_type == 'CASH_OUT':
        # Agent gives cash, receives mobile money -> balance increases
        # Opening = Balance - amount + fee
        return first_balance - first_amount + first_fee
    elif txn_type in ['CASH_IN', 'BILL PAYMENT', 'DEBIT']:
        # Agent receives cash/pays bill/debit -> balance decreases
        # Opening = Balance + amount + fee
        return first_balance + first_amount + first_fee
    elif txn_type in ['DEPOSIT', 'REFUND']:
        # Deposit/Refund -> balance increases by (amount - fee)
        # Opening = Balance - (amount - fee)
        return first_balance - first_amount + first_fee
    elif txn_type in ['REVERSAL', 'LOAN_REPAYMENT', 'ADJUSTMENT']:
        # Reversal/Loan repayment/Adjustment -> signed amount (normalized in processor)
        # Opening = Balance - amount + fee
        return first_balance - first_amount + first_fee
    else:  # TRANSFER, BATCH_TRANSFER, or other types
        # Amount is signed (negative=outgoing, positive=incoming)
        # Opening = Balance - amount + fee
        return first_balance - first_amount + first_fee


def apply_transaction_mtn(balance: float, amount: float, txn_type: str, fee: float = 0) -> float:
    """
    Apply transaction to balance for MTN.

    MTN Logic (based on transaction type):
    - CASH_OUT: Agent gives cash, receives mobile money -> balance increases
      New Balance = Balance + amount - fee
    - CASH_IN: Agent receives cash, pays mobile money -> balance decreases
      New Balance = Balance - amount - fee
    - BILL PAYMENT: Agent pays bill -> balance decreases
      New Balance = Balance - amount - fee
    - TRANSFER: Amount is signed
      New Balance = Balance + amount - fee

    Note: Fees reduce balance, commission/tax don't affect float_balance

    Args:
        balance: Current balance
        amount: Transaction amount
        txn_type: Transaction type (CASH_OUT, CASH_IN, BILL PAYMENT, TRANSFER, etc.)
        fee: Transaction fee (default 0)

    Returns:
        New balance
    """
    balance = float(balance)
    amount = float(amount)
    fee = float(fee) if fee else 0.0
    txn_type = str(txn_type).upper()

    if txn_type == 'CASH_OUT':
        # Agent gives cash, receives mobile money -> balance increases
        # New Balance = Balance + amount - fee
        return balance + amount - fee
    elif txn_type in ['CASH_IN', 'BILL PAYMENT', 'DEBIT']:
        # Agent receives cash/pays bill/debit -> balance decreases
        # New Balance = Balance - amount - fee
        return balance - amount - fee
    elif txn_type in ['DEPOSIT', 'REFUND']:
        # Deposit/Refund -> balance increases by (amount - fee)
        # New Balance = Balance + (amount - fee)
        return balance + amount - fee
    elif txn_type in ['REVERSAL', 'LOAN_REPAYMENT', 'ADJUSTMENT']:
        # Reversal/Loan repayment/Adjustment -> signed amount (normalized in processor)
        # New Balance = Balance + amount - fee
        return balance + amount - fee
    else:  # TRANSFER, BATCH_TRANSFER, or other types
        # Amount is signed (negative=outgoing, positive=incoming)
        # New Balance = Balance + amount - fee
        return balance + amount - fee


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
