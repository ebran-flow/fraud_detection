"""
Parallel Import API Endpoint
Provides batch import functionality with multiprocessing
"""
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ...services.db import get_db
from ...services.parallel_importer import (
    parallel_import_files,
    batch_import_from_directory,
    get_optimal_worker_count
)

router = APIRouter()
logger = logging.getLogger(__name__)


class FileImportRequest(BaseModel):
    """Request model for importing specific files"""
    files: List[dict]  # List of {'file_path', 'run_id', 'provider_code'}
    num_workers: Optional[int] = None


class DirectoryImportRequest(BaseModel):
    """Request model for importing all files from directory"""
    directory: str
    provider_code: str  # 'UATL' or 'UMTN'
    num_workers: Optional[int] = None


@router.post("/parallel-import")
async def parallel_import(
    request: FileImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Import multiple files in parallel using multiprocessing

    Body:
    {
        "files": [
            {"file_path": "/path/to/file1.pdf", "run_id": "abc123", "provider_code": "UATL"},
            {"file_path": "/path/to/file2.pdf", "run_id": "def456", "provider_code": "UATL"}
        ],
        "num_workers": 8  // Optional, defaults to CPU count - 1
    }
    """
    try:
        # Get database configuration
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'database': os.getenv('DB_NAME', 'fraud_detection')
        }

        # Validate files exist
        for file_info in request.files:
            if not os.path.exists(file_info['file_path']):
                raise HTTPException(status_code=400, detail=f"File not found: {file_info['file_path']}")

        # Import files in parallel
        results = parallel_import_files(
            request.files,
            db_config,
            num_workers=request.num_workers
        )

        # Calculate summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        total_transactions = sum(r.get('num_transactions', 0) for r in results if r['status'] == 'success')

        return {
            'status': 'completed',
            'total_files': len(request.files),
            'successful': successful,
            'failed': failed,
            'total_transactions': total_transactions,
            'workers_used': request.num_workers or get_optimal_worker_count(),
            'results': results
        }

    except Exception as e:
        logger.error(f"Error in parallel import: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch-import-directory")
async def batch_import_dir(
    request: DirectoryImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Import all files from a directory in parallel

    Body:
    {
        "directory": "/path/to/statements",
        "provider_code": "UATL",
        "num_workers": 8  // Optional
    }
    """
    try:
        # Validate directory exists
        if not os.path.exists(request.directory):
            raise HTTPException(status_code=400, detail=f"Directory not found: {request.directory}")

        if not os.path.isdir(request.directory):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.directory}")

        # Get database configuration
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'database': os.getenv('DB_NAME', 'fraud_detection')
        }

        # Import directory
        result = batch_import_from_directory(
            request.directory,
            request.provider_code,
            db_config
        )

        return result

    except Exception as e:
        logger.error(f"Error in batch directory import: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/optimal-workers")
async def get_optimal_workers():
    """
    Get recommended number of workers based on system CPU count
    """
    return {
        'optimal_workers': get_optimal_worker_count(),
        'cpu_count': os.cpu_count(),
        'recommendation': f"Use {get_optimal_worker_count()} workers for best performance"
    }
