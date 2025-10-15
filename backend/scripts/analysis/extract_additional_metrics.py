#!/usr/bin/env python3
"""
Extract additional fraud detection metrics from statements
Metrics extracted:
1. Transaction ID sequence integrity (gaps, duplicates, pattern breaks)
2. Balance jump count (large unexplained balance changes)
3. Timestamp anomalies (same-second transactions, non-chronological)
4. PDF metadata (creation date, modification date, producer)
5. Amount patterns (round numbers, duplicates)
"""
import os
import sys
import logging
import json
import pypdfium2 as pdfium
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3307')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')


def extract_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract PDF metadata for anomaly detection
    Returns: dict with creation_date, mod_date, producer, creator
    """
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        metadata = pdf.get_metadata_dict()

        return {
            'creation_date': metadata.get('CreationDate', ''),
            'mod_date': metadata.get('ModDate', ''),
            'producer': metadata.get('Producer', ''),
            'creator': metadata.get('Creator', ''),
            'title': metadata.get('Title', ''),
        }
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {e}")
        return {}


def check_transaction_id_integrity(transactions: list) -> dict:
    """
    Check transaction ID sequence for gaps, duplicates, and pattern breaks
    transactions: list of dicts with 'transaction_id' field

    Returns: {
        'has_gaps': bool,
        'gap_count': int,
        'has_duplicates': bool,
        'duplicate_count': int,
        'has_pattern_breaks': bool,
        'pattern_break_count': int,
        'duplicate_ids': list,
    }
    """
    if not transactions:
        return {
            'has_gaps': False,
            'gap_count': 0,
            'has_duplicates': False,
            'duplicate_count': 0,
            'has_pattern_breaks': False,
            'pattern_break_count': 0,
            'duplicate_ids': [],
        }

    # Extract transaction IDs
    tx_ids = [tx.get('transaction_id', '') for tx in transactions if tx.get('transaction_id')]

    if not tx_ids:
        return {
            'has_gaps': False,
            'gap_count': 0,
            'has_duplicates': False,
            'duplicate_count': 0,
            'has_pattern_breaks': False,
            'pattern_break_count': 0,
            'duplicate_ids': [],
        }

    # Check for duplicates
    tx_id_counts = Counter(tx_ids)
    duplicates = [tid for tid, count in tx_id_counts.items() if count > 1]

    # Try to extract numeric sequences from transaction IDs
    # Common patterns: TXN123456, 123456, TXN-123456, etc.
    numeric_sequences = []
    pattern_formats = []

    for tx_id in tx_ids:
        # Extract all numbers from transaction ID
        numbers = re.findall(r'\d+', tx_id)
        if numbers:
            # Use the longest number sequence (likely the sequential part)
            longest_num = max(numbers, key=len)
            numeric_sequences.append(int(longest_num))

            # Track the pattern format (e.g., "TXN###" where ### is the number)
            pattern = re.sub(r'\d+', '#', tx_id)
            pattern_formats.append(pattern)

    # Check for gaps in numeric sequence
    gap_count = 0
    if len(numeric_sequences) > 1:
        sorted_seqs = sorted(numeric_sequences)
        for i in range(len(sorted_seqs) - 1):
            gap = sorted_seqs[i + 1] - sorted_seqs[i]
            if gap > 1:
                gap_count += (gap - 1)

    # Check for pattern breaks (format changes)
    pattern_counts = Counter(pattern_formats)
    has_pattern_breaks = len(pattern_counts) > 1
    pattern_break_count = len(pattern_formats) - max(pattern_counts.values()) if has_pattern_breaks else 0

    return {
        'has_gaps': gap_count > 0,
        'gap_count': gap_count,
        'has_duplicates': len(duplicates) > 0,
        'duplicate_count': len(duplicates),
        'has_pattern_breaks': has_pattern_breaks,
        'pattern_break_count': pattern_break_count,
        'duplicate_ids': duplicates,
    }


def check_balance_jumps(transactions: list, threshold: float = 0.5) -> dict:
    """
    Check for large unexplained balance changes (>threshold of previous balance)
    transactions: list of dicts with 'balance' field
    threshold: flag if balance changes by more than this ratio (default 50%)

    Returns: {
        'balance_jump_count': int,
        'max_jump_ratio': float,
        'jump_positions': list of transaction indices
    }
    """
    if not transactions or len(transactions) < 2:
        return {
            'balance_jump_count': 0,
            'max_jump_ratio': 0.0,
            'jump_positions': [],
        }

    balance_jumps = []
    jump_positions = []

    for i in range(len(transactions) - 1):
        prev_balance = transactions[i].get('balance')
        curr_balance = transactions[i + 1].get('balance')

        if prev_balance is None or curr_balance is None:
            continue

        if prev_balance == 0:
            continue

        # Calculate ratio of change
        change_ratio = abs(curr_balance - prev_balance) / abs(prev_balance)

        if change_ratio > threshold:
            balance_jumps.append(change_ratio)
            jump_positions.append(i + 1)

    return {
        'balance_jump_count': len(balance_jumps),
        'max_jump_ratio': max(balance_jumps) if balance_jumps else 0.0,
        'jump_positions': jump_positions,
    }


def check_timestamp_anomalies(transactions: list) -> dict:
    """
    Check for timestamp anomalies:
    - Same-second transactions (unusual for individual accounts)
    - Non-chronological timestamps
    - Business hours distribution

    Returns: {
        'same_second_groups': int,
        'non_chronological_count': int,
        'business_hours_ratio': float,
        'weekend_ratio': float,
    }
    """
    if not transactions or len(transactions) < 2:
        return {
            'same_second_groups': 0,
            'non_chronological_count': 0,
            'business_hours_ratio': 0.0,
            'weekend_ratio': 0.0,
        }

    timestamps = []
    for tx in transactions:
        date_time = tx.get('date_time')
        if date_time:
            try:
                if isinstance(date_time, str):
                    # Try multiple datetime formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S']:
                        try:
                            dt = datetime.strptime(date_time, fmt)
                            timestamps.append(dt)
                            break
                        except:
                            continue
                else:
                    timestamps.append(date_time)
            except:
                continue

    if len(timestamps) < 2:
        return {
            'same_second_groups': 0,
            'non_chronological_count': 0,
            'business_hours_ratio': 0.0,
            'weekend_ratio': 0.0,
        }

    # Check for same-second transactions
    timestamp_strs = [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in timestamps]
    timestamp_counts = Counter(timestamp_strs)
    same_second_groups = sum(1 for count in timestamp_counts.values() if count > 1)

    # Check for non-chronological order
    non_chronological_count = 0
    for i in range(len(timestamps) - 1):
        if timestamps[i] > timestamps[i + 1]:
            non_chronological_count += 1

    # Check business hours (8 AM - 6 PM)
    business_hours_count = sum(1 for dt in timestamps if 8 <= dt.hour < 18)
    business_hours_ratio = business_hours_count / len(timestamps)

    # Check weekends (Saturday=5, Sunday=6)
    weekend_count = sum(1 for dt in timestamps if dt.weekday() >= 5)
    weekend_ratio = weekend_count / len(timestamps)

    return {
        'same_second_groups': same_second_groups,
        'non_chronological_count': non_chronological_count,
        'business_hours_ratio': business_hours_ratio,
        'weekend_ratio': weekend_ratio,
    }


def check_amount_patterns(transactions: list) -> dict:
    """
    Check for suspicious amount patterns:
    - Round number ratio (amounts ending in 000, 500, etc.)
    - Duplicate amounts
    - Benford's law compliance (first digit distribution)

    Returns: {
        'round_number_ratio': float,
        'duplicate_amount_ratio': float,
        'benford_score': float (0-1, closer to 1 = more natural)
    }
    """
    if not transactions:
        return {
            'round_number_ratio': 0.0,
            'duplicate_amount_ratio': 0.0,
            'benford_score': 0.0,
        }

    amounts = []
    for tx in transactions:
        amount = tx.get('amount')
        if amount is not None:
            try:
                amounts.append(float(amount))
            except:
                continue

    if not amounts:
        return {
            'round_number_ratio': 0.0,
            'duplicate_amount_ratio': 0.0,
            'benford_score': 0.0,
        }

    # Check for round numbers (divisible by 1000 or 500)
    round_count = sum(1 for amt in amounts if amt % 1000 == 0 or amt % 500 == 0)
    round_number_ratio = round_count / len(amounts)

    # Check for duplicate amounts
    amount_counts = Counter(amounts)
    duplicate_count = sum(1 for count in amount_counts.values() if count > 1)
    duplicate_amount_ratio = duplicate_count / len(amounts)

    # Benford's Law check (first digit distribution)
    # Expected distribution: P(d) = log10(1 + 1/d)
    benford_expected = {
        1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
        6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
    }

    first_digits = []
    for amt in amounts:
        if amt > 0:
            first_digit = int(str(int(amt))[0])
            if 1 <= first_digit <= 9:
                first_digits.append(first_digit)

    if len(first_digits) < 10:
        # Not enough data for Benford's Law
        benford_score = 0.5
    else:
        # Calculate chi-square distance from expected distribution
        digit_counts = Counter(first_digits)
        observed_dist = {d: digit_counts.get(d, 0) / len(first_digits) for d in range(1, 10)}

        # Calculate normalized difference (0 = perfect match, 1 = worst)
        total_diff = sum(abs(observed_dist[d] - benford_expected[d]) for d in range(1, 10))
        benford_score = 1.0 - (total_diff / 2.0)  # Normalize to 0-1

    return {
        'round_number_ratio': round_number_ratio,
        'duplicate_amount_ratio': duplicate_amount_ratio,
        'benford_score': benford_score,
    }


def extract_metrics_for_statement(run_id: str, pdf_path: str, conn) -> dict:
    """
    Extract all additional metrics for a single statement
    """
    # Get transactions for this statement (using UATL table)
    result = conn.execute(text("""
        SELECT
            txn_id as transaction_id,
            txn_date as date_time,
            amount,
            balance
        FROM uatl_processed_statements
        WHERE run_id = :run_id
        ORDER BY txn_date
    """), {'run_id': run_id})

    transactions = [dict(row._mapping) for row in result]

    # Extract PDF metadata
    pdf_metadata = {}
    if pdf_path and os.path.exists(pdf_path):
        pdf_metadata = extract_pdf_metadata(pdf_path)

    # Calculate all metrics
    tx_id_integrity = check_transaction_id_integrity(transactions)
    balance_jumps = check_balance_jumps(transactions)
    timestamp_anomalies = check_timestamp_anomalies(transactions)
    amount_patterns = check_amount_patterns(transactions)

    return {
        'run_id': run_id,
        'pdf_metadata': pdf_metadata,
        'transaction_id_integrity': tx_id_integrity,
        'balance_jumps': balance_jumps,
        'timestamp_anomalies': timestamp_anomalies,
        'amount_patterns': amount_patterns,
        'transaction_count': len(transactions),
    }


def scan_all_statements():
    """
    Scan all Airtel format_2 statements and extract additional metrics
    """
    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        logger.info("Finding Airtel format_2 statements...")

        # Get all format_2 UATL statements
        result = conn.execute(text("""
            SELECT
                m.run_id,
                m.pdf_path,
                m.acc_number,
                s.balance_match,
                s.balance_diff_change_ratio
            FROM metadata m
            LEFT JOIN summary s ON m.run_id = s.run_id
            WHERE m.acc_prvdr_code = 'UATL'
            AND m.format = 'format_2'
            AND m.pdf_path IS NOT NULL
            ORDER BY m.run_id
        """))

        statements = result.fetchall()
        total = len(statements)

        logger.info(f"Found {total} format_2 UATL statements")
        logger.info(f"Extracting additional metrics...")
        logger.info(f"Estimated duration: {total/3/60:.1f} minutes at ~3 statements/sec")
        logger.info("")

        all_results = []
        start_time = datetime.now()

        for idx, row in enumerate(statements, 1):
            run_id = row[0]
            pdf_path = row[1]
            acc_number = row[2]
            balance_match = row[3]
            balance_diff_change_ratio = row[4]

            # Fix path if needed
            if pdf_path and not os.path.exists(pdf_path):
                alt_paths = [
                    pdf_path.replace('/app/', '/home/ebran/Developer/projects/airtel_fraud_detection/backend/'),
                    pdf_path.replace('/airtel_fraud_detection/', '/airtel_fraud_detection/backend/'),
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        pdf_path = alt_path
                        break

            try:
                # Extract metrics
                metrics = extract_metrics_for_statement(run_id, pdf_path, conn)

                # Add metadata
                metrics['acc_number'] = acc_number
                metrics['balance_match'] = balance_match
                metrics['balance_diff_change_ratio'] = float(balance_diff_change_ratio) if balance_diff_change_ratio else 0.0

                all_results.append(metrics)

                # Log interesting findings
                flags = []
                if metrics['transaction_id_integrity']['has_duplicates']:
                    flags.append(f"Duplicate TxIDs: {metrics['transaction_id_integrity']['duplicate_count']}")
                if metrics['transaction_id_integrity']['gap_count'] > 10:
                    flags.append(f"ID Gaps: {metrics['transaction_id_integrity']['gap_count']}")
                if metrics['balance_jumps']['balance_jump_count'] > 0:
                    flags.append(f"Balance Jumps: {metrics['balance_jumps']['balance_jump_count']}")
                if metrics['timestamp_anomalies']['non_chronological_count'] > 0:
                    flags.append(f"Non-chrono: {metrics['timestamp_anomalies']['non_chronological_count']}")

                if flags:
                    logger.info(f"[{idx}/{total}] 🚨 {run_id} - {', '.join(flags)}")
                else:
                    logger.info(f"[{idx}/{total}] ✅ {run_id} - Clean")

                # Progress indicator
                if idx % 100 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (total - idx) / rate if rate > 0 else 0
                    logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Speed: {rate:.2f}/s | ETA: {remaining/60:.1f}m")
                    logger.info("")

            except Exception as e:
                logger.error(f"[{idx}/{total}] ❌ {run_id} - Error: {e}")
                continue

        # Save results
        output_file = 'additional_metrics_results.json'
        output_data = {
            'scan_date': datetime.now().isoformat(),
            'total_scanned': total,
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'results': all_results,
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        # Final report
        logger.info("")
        logger.info("=" * 80)
        logger.info("FINAL REPORT - ADDITIONAL METRICS EXTRACTION")
        logger.info("=" * 80)
        logger.info(f"Total statements scanned: {total}")
        logger.info(f"Duration: {datetime.now() - start_time}")
        logger.info(f"Average speed: {total/(datetime.now() - start_time).total_seconds():.2f} statements/second")
        logger.info("")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 80)


if __name__ == '__main__':
    scan_all_statements()
