"""
Upload endpoint
Handles file uploads (PDF for UATL, Excel/CSV for UMTN), parsing, and storage in database
"""
import os
import logging
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...config import UPLOADED_PDF_PATH
from ...services.db import get_db
from ...services.parsers import get_parser
from ...services.mapper import enrich_metadata_with_mapper, get_mapping_by_run_id
from ...services import crud_v2 as crud
from ...models.metadata import Metadata
from ...schemas.upload import UploadResponse, UploadFileResult

router = APIRouter()
logger = logging.getLogger(__name__)


def extract_run_id_from_filename(filename: str) -> str:
    """
    Extract run_id from filename
    Convention: filename should be in format {run_id}.{ext}
    """
    return os.path.splitext(filename)[0]


def detect_provider_from_file(filename: str, run_id: str, file_content_check: str = None) -> str:
    """
    Detect provider code from filename extension and mapper

    Priority:
    1. Check mapper.csv for run_id
    2. Check file content for Airtel/MTN indicators (for CSV files)
    3. Check file extension (.pdf = UATL, .csv with Airtel = UATL, .xlsx/.xls/.csv = UMTN)
    4. Default to UATL
    """
    # First check mapper
    mapping = get_mapping_by_run_id(run_id)
    if mapping and mapping.get('acc_prvdr_code'):
        logger.info(f"Provider detected from mapper for {run_id}: {mapping['acc_prvdr_code']}")
        return mapping['acc_prvdr_code']

    # Check file extension
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return 'UATL'
    elif ext == 'csv':
        # For CSV, check content to determine provider
        if file_content_check and 'Airtel Money' in file_content_check:
            logger.info(f"Detected Airtel CSV for {run_id}")
            return 'UATL'
        else:
            logger.info(f"Detected MTN CSV for {run_id}")
            return 'UMTN'
    elif ext in ['xlsx', 'xls']:
        return 'UMTN'

    # Default
    logger.warning(f"Could not detect provider for {filename}, defaulting to UATL")
    return 'UATL'


def validate_file(file_path: str, provider_code: str) -> bool:
    """
    Validate file based on provider type

    UATL: Must be PDF or CSV (Airtel Money CSV)
    UMTN: Must be Excel or CSV
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False

    ext = file_path.lower().split('.')[-1]

    if provider_code == 'UATL':
        if ext not in ['pdf', 'csv']:
            logger.error(f"UATL file must be PDF or CSV: {file_path}")
            return False
    elif provider_code == 'UMTN':
        if ext not in ['xlsx', 'xls', 'csv']:
            logger.error(f"UMTN file must be Excel or CSV: {file_path}")
            return False

    return True


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    provider: str = Query(None, description="Provider code (UATL or UMTN)")
):
    """
    Upload one or more statement files (PDF for UATL, Excel/CSV for UMTN)
    - Detects provider from filename extension and mapper
    - Parses file data using provider-specific parser
    - Checks if run_id already exists (skip if exists)
    - Stores raw transactions and metadata in provider-specific tables
    - Stores file for audit
    """
    results = []
    successful = 0
    skipped = 0
    failed = 0

    for file in files:
        try:
            # Extract run_id from filename
            run_id = extract_run_id_from_filename(file.filename)

            # Use provided provider or detect from file and mapper
            if provider:
                provider_code = provider
                logger.info(f"Using user-selected provider for {run_id}: {provider_code}")
            else:
                provider_code = detect_provider_from_file(file.filename, run_id)
                logger.info(f"Auto-detected provider for {run_id}: {provider_code}")

            # Check if already processed (provider-specific)
            if crud.check_run_id_exists(db, run_id, provider_code):
                results.append(UploadFileResult(
                    filename=file.filename,
                    run_id=run_id,
                    status='skipped',
                    message=f'Already exists in database (provider: {provider_code})'
                ))
                skipped += 1
                continue

            # Save uploaded file
            file_path = os.path.join(UPLOADED_PDF_PATH, file.filename)
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file.file, f)

            # Validate file based on provider
            if not validate_file(file_path, provider_code):
                results.append(UploadFileResult(
                    filename=file.filename,
                    run_id=run_id,
                    status='error',
                    message=f'Invalid file format for provider {provider_code}'
                ))
                failed += 1
                continue

            # Get provider-specific parser based on file type
            parser = get_parser(provider_code, file_path)

            # Parse file using provider-specific parser
            raw_statements, metadata = parser(file_path, run_id)

            # Enrich metadata with mapper data (rm_name, acc_prvdr_code override)
            metadata = enrich_metadata_with_mapper(metadata, run_id)

            # Provider code should already be in metadata from parser, but ensure consistency
            provider_code = metadata.get('acc_prvdr_code', provider_code)

            # Insert into database within transaction
            try:
                # Insert metadata first (shared table)
                metadata_obj = crud.create(db, Metadata, metadata)

                # Bulk insert raw statements (provider-specific table)
                crud.bulk_create_raw(db, provider_code, raw_statements)

                db.commit()

                results.append(UploadFileResult(
                    filename=file.filename,
                    run_id=run_id,
                    status='success',
                    message=f'Successfully parsed and stored ({provider_code})',
                    acc_number=metadata['acc_number'],
                    num_transactions=len(raw_statements)
                ))
                successful += 1

                logger.info(f"Successfully uploaded and parsed {file.filename} ({provider_code}): {len(raw_statements)} transactions")

            except Exception as e:
                db.rollback()
                logger.error(f"Database error for {file.filename}: {e}")
                results.append(UploadFileResult(
                    filename=file.filename,
                    run_id=run_id,
                    status='error',
                    message=f'Database error: {str(e)}'
                ))
                failed += 1

        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            results.append(UploadFileResult(
                filename=file.filename,
                run_id=extract_run_id_from_filename(file.filename) if file.filename else 'unknown',
                status='error',
                message=f'Processing error: {str(e)}'
            ))
            failed += 1

    return UploadResponse(
        total_files=len(files),
        successful=successful,
        skipped=skipped,
        failed=failed,
        results=results
    )
