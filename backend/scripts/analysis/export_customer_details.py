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
        -- CTE 1: Filter statement requests early
        WITH filtered_statements AS (
            SELECT
                s.id,
                s.flow_req_id,
                s.acc_number,
                s.alt_acc_num,
                s.acc_prvdr_code,
                s.status,
                s.object_key,
                s.lambda_status,
                s.created_at,
                s.entity,
                s.entity_id,
                s.created_by
            FROM partner_acc_stmt_requests s
            WHERE s.acc_prvdr_code IN ('UMTN', 'UATL')
                AND s.created_at <= :cutoff_date
                AND s.id <= :max_id
        ),

        -- CTE 2: Resolve final entity (handle customer_statement intermediate)
        final_entities AS (
            SELECT
                fs.id AS stmt_request_id,
                fs.flow_req_id AS run_id,
                fs.acc_number,
                fs.alt_acc_num,
                fs.acc_prvdr_code,
                fs.status AS stmt_status,
                fs.object_key,
                fs.lambda_status,
                DATE(fs.created_at) AS created_date,
                fs.created_at,
                fs.created_by,
                fs.entity AS direct_entity,
                fs.entity_id AS direct_entity_id,

                -- Customer statement details
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

                -- Final resolved entity
                CASE
                    WHEN fs.entity = 'customer_statement' THEN cs.entity
                    ELSE fs.entity
                END AS final_entity_type,

                CASE
                    WHEN fs.entity = 'customer_statement' THEN CAST(cs.entity_id AS UNSIGNED)
                    ELSE fs.entity_id
                END AS final_entity_id

            FROM filtered_statements fs
            LEFT JOIN customer_statements cs
                ON fs.entity = 'customer_statement' AND cs.id = fs.entity_id
        ),

        -- CTE 3: Get lead details only for lead entities
        lead_details AS (
            SELECT
                fe.stmt_request_id,
                l.id AS lead_id,
                l.cust_id,
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
                l.onboarded_date AS lead_onboarded_date
            FROM final_entities fe
            INNER JOIN leads l ON fe.final_entity_type = 'lead' AND l.id = fe.final_entity_id
        ),

        -- CTE 4: Get reassessment details only for reassessment entities
        reassessment_details AS (
            SELECT
                fe.stmt_request_id,
                rr.id AS reassessment_id,
                rr.cust_id,
                rr.prev_limit AS rr_prev_limit,
                rr.status AS rr_status,
                rr.type AS rr_type,
                rr.created_at AS rr_created_at
            FROM final_entities fe
            INNER JOIN reassessment_results rr
                ON fe.final_entity_type = 'reassessment_result' AND rr.id = fe.final_entity_id
        ),

        -- CTE 5: Get RM details (statement request creator)
        rm_details AS (
            SELECT
                fe.stmt_request_id,
                p.id AS rm_id,
                CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) AS rm_name
            FROM final_entities fe
            LEFT JOIN persons p ON p.id = fe.created_by
        ),

        -- CTE 6: Get borrower details
        borrower_details AS (
            SELECT
                fe.stmt_request_id,
                b.id AS borrower_id,
                b.cust_id AS borrower_cust_id,
                b.biz_name AS borrower_biz_name,
                b.reg_date AS borrower_reg_date,
                b.tot_loans,
                b.tot_default_loans,
                b.crnt_fa_limit,
                b.prev_fa_limit,
                b.last_assessment_date,
                b.kyc_status,
                b.activity_status,
                b.profile_status,
                b.fa_status,
                b.status AS borrower_status,
                b.risk_category,
                b.reg_flow_rel_mgr_id,
                b.flow_rel_mgr_id,

                -- Registered RM
                reg_rm.id AS reg_rm_id,
                CONCAT_WS(' ', reg_rm.first_name, reg_rm.middle_name, reg_rm.last_name) AS reg_rm_name,

                -- Current RM
                curr_rm.id AS current_rm_id,
                CONCAT_WS(' ', curr_rm.first_name, curr_rm.middle_name, curr_rm.last_name) AS current_rm_name

            FROM final_entities fe
            INNER JOIN borrowers b
                ON COALESCE(
                    (SELECT l.cust_id FROM lead_details l WHERE l.stmt_request_id = fe.stmt_request_id),
                    (SELECT r.cust_id FROM reassessment_details r WHERE r.stmt_request_id = fe.stmt_request_id)
                ) = b.cust_id
            LEFT JOIN persons reg_rm ON reg_rm.id = b.reg_flow_rel_mgr_id
            LEFT JOIN persons curr_rm ON curr_rm.id = b.flow_rel_mgr_id
        )

        -- Final SELECT: Join all CTEs together
        SELECT
            fe.stmt_request_id,
            fe.run_id,
            fe.acc_number,
            fe.alt_acc_num,
            fe.acc_prvdr_code,
            fe.stmt_status,
            fe.object_key,
            fe.lambda_status,
            fe.created_date,
            fe.created_at,

            -- RM details
            rm.rm_id,
            rm.rm_name,

            -- Entity chain
            fe.direct_entity,
            fe.direct_entity_id,
            fe.customer_statement_id,
            fe.cs_entity,
            fe.cs_entity_id,
            fe.holder_name,
            fe.distributor_code,
            fe.acc_ownership,
            fe.cs_status,
            fe.cs_result,
            fe.cs_score,
            fe.cs_limit,
            fe.cs_prev_limit,
            fe.cs_assessment_date,

            -- Final entity
            fe.final_entity_type,
            fe.final_entity_id,

            -- Customer ID
            COALESCE(ld.cust_id, rd.cust_id) AS cust_id,

            -- Lead details
            ld.lead_id,
            ld.lead_mobile,
            ld.lead_biz_name,
            ld.lead_first_name,
            ld.lead_last_name,
            ld.lead_id_proof,
            ld.lead_national_id,
            ld.lead_location,
            ld.lead_territory,
            ld.lead_status,
            ld.lead_profile_status,
            ld.lead_score_status,
            ld.lead_type,
            ld.lead_date,
            ld.lead_assessment_date,
            ld.lead_onboarded_date,

            -- Reassessment details
            rd.reassessment_id,
            rd.rr_prev_limit,
            rd.rr_status,
            rd.rr_type,
            rd.rr_created_at,

            -- Borrower details
            bd.borrower_id,
            bd.borrower_cust_id,
            bd.borrower_biz_name,
            bd.borrower_reg_date,
            bd.tot_loans,
            bd.tot_default_loans,
            bd.crnt_fa_limit,
            bd.prev_fa_limit,
            bd.last_assessment_date AS borrower_last_assessment_date,
            bd.kyc_status AS borrower_kyc_status,
            bd.activity_status AS borrower_activity_status,
            bd.profile_status AS borrower_profile_status,
            bd.fa_status AS borrower_fa_status,
            bd.borrower_status,
            bd.risk_category,

            -- Borrower RMs
            bd.reg_rm_id,
            bd.reg_rm_name,
            bd.current_rm_id,
            bd.current_rm_name

        FROM final_entities fe
        LEFT JOIN rm_details rm ON rm.stmt_request_id = fe.stmt_request_id
        LEFT JOIN lead_details ld ON ld.stmt_request_id = fe.stmt_request_id
        LEFT JOIN reassessment_details rd ON rd.stmt_request_id = fe.stmt_request_id
        LEFT JOIN borrower_details bd ON bd.stmt_request_id = fe.stmt_request_id

        ORDER BY fe.created_at DESC
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
