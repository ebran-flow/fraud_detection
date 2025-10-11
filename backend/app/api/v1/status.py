"""
Status endpoint
Provides health check and system statistics
Supports multi-provider statistics
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from ...services.db import get_db
from ...services import crud_v2 as crud
from ...services.mapper import load_mapper

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get system status and statistics
    """
    try:
        stats = crud.get_statistics(db)

        # Check mapper availability
        mapper_df = load_mapper()
        mapper_loaded = not mapper_df.empty
        mapper_count = len(mapper_df) if mapper_loaded else 0

        return {
            'status': 'healthy',
            'database': 'connected',
            'statistics': stats,
            'mapper': {
                'loaded': mapper_loaded,
                'record_count': mapper_count
            }
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok"}
