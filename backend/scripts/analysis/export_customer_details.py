#!/usr/bin/env python3
"""
Export Customer Details for All Statements

This script retrieves customer information for all statement requests by following
the entity relationship chain:
- partner_acc_stmt_requests → entity/entity_id
- customer_statements (if applicable) → entity/entity_id
- leads or reassessment_results → cust_id

Usage:
    python scripts/analysis/export_customer_details.py --output customer_details.csv
    python scripts/analysis/export_customer_details.py --output customer_details.csv --format json
"""

import sys
import os
import argparse
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Setup paths
load_dotenv(Path(__file__).parent.parent.parent / '.env')
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_customer_details(engine, cutoff_date='2025-10-10 19:07:24', max_id=30668):
    """
    Retrieve customer details for all statements by following entity relationships.

    Args:
        engine: SQLAlchemy engine
        cutoff_date: Maximum created_at timestamp
        max_id: Maximum statement request ID

    Returns:
        pandas DataFrame with customer details
    """
    query = text("""
        SELECT
            -- Statement request details
            s.id AS stmt_request_id,
            s.flow_req_id AS run_id,
            s.acc_number,
            s.alt_acc_num,
            s.acc_prvdr_code,
            s.status AS stmt_status,
            s.object_key,
            s.lambda_status,
            DATE(s.created_at) AS created_date,
            s.created_at,

            -- RM details
            p.id AS rm_id,
            CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) AS rm_name,

            -- Entity information (direct from statement request)
            s.entity AS direct_entity,
            s.entity_id AS direct_entity_id,

            -- Customer statement details (if entity = 'customer_statement')
            cs.id AS customer_statement_id,
            cs.entity AS cs_entity,
            cs.entity_id AS cs_entity_id,
            cs.holder_name,
            cs.distributor_code,
            cs.acc_ownership,
            cs.status AS cs_status,
            cs.result AS cs_result,
            cs.score AS cs_score,
            cs.`limit` AS cs_limit,
            cs.prev_limit AS cs_prev_limit,
            cs.assessment_date AS cs_assessment_date,

            -- Final entity type (either direct or from customer_statement)
            CASE
                WHEN s.entity = 'customer_statement' THEN cs.entity
                ELSE s.entity
            END AS final_entity_type,

            -- Final entity ID (either direct or from customer_statement)
            CASE
                WHEN s.entity = 'customer_statement' THEN cs.entity_id
                ELSE s.entity_id
            END AS final_entity_id,

            -- Customer ID (from leads or reassessment_results)
            COALESCE(
                l.cust_id,
                rr.cust_id
            ) AS cust_id,

            -- Lead details (if final entity = 'lead')
            l.id AS lead_id,
            l.mobile_num AS lead_mobile,
            l.biz_name AS lead_biz_name,
            l.first_name AS lead_first_name,
            l.last_name AS lead_last_name,
            l.id_proof_num AS lead_id_proof,
            l.national_id AS lead_national_id,
            l.location AS lead_location,
            l.territory AS lead_territory,
            l.status AS lead_status,
            l.profile_status AS lead_profile_status,
            l.score_status AS lead_score_status,
            l.type AS lead_type,
            l.lead_date,
            l.assessment_date AS lead_assessment_date,
            l.onboarded_date AS lead_onboarded_date,

            -- Reassessment result details (if final entity = 'reassessment_result')
            rr.id AS reassessment_id,
            rr.prev_limit AS rr_prev_limit,
            rr.status AS rr_status,
            rr.type AS rr_type,
            rr.created_at AS rr_created_at

        FROM partner_acc_stmt_requests s

        -- Filter early with WHERE conditions
        WHERE
            s.acc_prvdr_code IN ('UMTN', 'UATL')
            AND s.created_at <= :cutoff_date
            AND s.id <= :max_id

        -- Join RM details
        LEFT JOIN persons p ON p.id = s.created_by

        -- Join customer_statement only when entity = 'customer_statement'
        LEFT JOIN customer_statements cs
            ON cs.id = s.entity_id
            WHERE s.entity = 'customer_statement'

        -- Join leads with optimized conditions
        LEFT JOIN leads l
            ON (
                -- Direct link
                (s.entity = 'lead' AND l.id = s.entity_id)
                OR
                -- Indirect link through customer_statement
                (cs.id IS NOT NULL AND cs.entity = 'lead' AND l.id = CAST(cs.entity_id AS UNSIGNED))
            )

        -- Join reassessment_results with optimized conditions
        LEFT JOIN reassessment_results rr
            ON (
                -- Direct link
                (s.entity = 'reassessment_result' AND rr.id = s.entity_id)
                OR
                -- Indirect link through customer_statement
                (cs.id IS NOT NULL AND cs.entity = 'reassessment_result' AND rr.id = CAST(cs.entity_id AS UNSIGNED))
            )

        ORDER BY s.created_at DESC
    """)

    logger.info(f"Executing query with cutoff_date={cutoff_date}, max_id={max_id}")

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'cutoff_date': cutoff_date, 'max_id': max_id})

    logger.info(f"Retrieved {len(df):,} statement records")

    return df


def analyze_entity_distribution(df):
    """Analyze and report on entity type distribution."""
    logger.info("\n" + "=" * 80)
    logger.info("ENTITY DISTRIBUTION ANALYSIS")
    logger.info("=" * 80)

    # Direct entity distribution
    logger.info("\nDirect Entity Types (from partner_acc_stmt_requests):")
    direct_dist = df['direct_entity'].value_counts()
    for entity, count in direct_dist.items():
        logger.info(f"  {entity}: {count:,} ({count/len(df)*100:.1f}%)")

    # Final entity distribution
    logger.info("\nFinal Entity Types (after resolving customer_statement):")
    final_dist = df['final_entity_type'].value_counts()
    for entity, count in final_dist.items():
        logger.info(f"  {entity}: {count:,} ({count/len(df)*100:.1f}%)")

    # Customer ID coverage
    cust_id_count = df['cust_id'].notna().sum()
    logger.info(f"\nCustomer ID Coverage:")
    logger.info(f"  With cust_id: {cust_id_count:,} ({cust_id_count/len(df)*100:.1f}%)")
    logger.info(f"  Without cust_id: {len(df) - cust_id_count:,} ({(len(df) - cust_id_count)/len(df)*100:.1f}%)")

    # Provider distribution
    logger.info(f"\nProvider Distribution:")
    provider_dist = df['acc_prvdr_code'].value_counts()
    for provider, count in provider_dist.items():
        logger.info(f"  {provider}: {count:,} ({count/len(df)*100:.1f}%)")


def export_to_csv(df, output_path):
    """Export DataFrame to CSV."""
    df.to_csv(output_path, index=False)
    logger.info(f"\n✓ Exported {len(df):,} records to {output_path}")
    logger.info(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")


def export_to_json(df, output_path):
    """Export DataFrame to JSON."""
    df.to_json(output_path, orient='records', date_format='iso', indent=2)
    logger.info(f"\n✓ Exported {len(df):,} records to {output_path}")
    logger.info(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description='Export customer details for all statement requests',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--output', '-o', type=str, default='customer_details.csv',
                       help='Output file path (default: customer_details.csv)')
    parser.add_argument('--format', '-f', type=str, choices=['csv', 'json'], default='csv',
                       help='Output format (default: csv)')
    parser.add_argument('--cutoff-date', type=str, default='2025-10-10 19:07:24',
                       help='Maximum created_at timestamp (default: 2025-10-10 19:07:24)')
    parser.add_argument('--max-id', type=int, default=30668,
                       help='Maximum statement request ID (default: 30668)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze entity distribution without exporting')

    args = parser.parse_args()

    # Database connection - Flow API database
    FLOW_DB_USER = os.getenv('FLOW_DB_USER')
    FLOW_DB_PASSWORD = os.getenv('FLOW_DB_PASSWORD')
    FLOW_DB_HOST = os.getenv('FLOW_DB_HOST')
    FLOW_DB_PORT = os.getenv('FLOW_DB_PORT', '3306')
    FLOW_DB_NAME = os.getenv('FLOW_DB_NAME')

    engine = create_engine(
        f'mysql+pymysql://{FLOW_DB_USER}:{FLOW_DB_PASSWORD}@{FLOW_DB_HOST}:{FLOW_DB_PORT}/{FLOW_DB_NAME}'
    )

    logger.info("=" * 80)
    logger.info("CUSTOMER DETAILS EXPORT")
    logger.info("=" * 80)

    # Retrieve data
    df = get_customer_details(engine, args.cutoff_date, args.max_id)

    # Analyze entity distribution
    analyze_entity_distribution(df)

    if not args.analyze_only:
        # Export
        if args.format == 'csv':
            export_to_csv(df, args.output)
        else:
            export_to_json(df, args.output)

        logger.info("\n" + "=" * 80)
        logger.info("EXPORT COMPLETE")
        logger.info("=" * 80)

    return 0


if __name__ == '__main__':
    exit(main())
