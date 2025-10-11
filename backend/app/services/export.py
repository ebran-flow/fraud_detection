"""
Export Service
Handles CSV/Excel exports of processed statements and summaries
Supports multi-provider queries
"""
import io
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
import pandas as pd

from ..models.summary import Summary
from ..models.metadata import Metadata
from . import crud_v2 as crud
from .provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


def export_processed_statements_csv(
    db: Session,
    run_ids: Optional[List[str]] = None,
    acc_number: Optional[str] = None,
    acc_prvdr_code: Optional[str] = None,
) -> str:
    """
    Export processed statements to CSV format
    Queries from provider-specific tables

    Args:
        db: Database session
        run_ids: List of run_ids to export (if None, export all)
        acc_number: Filter by account number
        acc_prvdr_code: Filter by provider code

    Returns:
        CSV string
    """
    try:
        all_statements = []

        # Determine which providers to query
        providers_to_query = []
        if acc_prvdr_code:
            # Only query specific provider
            providers_to_query = [acc_prvdr_code]
        else:
            # Query all providers
            providers_to_query = ProviderFactory.get_all_providers()

        # Query each provider
        for provider in providers_to_query:
            try:
                ProcessedModel = ProviderFactory.get_processed_model(provider)

                query = db.query(ProcessedModel)

                # Apply filters
                if run_ids:
                    query = query.filter(ProcessedModel.run_id.in_(run_ids))

                if acc_number:
                    query = query.filter(ProcessedModel.acc_number == acc_number)

                # Order by date
                query = query.order_by(ProcessedModel.run_id, ProcessedModel.txn_date)

                # Execute query
                statements = query.all()

                # Convert to dicts and add provider code
                for stmt in statements:
                    stmt_dict = {c.name: getattr(stmt, c.name) for c in stmt.__table__.columns}
                    stmt_dict['acc_prvdr_code'] = provider
                    all_statements.append(stmt_dict)

            except Exception as e:
                logger.warning(f"Error querying {provider} processed statements: {e}")
                continue

        if not all_statements:
            logger.warning("No processed statements found for export")
            return ""

        # Convert to DataFrame
        df = pd.DataFrame(all_statements)

        # Sort by run_id and txn_date
        if 'run_id' in df.columns and 'txn_date' in df.columns:
            df = df.sort_values(['run_id', 'txn_date'])

        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()

        logger.info(f"Exported {len(all_statements)} processed statements to CSV")
        return csv_string

    except Exception as e:
        logger.error(f"Error exporting processed statements: {e}")
        raise


def export_summary_csv(
    db: Session,
    run_ids: Optional[List[str]] = None,
    acc_number: Optional[str] = None,
    acc_prvdr_code: Optional[str] = None,
) -> str:
    """
    Export summary data to CSV format
    Uses unified_statements view to include both IMPORTED and PROCESSED statements

    Args:
        db: Database session
        run_ids: List of run_ids to export (if None, export all)
        acc_number: Filter by account number
        acc_prvdr_code: Provider code filter

    Returns:
        CSV string
    """
    try:
        from sqlalchemy import text

        # Build WHERE clause
        where_clauses = []
        if run_ids:
            run_ids_str = "','".join(run_ids)
            where_clauses.append(f"run_id IN ('{run_ids_str}')")
        if acc_number:
            where_clauses.append(f"acc_number = '{acc_number}'")
        if acc_prvdr_code:
            where_clauses.append(f"acc_prvdr_code = '{acc_prvdr_code}'")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query unified_statements view
        query = f"""
            SELECT
                run_id,
                acc_number,
                acc_prvdr_code,
                rm_name,
                num_rows,
                imported_at,
                processing_status,
                verification_status,
                balance_match,
                duplicate_count,
                processed_at,
                balance_diff_changes,
                balance_diff_change_ratio,
                calculated_closing_balance,
                stmt_closing_balance,
                meta_title,
                meta_author,
                meta_producer,
                meta_created_at,
                meta_modified_at
            FROM unified_statements
            WHERE {where_clause}
            ORDER BY imported_at DESC
        """

        result = db.execute(text(query))
        rows = result.fetchall()

        if not rows:
            logger.warning("No statements found for export")
            return ""

        # Convert to list of dicts
        data = []
        for row in rows:
            data.append({
                'run_id': row[0],
                'acc_number': row[1],
                'acc_prvdr_code': row[2],
                'rm_name': row[3],
                'num_rows': row[4],
                'imported_at': row[5],
                'processing_status': row[6],
                'verification_status': row[7] if row[7] else 'Not Processed',
                'balance_match': row[8] if row[8] else 'N/A',
                'duplicate_count': row[9] if row[9] else 0,
                'processed_at': row[10],
                'balance_diff_changes': row[11] if row[11] is not None else 0,
                'balance_diff_change_ratio': float(row[12]) if row[12] is not None else 0.0,
                'calculated_closing_balance': float(row[13]) if row[13] is not None else 0.0,
                'stmt_closing_balance': float(row[14]) if row[14] is not None else 0.0,
                'meta_title': row[15] if row[15] else 'N/A',
                'meta_author': row[16] if row[16] else 'N/A',
                'meta_producer': row[17] if row[17] else 'N/A',
                'meta_created_at': row[18],
                'meta_modified_at': row[19]
            })

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()

        logger.info(f"Exported {len(data)} statements to summary CSV")
        return csv_string

    except Exception as e:
        logger.error(f"Error exporting summary: {e}")
        raise


def export_processed_statements_excel(
    db: Session,
    run_ids: Optional[List[str]] = None,
    acc_number: Optional[str] = None,
    acc_prvdr_code: Optional[str] = None,
) -> bytes:
    """
    Export processed statements to Excel format
    Queries from provider-specific tables

    Returns:
        Excel file as bytes
    """
    try:
        all_statements = []

        # Determine which providers to query
        providers_to_query = []
        if acc_prvdr_code:
            providers_to_query = [acc_prvdr_code]
        else:
            providers_to_query = ProviderFactory.get_all_providers()

        # Query each provider
        for provider in providers_to_query:
            try:
                ProcessedModel = ProviderFactory.get_processed_model(provider)

                query = db.query(ProcessedModel)

                if run_ids:
                    query = query.filter(ProcessedModel.run_id.in_(run_ids))

                if acc_number:
                    query = query.filter(ProcessedModel.acc_number == acc_number)

                query = query.order_by(ProcessedModel.run_id, ProcessedModel.txn_date)

                statements = query.all()

                # Convert to dicts and add provider code
                for stmt in statements:
                    stmt_dict = {c.name: getattr(stmt, c.name) for c in stmt.__table__.columns}
                    stmt_dict['acc_prvdr_code'] = provider
                    all_statements.append(stmt_dict)

            except Exception as e:
                logger.warning(f"Error querying {provider} processed statements: {e}")
                continue

        if not all_statements:
            logger.warning("No processed statements found for export")
            return b""

        df = pd.DataFrame(all_statements)

        # Sort by run_id and txn_date
        if 'run_id' in df.columns and 'txn_date' in df.columns:
            df = df.sort_values(['run_id', 'txn_date'])

        # Convert to Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Processed Statements')

        excel_bytes = excel_buffer.getvalue()

        logger.info(f"Exported {len(all_statements)} processed statements to Excel")
        return excel_bytes

    except Exception as e:
        logger.error(f"Error exporting processed statements to Excel: {e}")
        raise


def export_summary_excel(
    db: Session,
    run_ids: Optional[List[str]] = None,
    acc_number: Optional[str] = None,
    acc_prvdr_code: Optional[str] = None,
) -> bytes:
    """
    Export summary data to Excel format
    Uses unified_statements view to include both IMPORTED and PROCESSED statements

    Returns:
        Excel file as bytes
    """
    try:
        from sqlalchemy import text

        # Build WHERE clause
        where_clauses = []
        if run_ids:
            run_ids_str = "','".join(run_ids)
            where_clauses.append(f"run_id IN ('{run_ids_str}')")
        if acc_number:
            where_clauses.append(f"acc_number = '{acc_number}'")
        if acc_prvdr_code:
            where_clauses.append(f"acc_prvdr_code = '{acc_prvdr_code}'")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query unified_statements view
        query = f"""
            SELECT
                run_id,
                acc_number,
                acc_prvdr_code,
                rm_name,
                num_rows,
                imported_at,
                processing_status,
                verification_status,
                balance_match,
                duplicate_count,
                processed_at,
                balance_diff_changes,
                balance_diff_change_ratio,
                calculated_closing_balance,
                stmt_closing_balance,
                meta_title,
                meta_author,
                meta_producer,
                meta_created_at,
                meta_modified_at
            FROM unified_statements
            WHERE {where_clause}
            ORDER BY imported_at DESC
        """

        result = db.execute(text(query))
        rows = result.fetchall()

        if not rows:
            logger.warning("No statements found for export")
            return b""

        # Convert to list of dicts
        data = []
        for row in rows:
            data.append({
                'run_id': row[0],
                'acc_number': row[1],
                'acc_prvdr_code': row[2],
                'rm_name': row[3],
                'num_rows': row[4],
                'imported_at': row[5],
                'processing_status': row[6],
                'verification_status': row[7] if row[7] else 'Not Processed',
                'balance_match': row[8] if row[8] else 'N/A',
                'duplicate_count': row[9] if row[9] else 0,
                'processed_at': row[10],
                'balance_diff_changes': row[11] if row[11] is not None else 0,
                'balance_diff_change_ratio': float(row[12]) if row[12] is not None else 0.0,
                'calculated_closing_balance': float(row[13]) if row[13] is not None else 0.0,
                'stmt_closing_balance': float(row[14]) if row[14] is not None else 0.0,
                'meta_title': row[15] if row[15] else 'N/A',
                'meta_author': row[16] if row[16] else 'N/A',
                'meta_producer': row[17] if row[17] else 'N/A',
                'meta_created_at': row[18],
                'meta_modified_at': row[19]
            })

        df = pd.DataFrame(data)

        # Convert to Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Summary')

        excel_bytes = excel_buffer.getvalue()

        logger.info(f"Exported {len(data)} statements to summary Excel")
        return excel_bytes

    except Exception as e:
        logger.error(f"Error exporting summary to Excel: {e}")
        raise
