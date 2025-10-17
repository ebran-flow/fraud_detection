"""
Customer Details Service
Handles fetching and caching customer details from FLOW_API
Replaces mapper.csv approach with customer_details table
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os

logger = logging.getLogger(__name__)

# Database engines (lazy initialization)
_fraud_db_engine = None
_flow_db_engine = None


def get_fraud_db_engine():
    """Get or create fraud_detection database engine."""
    global _fraud_db_engine
    if _fraud_db_engine is None:
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PASSWORD')
        DB_HOST = os.getenv('DB_HOST')
        DB_PORT = os.getenv('DB_PORT', '3306')
        DB_NAME = os.getenv('DB_NAME')

        _fraud_db_engine = create_engine(
            f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
            pool_pre_ping=True,
            pool_recycle=3600
        )
    return _fraud_db_engine


def get_flow_db_engine():
    """Get or create flow_api database engine."""
    global _flow_db_engine
    if _flow_db_engine is None:
        FLOW_DB_USER = os.getenv('FLOW_DB_USER')
        FLOW_DB_PASSWORD = os.getenv('FLOW_DB_PASSWORD')
        FLOW_DB_HOST = os.getenv('FLOW_DB_HOST')
        FLOW_DB_PORT = os.getenv('FLOW_DB_PORT', '3306')
        FLOW_DB_NAME = os.getenv('FLOW_DB_NAME')

        _flow_db_engine = create_engine(
            f'mysql+pymysql://{FLOW_DB_USER}:{FLOW_DB_PASSWORD}@{FLOW_DB_HOST}:{FLOW_DB_PORT}/{FLOW_DB_NAME}',
            pool_pre_ping=True,
            pool_recycle=3600
        )
    return _flow_db_engine


def convert_to_db_value(value):
    """Convert values to database-compatible format."""
    if value is None:
        return None
    if isinstance(value, (datetime, Decimal)):
        return value
    if isinstance(value, str):
        return value if value.strip() != '' else None
    return value


def get_customer_details_by_run_id(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get customer details for a specific run_id from customer_details table.

    Args:
        run_id: flow_req_id from partner_acc_stmt_requests

    Returns:
        Dict with customer details or None if not found
    """
    try:
        engine = get_fraud_db_engine()

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM customer_details WHERE run_id = :run_id LIMIT 1"),
                {'run_id': run_id}
            )
            row = result.fetchone()

            if row is None:
                logger.debug(f"No customer details found for run_id: {run_id}")
                return None

            # Convert row to dict
            return dict(row._mapping)

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching customer details for run_id {run_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching customer details for run_id {run_id}: {e}")
        return None


def fetch_customer_details_from_flow_api(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch customer details from FLOW_API for a specific run_id.

    This mirrors the query from export_customer_details.py but for a single run_id.

    Args:
        run_id: flow_req_id from partner_acc_stmt_requests

    Returns:
        Dict with customer details or None if not found
    """
    try:
        engine = get_flow_db_engine()

        query = text("""
            -- CTE 1: Get statement request
            WITH stmt_request AS (
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
                WHERE s.flow_req_id = :run_id
                LIMIT 1
            ),

            -- CTE 2: Resolve final entity
            final_entity AS (
                SELECT
                    sr.id AS stmt_request_id,
                    sr.flow_req_id AS run_id,
                    sr.acc_number,
                    sr.alt_acc_num,
                    sr.acc_prvdr_code,
                    sr.status AS stmt_status,
                    sr.object_key,
                    sr.lambda_status,
                    DATE(sr.created_at) AS created_date,
                    sr.created_at,
                    sr.created_by,
                    sr.entity AS direct_entity,
                    sr.entity_id AS direct_entity_id,

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
                        WHEN sr.entity = 'customer_statement' THEN cs.entity
                        ELSE sr.entity
                    END AS final_entity_type,

                    CASE
                        WHEN sr.entity = 'customer_statement' THEN CAST(cs.entity_id AS UNSIGNED)
                        ELSE sr.entity_id
                    END AS final_entity_id

                FROM stmt_request sr
                LEFT JOIN customer_statements cs
                    ON sr.entity = 'customer_statement' AND cs.id = sr.entity_id
            ),

            -- CTE 3: RM details
            rm_details AS (
                SELECT
                    fe.stmt_request_id,
                    p.id AS rm_id,
                    CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) AS rm_name
                FROM final_entity fe
                LEFT JOIN persons p ON p.id = fe.created_by
            ),

            -- CTE 4: Lead details
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
                FROM final_entity fe
                INNER JOIN leads l ON fe.final_entity_type = 'lead' AND l.id = fe.final_entity_id
            ),

            -- CTE 5: Reassessment details
            reassessment_details AS (
                SELECT
                    fe.stmt_request_id,
                    rr.id AS reassessment_id,
                    rr.cust_id,
                    rr.prev_limit AS rr_prev_limit,
                    rr.status AS rr_status,
                    rr.type AS rr_type,
                    rr.created_at AS rr_created_at
                FROM final_entity fe
                INNER JOIN reassessment_results rr
                    ON fe.final_entity_type = 'reassessment_result' AND rr.id = fe.final_entity_id
            ),

            -- CTE 6: Borrower details
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

                FROM final_entity fe
                INNER JOIN borrowers b
                    ON COALESCE(
                        (SELECT l.cust_id FROM lead_details l WHERE l.stmt_request_id = fe.stmt_request_id),
                        (SELECT r.cust_id FROM reassessment_details r WHERE r.stmt_request_id = fe.stmt_request_id)
                    ) = b.cust_id
                LEFT JOIN persons reg_rm ON reg_rm.id = b.reg_flow_rel_mgr_id
                LEFT JOIN persons curr_rm ON curr_rm.id = b.flow_rel_mgr_id
            )

            -- Final SELECT
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
                rm.rm_id,
                rm.rm_name,
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
                fe.final_entity_type,
                fe.final_entity_id,
                COALESCE(ld.cust_id, rd.cust_id) AS cust_id,
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
                rd.reassessment_id,
                rd.rr_prev_limit,
                rd.rr_status,
                rd.rr_type,
                rd.rr_created_at,
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
                bd.reg_rm_id,
                bd.reg_rm_name,
                bd.current_rm_id,
                bd.current_rm_name
            FROM final_entity fe
            LEFT JOIN rm_details rm ON rm.stmt_request_id = fe.stmt_request_id
            LEFT JOIN lead_details ld ON ld.stmt_request_id = fe.stmt_request_id
            LEFT JOIN reassessment_details rd ON rd.stmt_request_id = fe.stmt_request_id
            LEFT JOIN borrower_details bd ON bd.stmt_request_id = fe.stmt_request_id
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {'run_id': run_id})
            row = result.fetchone()

            if row is None:
                logger.warning(f"No data found in FLOW_API for run_id: {run_id}")
                return None

            # Convert row to dict
            return dict(row._mapping)

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching from FLOW_API for run_id {run_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching from FLOW_API for run_id {run_id}: {e}")
        return None


def store_customer_details(details: Dict[str, Any]) -> bool:
    """
    Store customer details in customer_details table.

    Args:
        details: Dict with customer details (from fetch_customer_details_from_flow_api)

    Returns:
        True if successful, False otherwise
    """
    try:
        engine = get_fraud_db_engine()

        # Add sync timestamp
        details['synced_at'] = datetime.now()

        # Build column list (exclude None values for cleaner insertion)
        columns = [k for k, v in details.items() if v is not None]
        placeholders = ', '.join([f':{col}' for col in columns])
        column_names = ', '.join([f'`{col}`' for col in columns])

        query = text(f"""
            REPLACE INTO customer_details ({column_names})
            VALUES ({placeholders})
        """)

        with engine.connect() as conn:
            conn.execute(query, details)
            conn.commit()

        logger.info(f"Stored customer details for run_id: {details.get('run_id')}")
        return True

    except SQLAlchemyError as e:
        logger.error(f"Database error storing customer details: {e}")
        return False
    except Exception as e:
        logger.error(f"Error storing customer details: {e}")
        return False


def get_or_fetch_customer_details(run_id: str, fetch_if_missing: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get customer details from local table, or fetch from FLOW_API if missing.

    This is the main function to use in the import pipeline.

    Args:
        run_id: flow_req_id from partner_acc_stmt_requests
        fetch_if_missing: If True, fetch from FLOW_API if not in local table

    Returns:
        Dict with customer details or None
    """
    # Try local table first
    details = get_customer_details_by_run_id(run_id)

    if details is not None:
        logger.debug(f"Found customer details in local table for run_id: {run_id}")
        return details

    # If not found and fetch_if_missing is True, fetch from FLOW_API
    if fetch_if_missing:
        logger.info(f"Fetching customer details from FLOW_API for run_id: {run_id}")
        details = fetch_customer_details_from_flow_api(run_id)

        if details is not None:
            # Store in local table for future use
            store_customer_details(details)
            return details

    logger.warning(f"Could not find customer details for run_id: {run_id}")
    return None


def enrich_metadata_with_customer_details(metadata: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    """
    Enrich metadata dictionary with customer details.

    This replaces enrich_metadata_with_mapper() from mapper.py.

    Args:
        metadata: Metadata dict (from parser)
        run_id: Run ID to lookup

    Returns:
        Enriched metadata dict
    """
    details = get_or_fetch_customer_details(run_id, fetch_if_missing=True)

    if details:
        # Enrich with basic fields
        metadata['rm_name'] = details.get('rm_name', metadata.get('rm_name'))
        metadata['acc_prvdr_code'] = details.get('acc_prvdr_code', metadata.get('acc_prvdr_code'))

        # Account number
        if details.get('acc_number'):
            metadata['acc_number'] = details['acc_number']

        # Submitted date from created_date
        if details.get('created_date'):
            metadata['submitted_date'] = details['created_date']

        # Add customer ID if available
        if details.get('cust_id'):
            metadata['cust_id'] = details['cust_id']

    return metadata


def batch_fetch_and_store(run_ids: List[str]) -> int:
    """
    Batch fetch customer details for multiple run_ids.

    Args:
        run_ids: List of run_ids to fetch

    Returns:
        Number of successfully stored records
    """
    count = 0

    for run_id in run_ids:
        details = get_or_fetch_customer_details(run_id, fetch_if_missing=True)
        if details:
            count += 1

    logger.info(f"Batch fetched and stored {count}/{len(run_ids)} customer details")
    return count
