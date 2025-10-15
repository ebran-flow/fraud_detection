#!/usr/bin/env python3
"""
Test additional metrics extraction on a few sample statements
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from extract_additional_metrics import extract_metrics_for_statement

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


def test_on_samples():
    """
    Test metrics extraction on a few sample statements
    """
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        # Get 5 sample statements
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
            ORDER BY RAND()
            LIMIT 5
        """))

        statements = result.fetchall()

        for idx, row in enumerate(statements, 1):
            run_id = row[0]
            pdf_path = row[1]
            acc_number = row[2]
            balance_match = row[3]
            balance_diff_change_ratio = row[4]

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"Testing statement {idx}/5: {run_id}")
            logger.info("=" * 80)

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

                # Display results
                logger.info(f"Run ID: {run_id}")
                logger.info(f"Account: {acc_number}")
                logger.info(f"Balance Match: {balance_match}")
                logger.info(f"Transactions: {metrics['transaction_count']}")
                logger.info("")

                # PDF Metadata
                logger.info("PDF Metadata:")
                if metrics['pdf_metadata']:
                    for key, value in metrics['pdf_metadata'].items():
                        logger.info(f"  {key}: {value}")
                else:
                    logger.info("  No metadata available")
                logger.info("")

                # Transaction ID Integrity
                logger.info("Transaction ID Integrity:")
                tx_integrity = metrics['transaction_id_integrity']
                logger.info(f"  Has Gaps: {tx_integrity['has_gaps']} (count: {tx_integrity['gap_count']})")
                logger.info(f"  Has Duplicates: {tx_integrity['has_duplicates']} (count: {tx_integrity['duplicate_count']})")
                if tx_integrity['duplicate_ids']:
                    logger.info(f"  Duplicate IDs: {tx_integrity['duplicate_ids'][:5]}")  # Show first 5
                logger.info(f"  Has Pattern Breaks: {tx_integrity['has_pattern_breaks']} (count: {tx_integrity['pattern_break_count']})")
                logger.info("")

                # Balance Jumps
                logger.info("Balance Jumps:")
                balance_jumps = metrics['balance_jumps']
                logger.info(f"  Jump Count: {balance_jumps['balance_jump_count']}")
                logger.info(f"  Max Jump Ratio: {balance_jumps['max_jump_ratio']:.2%}")
                if balance_jumps['jump_positions']:
                    logger.info(f"  Jump Positions: {balance_jumps['jump_positions'][:5]}")  # Show first 5
                logger.info("")

                # Timestamp Anomalies
                logger.info("Timestamp Anomalies:")
                ts_anomalies = metrics['timestamp_anomalies']
                logger.info(f"  Same-second Groups: {ts_anomalies['same_second_groups']}")
                logger.info(f"  Non-chronological: {ts_anomalies['non_chronological_count']}")
                logger.info(f"  Business Hours Ratio: {ts_anomalies['business_hours_ratio']:.2%}")
                logger.info(f"  Weekend Ratio: {ts_anomalies['weekend_ratio']:.2%}")
                logger.info("")

                # Amount Patterns
                logger.info("Amount Patterns:")
                amount_patterns = metrics['amount_patterns']
                logger.info(f"  Round Number Ratio: {amount_patterns['round_number_ratio']:.2%}")
                logger.info(f"  Duplicate Amount Ratio: {amount_patterns['duplicate_amount_ratio']:.2%}")
                logger.info(f"  Benford Score: {amount_patterns['benford_score']:.3f} (closer to 1.0 = more natural)")
                logger.info("")

            except Exception as e:
                logger.error(f"Error processing {run_id}: {e}")
                import traceback
                traceback.print_exc()


if __name__ == '__main__':
    test_on_samples()
