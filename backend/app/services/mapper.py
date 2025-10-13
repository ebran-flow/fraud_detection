"""
Mapper Service
Handles loading and caching of mapper.csv data
Maps run_id to acc_number, rm_name, etc.
"""
import pandas as pd
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from ..config import MAPPER_CSV

logger = logging.getLogger(__name__)

# Global cache for mapper data
_mapper_cache: Optional[pd.DataFrame] = None


def load_mapper() -> pd.DataFrame:
    """
    Load mapper.csv file into memory
    Cache it for fast lookups
    """
    global _mapper_cache

    if _mapper_cache is not None:
        logger.debug("Using cached mapper data")
        return _mapper_cache

    try:
        logger.info(f"Loading mapper from: {MAPPER_CSV}")
        _mapper_cache = pd.read_csv(MAPPER_CSV)
        logger.info(f"Loaded {len(_mapper_cache)} mapper records")
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

    Returns:
        Dict with keys: acc_number, rm_name, acc_prvdr_code, etc.
        None if not found
    """
    df = load_mapper()

    if df.empty:
        return None

    match = df[df['run_id'] == run_id]

    if match.empty:
        logger.warning(f"No mapping found for run_id: {run_id}")
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
    Enrich metadata dictionary with data from mapper

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
                # Parse created_date (format: YYYY-MM-DD)
                submitted_date = datetime.strptime(str(mapping['created_date']), '%Y-%m-%d').date()
                metadata['submitted_date'] = submitted_date
            except Exception as e:
                logger.warning(f"Could not parse created_date for run_id {run_id}: {e}")

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
