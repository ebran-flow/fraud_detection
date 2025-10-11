"""
CRUD helper utilities - DRY layer for database operations
"""
from typing import List, Optional, Dict, Any, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, delete
from datetime import datetime
import logging

from ..models.base import Base
from ..models.raw import RawStatement
from ..models.metadata import Metadata
from ..models.processed import ProcessedStatement
from ..models.summary import Summary

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)


# ===== Generic CRUD Operations =====

def create(db: Session, model: Type[T], data: Dict[str, Any]) -> T:
    """Create a new record"""
    try:
        instance = model(**data)
        db.add(instance)
        db.flush()
        return instance
    except Exception as e:
        logger.error(f"Error creating {model.__name__}: {e}")
        raise


def bulk_create(db: Session, model: Type[T], data_list: List[Dict[str, Any]]) -> List[T]:
    """Bulk create multiple records"""
    try:
        instances = [model(**data) for data in data_list]
        db.bulk_save_objects(instances, return_defaults=True)
        db.flush()
        return instances
    except Exception as e:
        logger.error(f"Error bulk creating {model.__name__}: {e}")
        raise


def get_by_id(db: Session, model: Type[T], record_id: int) -> Optional[T]:
    """Get a record by ID"""
    return db.query(model).filter(model.id == record_id).first()


def get_by_field(db: Session, model: Type[T], field_name: str, value: Any) -> Optional[T]:
    """Get a single record by field name"""
    return db.query(model).filter(getattr(model, field_name) == value).first()


def get_all_by_field(db: Session, model: Type[T], field_name: str, value: Any) -> List[T]:
    """Get all records matching a field value"""
    return db.query(model).filter(getattr(model, field_name) == value).all()


def update(db: Session, instance: T, data: Dict[str, Any]) -> T:
    """Update a record"""
    try:
        for key, value in data.items():
            setattr(instance, key, value)
        db.flush()
        return instance
    except Exception as e:
        logger.error(f"Error updating record: {e}")
        raise


def delete_by_id(db: Session, model: Type[T], record_id: int) -> bool:
    """Delete a record by ID"""
    try:
        instance = get_by_id(db, model, record_id)
        if instance:
            db.delete(instance)
            db.flush()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting record: {e}")
        raise


def delete_by_field(db: Session, model: Type[T], field_name: str, value: Any) -> int:
    """Delete all records matching a field value"""
    try:
        count = db.query(model).filter(getattr(model, field_name) == value).delete()
        db.flush()
        return count
    except Exception as e:
        logger.error(f"Error deleting records: {e}")
        raise


# ===== Specific Operations for Fraud Detection =====

def check_run_id_exists(db: Session, run_id: str) -> bool:
    """Check if a run_id already exists in raw_statements"""
    return db.query(RawStatement).filter(RawStatement.run_id == run_id).first() is not None


def get_raw_statements_by_run_id(db: Session, run_id: str) -> List[RawStatement]:
    """Get all raw statements for a run_id"""
    return db.query(RawStatement).filter(RawStatement.run_id == run_id).order_by(RawStatement.txn_date).all()


def get_metadata_by_run_id(db: Session, run_id: str) -> Optional[Metadata]:
    """Get metadata for a run_id"""
    return db.query(Metadata).filter(Metadata.run_id == run_id).first()


def get_processed_statements_by_run_id(db: Session, run_id: str) -> List[ProcessedStatement]:
    """Get all processed statements for a run_id"""
    return db.query(ProcessedStatement).filter(ProcessedStatement.run_id == run_id).order_by(ProcessedStatement.txn_date).all()


def get_summary_by_run_id(db: Session, run_id: str) -> Optional[Summary]:
    """Get summary for a run_id"""
    return db.query(Summary).filter(Summary.run_id == run_id).first()


def list_metadata_with_pagination(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> tuple[List[Metadata], int]:
    """
    Get paginated list of metadata with optional filters
    Returns: (list of metadata, total count)
    """
    query = db.query(Metadata)

    # Apply filters if provided
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
        processed_count = delete_by_field(db, ProcessedStatement, 'run_id', run_id)
        summary_count = delete_by_field(db, Summary, 'run_id', run_id)

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
        # Delete in order: processed -> summary -> raw -> metadata
        processed_count = delete_by_field(db, ProcessedStatement, 'run_id', run_id)
        summary_count = delete_by_field(db, Summary, 'run_id', run_id)
        raw_count = delete_by_field(db, RawStatement, 'run_id', run_id)
        metadata_count = delete_by_field(db, Metadata, 'run_id', run_id)

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
    """Get overall statistics"""
    return {
        'total_statements': db.query(RawStatement).count(),
        'total_accounts': db.query(Metadata).count(),
        'processed_count': db.query(ProcessedStatement).count(),
        'summary_count': db.query(Summary).count(),
    }
