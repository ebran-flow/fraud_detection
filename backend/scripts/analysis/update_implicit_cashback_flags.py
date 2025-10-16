#!/usr/bin/env python3
"""
Scan all UATL statements and detect implicit fee/commission behavior.
Updates metadata.uses_implicit_cashback and metadata.uses_implicit_ind02_commission columns.
"""
import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.balance_utils import detect_uses_implicit_cashback, detect_uses_implicit_ind02_commission

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')


def scan_and_update_statements():
    """
    Scan all UATL statements and update implicit fee/commission flags
    """

    # Connect to database
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )

    with engine.connect() as conn:
        # Get all UATL statements
        logger.info("Finding UATL statements...")

        result = conn.execute(text("""
            SELECT run_id, acc_number, format
            FROM metadata
            WHERE acc_prvdr_code = 'UATL'
            ORDER BY run_id
        """))

        statements = result.fetchall()
        total = len(statements)

        logger.info(f"Found {total} UATL statements")
        logger.info("Scanning and updating implicit fee/commission flags...")
        logger.info("")

        updated_count = 0
        uses_cashback_count = 0
        no_cashback_count = 0
        uses_ind02_commission_count = 0
        no_ind02_commission_count = 0

        for idx, row in enumerate(statements, 1):
            run_id = row[0]
            acc_number = row[1]
            format_type = row[2]

            # Get transactions for this statement
            txn_result = conn.execute(text("""
                SELECT txn_id, amount, fee, balance, description
                FROM (
                    SELECT txn_id, amount, fee, balance, description
                    FROM uatl_processed_statements
                    WHERE run_id = :run_id
                    UNION ALL
                    SELECT txn_id, amount, fee, balance, description
                    FROM uatl_raw_statements
                    WHERE run_id = :run_id
                ) AS combined
                ORDER BY txn_id
                LIMIT 100
            """), {'run_id': run_id})

            txns = []
            for txn_row in txn_result:
                txns.append({
                    'txn_id': txn_row[0],
                    'amount': float(txn_row[1]) if txn_row[1] else 0,
                    'fee': float(txn_row[2]) if txn_row[2] else 0,
                    'balance': float(txn_row[3]) if txn_row[3] else 0,
                    'description': txn_row[4] or ''
                })

            if not txns:
                logger.warning(f"[{idx}/{total}] {run_id}: No transactions found")
                continue

            # Detect if uses implicit cashback
            uses_cashback = detect_uses_implicit_cashback(txns, max_test=5)

            # Detect if uses implicit IND02 commission
            uses_ind02_commission = detect_uses_implicit_ind02_commission(txns, max_test=5)

            # Update database
            conn.execute(text("""
                UPDATE metadata
                SET uses_implicit_cashback = :uses_cashback,
                    uses_implicit_ind02_commission = :uses_ind02_commission
                WHERE run_id = :run_id
            """), {
                'uses_cashback': uses_cashback,
                'uses_ind02_commission': uses_ind02_commission,
                'run_id': run_id
            })

            updated_count += 1
            if uses_cashback:
                uses_cashback_count += 1
            else:
                no_cashback_count += 1

            if uses_ind02_commission:
                uses_ind02_commission_count += 1
            else:
                no_ind02_commission_count += 1

            if idx % 100 == 0:
                conn.commit()
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Cashback: {uses_cashback_count}Y/{no_cashback_count}N | IND02: {uses_ind02_commission_count}Y/{no_ind02_commission_count}N")

        conn.commit()

        # Final report
        logger.info("")
        logger.info("=" * 80)
        logger.info("FINAL REPORT - IMPLICIT FEE/COMMISSION DETECTION")
        logger.info("=" * 80)
        logger.info(f"Total statements scanned:         {total}")
        logger.info(f"Updated:                          {updated_count}")
        logger.info("")
        logger.info("MERCHANT PAYMENT CASHBACK (4%):")
        logger.info(f"  Uses implicit cashback:         {uses_cashback_count} ({uses_cashback_count/updated_count*100:.1f}%)")
        logger.info(f"  No implicit cashback:           {no_cashback_count} ({no_cashback_count/updated_count*100:.1f}%)")
        logger.info("")
        logger.info("IND02 COMMISSION (0.5%):")
        logger.info(f"  Uses implicit commission:       {uses_ind02_commission_count} ({uses_ind02_commission_count/updated_count*100:.1f}%)")
        logger.info(f"  No implicit commission:         {no_ind02_commission_count} ({no_ind02_commission_count/updated_count*100:.1f}%)")
        logger.info("=" * 80)


if __name__ == '__main__':
    scan_and_update_statements()
