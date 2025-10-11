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

    Args:
        db: Database session
        run_ids: List of run_ids to export (if None, export all)
        acc_number: Filter by account number

    Returns:
        CSV string
    """
    try:
        query = db.query(Summary)

        # Apply filters
        if run_ids:
            query = query.filter(Summary.run_id.in_(run_ids))

        if acc_number:
            query = query.filter(Summary.acc_number == acc_number)

        if acc_prvdr_code:
            query = query.filter(Summary.acc_prvdr_code == acc_prvdr_code)

        # Order by created date
        query = query.order_by(Summary.created_at.desc())

        # Execute query
        summaries = query.all()

        if not summaries:
            logger.warning("No summaries found for export")
            return ""

        # Convert to DataFrame
        data = [summary.to_dict() for summary in summaries]
        df = pd.DataFrame(data)

        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()

        logger.info(f"Exported {len(summaries)} summaries to CSV")
        return csv_string

    except Exception as e:
        logger.error(f"Error exporting summaries: {e}")
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

    Returns:
        Excel file as bytes
    """
    try:
        query = db.query(Summary)

        if run_ids:
            query = query.filter(Summary.run_id.in_(run_ids))

        if acc_number:
            query = query.filter(Summary.acc_number == acc_number)

        if acc_prvdr_code:
            query = query.filter(Summary.acc_prvdr_code == acc_prvdr_code)

        query = query.order_by(Summary.created_at.desc())

        summaries = query.all()

        if not summaries:
            logger.warning("No summaries found for export")
            return b""

        data = [summary.to_dict() for summary in summaries]
        df = pd.DataFrame(data)

        # Convert to Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Summary')

        excel_bytes = excel_buffer.getvalue()

        logger.info(f"Exported {len(summaries)} summaries to Excel")
        return excel_bytes

    except Exception as e:
        logger.error(f"Error exporting summaries to Excel: {e}")
        raise
