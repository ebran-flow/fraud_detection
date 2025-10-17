"""
Mapper Service
Handles loading and caching of mapper.csv data AND customer_details table
Maps run_id to acc_number, rm_name, etc.

NOTE: This module now primarily uses customer_details table with mapper.csv as fallback.
"""
import pandas as pd
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from ..config import MAPPER_CSV

logger = logging.getLogger(__name__)

# Global cache for mapper data (legacy CSV)
_mapper_cache: Optional[pd.DataFrame] = None

# Flag to control whether to use customer_details table
USE_CUSTOMER_DETAILS_TABLE = True


def load_mapper() -> pd.DataFrame:
    """
    Load mapper.csv file into memory (legacy support)
    Cache it for fast lookups

    NOTE: This is now a fallback. Primary source is customer_details table.
    """
    global _mapper_cache

    if _mapper_cache is not None:
        logger.debug("Using cached mapper data")
        return _mapper_cache

    try:
        logger.info(f"Loading mapper from: {MAPPER_CSV}")
        _mapper_cache = pd.read_csv(MAPPER_CSV)
        logger.info(f"Loaded {len(_mapper_cache)} mapper records (legacy CSV)")
        return _mapper_cache
    except FileNotFoundError:
        logger.debug(f"Mapper CSV not found (optional): {MAPPER_CSV}")
        # Return empty dataframe if file doesn't exist - this is optional
        return pd.DataFrame()
    except Exception as e:
        logger.warning(f"Error loading mapper CSV: {e}")
        # Return empty dataframe on any error
        return pd.DataFrame()


def reload_mapper() -> int:
    """
    Force reload of mapper.csv
    Returns number of records loaded
    """
    global _mapper_cache
    _mapper_cache = None
    df = load_mapper()
    return len(df)


def get_mapping_by_run_id(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get mapping data for a specific run_id

    Now uses customer_details table as primary source with CSV as fallback.

    Returns:
        Dict with keys: acc_number, rm_name, acc_prvdr_code, etc.
        None if not found
    """
    # Try customer_details table first if enabled
    if USE_CUSTOMER_DETAILS_TABLE:
        try:
            from .customer_details import get_customer_details_by_run_id
            details = get_customer_details_by_run_id(run_id)

            if details:
                # Convert to mapper format
                return {
                    'run_id': details.get('run_id'),
                    'acc_number': details.get('acc_number'),
                    'rm_name': details.get('rm_name'),
                    'acc_prvdr_code': details.get('acc_prvdr_code', 'UATL'),
                    'status': details.get('stmt_status'),
                    'lambda_status': details.get('lambda_status'),
                    'created_date': details.get('created_date'),
                    # Additional fields available from customer_details
                    'cust_id': details.get('cust_id'),
                    'borrower_biz_name': details.get('borrower_biz_name'),
                }
        except Exception as e:
            logger.warning(f"Error fetching from customer_details table: {e}")
            # Fall through to CSV

    # Fallback to CSV
    df = load_mapper()

    if df.empty:
        return None

    match = df[df['run_id'] == run_id]

    if match.empty:
        logger.warning(f"No mapping found for run_id: {run_id} (checked both table and CSV)")
        return None

    row = match.iloc[0]

    # Helper function to convert pandas nan to None
    def safe_get(key, default=None):
        val = row.get(key, default)
        # Convert pandas nan to None
        if pd.isna(val):
            return None
        return val

    return {
        'run_id': safe_get('run_id'),
        'acc_number': safe_get('acc_number'),
        'rm_name': safe_get('rm_name'),
        'acc_prvdr_code': safe_get('acc_prvdr_code', 'UATL'),
        'status': safe_get('status'),
        'lambda_status': safe_get('lambda_status'),
        'created_date': safe_get('created_date'),
    }


def get_mapping_by_acc_number(acc_number: str) -> Optional[Dict[str, Any]]:
    """
    Get mapping data for a specific account number
    Returns the most recent mapping if multiple exist
    """
    df = load_mapper()

    if df.empty:
        return None

    matches = df[df['acc_number'] == acc_number]

    if matches.empty:
        logger.warning(f"No mapping found for acc_number: {acc_number}")
        return None

    # Return most recent record
    row = matches.iloc[-1]

    # Helper function to convert pandas nan to None
    def safe_get(key, default=None):
        val = row.get(key, default)
        # Convert pandas nan to None
        if pd.isna(val):
            return None
        return val

    return {
        'run_id': safe_get('run_id'),
        'acc_number': safe_get('acc_number'),
        'rm_name': safe_get('rm_name'),
        'acc_prvdr_code': safe_get('acc_prvdr_code', 'UATL'),
        'status': safe_get('status'),
        'lambda_status': safe_get('lambda_status'),
        'created_date': safe_get('created_date'),
    }


def enrich_metadata_with_mapper(metadata: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    """
    Enrich metadata dictionary with data from mapper (table or CSV)

    Now uses customer_details table as primary source with CSV as fallback.

    Args:
        metadata: Metadata dict (from parser)
        run_id: Run ID to lookup

    Returns:
        Enriched metadata dict
    """
    mapping = get_mapping_by_run_id(run_id)

    if mapping:
        # Override with mapper data
        metadata['rm_name'] = mapping.get('rm_name', metadata.get('rm_name'))
        metadata['acc_prvdr_code'] = mapping.get('acc_prvdr_code', metadata.get('acc_prvdr_code'))

        # Account number should match, but use parser's value if mapper is missing
        if mapping.get('acc_number'):
            metadata['acc_number'] = mapping['acc_number']

        # Add submitted_date from created_date
        if mapping.get('created_date'):
            try:
                from datetime import datetime
                # Handle both date and datetime objects
                if isinstance(mapping['created_date'], str):
                    # Parse created_date (format: YYYY-MM-DD)
                    submitted_date = datetime.strptime(str(mapping['created_date']), '%Y-%m-%d').date()
                else:
                    # Already a date object
                    submitted_date = mapping['created_date']
                metadata['submitted_date'] = submitted_date
            except Exception as e:
                logger.warning(f"Could not parse created_date for run_id {run_id}: {e}")

        # Add customer ID if available (from customer_details table)
        if mapping.get('cust_id'):
            metadata['cust_id'] = mapping['cust_id']

    return metadata


def get_all_run_ids() -> list:
    """Get list of all run_ids in mapper"""
    df = load_mapper()
    if df.empty:
        return []
    return df['run_id'].tolist()


def get_all_rm_names() -> list:
    """Get unique list of RM names"""
    df = load_mapper()
    if df.empty:
        return []
    return df['rm_name'].dropna().unique().tolist()
