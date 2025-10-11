"""
Multi-Provider CRUD Service
Uses factory pattern for provider-specific operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from .provider_factory import ProviderFactory
from ..models.metadata import Metadata
from ..models.summary import Summary

logger = logging.getLogger(__name__)


# ===== Provider-Specific CRUD Operations =====

def check_run_id_exists(db: Session, run_id: str, provider_code: str) -> bool:
    """Check if run_id exists for given provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    return db.query(RawModel).filter(RawModel.run_id == run_id).first() is not None


def get_raw_statements_by_run_id(db: Session, run_id: str, provider_code: str):
    """Get raw statements for provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    return db.query(RawModel).filter(RawModel.run_id == run_id).order_by(RawModel.txn_date).all()


def bulk_create_raw(db: Session, provider_code: str, data_list: List[Dict[str, Any]]):
    """Bulk insert raw statements for provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    instances = [RawModel(**data) for data in data_list]
    db.bulk_save_objects(instances, return_defaults=True)
    db.flush()
    return instances


def bulk_create_processed(db: Session, provider_code: str, data_list: List[Dict[str, Any]]):
    """Bulk insert processed statements for provider"""
    ProcessedModel = ProviderFactory.get_processed_model(provider_code)
    instances = [ProcessedModel(**data) for data in data_list]
    db.bulk_save_objects(instances, return_defaults=True)
    db.flush()
    return instances


def get_processed_statements_by_run_id(db: Session, run_id: str, provider_code: str):
    """Get processed statements for provider"""
    ProcessedModel = ProviderFactory.get_processed_model(provider_code)
    return db.query(ProcessedModel).filter(ProcessedModel.run_id == run_id).order_by(ProcessedModel.txn_date).all()


def delete_raw_by_run_id(db: Session, run_id: str, provider_code: str) -> int:
    """Delete raw statements for provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    count = db.query(RawModel).filter(RawModel.run_id == run_id).delete()
    db.flush()
    return count


def delete_processed_by_run_id(db: Session, run_id: str, provider_code: str) -> int:
    """Delete processed statements for provider"""
    ProcessedModel = ProviderFactory.get_processed_model(provider_code)
    count = db.query(ProcessedModel).filter(ProcessedModel.run_id == run_id).delete()
    db.flush()
    return count


# ===== Shared CRUD Operations (Metadata & Summary) =====

def create(db: Session, model, data: Dict[str, Any]):
    """Create a new record (shared tables)"""
    try:
        instance = model(**data)
        db.add(instance)
        db.flush()
        return instance
    except Exception as e:
        logger.error(f"Error creating {model.__name__}: {e}")
        raise


def get_metadata_by_run_id(db: Session, run_id: str) -> Optional[Metadata]:
    """Get metadata for a run_id"""
    return db.query(Metadata).filter(Metadata.run_id == run_id).first()


def get_summary_by_run_id(db: Session, run_id: str) -> Optional[Summary]:
    """Get summary for a run_id"""
    return db.query(Summary).filter(Summary.run_id == run_id).first()


def list_metadata_with_pagination(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Get paginated list of metadata with optional filters
    Returns: (list of metadata, total count)
    """
    query = db.query(Metadata)

    # Apply filters
    if filters:
        if 'acc_number' in filters and filters['acc_number']:
            query = query.filter(Metadata.acc_number == filters['acc_number'])
        if 'acc_prvdr_code' in filters and filters['acc_prvdr_code']:
            query = query.filter(Metadata.acc_prvdr_code == filters['acc_prvdr_code'])
        if 'rm_name' in filters and filters['rm_name']:
            query = query.filter(Metadata.rm_name.like(f"%{filters['rm_name']}%"))

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    results = query.order_by(Metadata.created_at.desc()).offset(offset).limit(page_size).all()

    return results, total


def delete_processed_data_by_run_id(db: Session, run_id: str) -> Dict[str, int]:
    """
    Delete processed data only (keeps raw + metadata)
    Returns count of deleted records
    """
    try:
        # Get provider code from metadata
        metadata = get_metadata_by_run_id(db, run_id)
        if not metadata:
            logger.warning(f"No metadata found for run_id: {run_id}")
            return {'processed_statements': 0, 'summary': 0}

        provider_code = metadata.acc_prvdr_code

        # Delete processed statements (provider-specific)
        processed_count = delete_processed_by_run_id(db, run_id, provider_code)

        # Delete summary (shared)
        summary_count = db.query(Summary).filter(Summary.run_id == run_id).delete()

        db.flush()
        return {
            'processed_statements': processed_count,
            'summary': summary_count
        }
    except Exception as e:
        logger.error(f"Error deleting processed data for {run_id}: {e}")
        raise


def delete_all_data_by_run_id(db: Session, run_id: str) -> Dict[str, int]:
    """
    Delete ALL data for a run_id (raw, metadata, processed, summary)
    Returns count of deleted records
    """
    try:
        # Get provider code from metadata
        metadata = get_metadata_by_run_id(db, run_id)
        if not metadata:
            logger.warning(f"No metadata found for run_id: {run_id}")
            return {'raw_statements': 0, 'metadata': 0, 'processed_statements': 0, 'summary': 0}

        provider_code = metadata.acc_prvdr_code

        # Delete in order: processed -> summary -> raw -> metadata
        processed_count = delete_processed_by_run_id(db, run_id, provider_code)
        summary_count = db.query(Summary).filter(Summary.run_id == run_id).delete()
        raw_count = delete_raw_by_run_id(db, run_id, provider_code)
        metadata_count = db.query(Metadata).filter(Metadata.run_id == run_id).delete()

        db.flush()
        return {
            'raw_statements': raw_count,
            'metadata': metadata_count,
            'processed_statements': processed_count,
            'summary': summary_count
        }
    except Exception as e:
        logger.error(f"Error deleting all data for {run_id}: {e}")
        raise


def batch_delete_processed_data(db: Session, run_ids: List[str]) -> Dict[str, Any]:
    """Batch delete processed data for multiple run_ids"""
    results = {}
    for run_id in run_ids:
        try:
            counts = delete_processed_data_by_run_id(db, run_id)
            results[run_id] = {'status': 'success', 'counts': counts}
        except Exception as e:
            results[run_id] = {'status': 'error', 'message': str(e)}
    return results


def batch_delete_all_data(db: Session, run_ids: List[str]) -> Dict[str, Any]:
    """Batch delete all data for multiple run_ids"""
    results = {}
    for run_id in run_ids:
        try:
            counts = delete_all_data_by_run_id(db, run_id)
            results[run_id] = {'status': 'success', 'counts': counts}
        except Exception as e:
            results[run_id] = {'status': 'error', 'message': str(e)}
    return results


def get_statistics(db: Session) -> Dict[str, Any]:
    """Get overall statistics across all providers"""
    stats = {}

    # Stats per provider
    for provider_code in ProviderFactory.get_all_providers():
        RawModel = ProviderFactory.get_raw_model(provider_code)
        ProcessedModel = ProviderFactory.get_processed_model(provider_code)

        stats[provider_code] = {
            'raw_statements': db.query(RawModel).count(),
            'processed_statements': db.query(ProcessedModel).count(),
        }

    # Shared stats
    stats['metadata_count'] = db.query(Metadata).count()
    stats['summary_count'] = db.query(Summary).count()

    # Provider breakdown from metadata
    stats['by_provider'] = {}
    for provider_code in ProviderFactory.get_all_providers():
        count = db.query(Metadata).filter(Metadata.acc_prvdr_code == provider_code).count()
        stats['by_provider'][provider_code] = count

    return stats
