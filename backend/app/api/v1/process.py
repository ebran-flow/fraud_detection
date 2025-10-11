"""
Process endpoint
Handles processing of statements: duplicate detection, balance verification
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...services.db import get_db
from ...services.processor import process_statement, batch_process_statements
from ...schemas.process import ProcessRequest, ProcessResponse, ProcessResult

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/process", response_model=ProcessResponse)
async def process_statements(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process one or more statements
    - Reads raw statements from database
    - Detects duplicates
    - Verifies running balance
    - Creates processed statements and summary
    """
    if not request.run_ids:
        raise HTTPException(status_code=400, detail="No run_ids provided")

    logger.info(f"Processing {len(request.run_ids)} statements")

    try:
        # Process all statements
        results_dict = batch_process_statements(db, request.run_ids)

        # Convert to response format
        results = []
        successful = 0
        failed = 0

        for run_id, result in results_dict.items():
            if result['status'] == 'success':
                results.append(ProcessResult(
                    run_id=run_id,
                    status='success',
                    message='Successfully processed',
                    processed_count=result.get('processed_count'),
                    duplicate_count=result.get('duplicate_count'),
                    balance_match=result.get('balance_match'),
                    verification_status=result.get('verification_status')
                ))
                successful += 1
            else:
                results.append(ProcessResult(
                    run_id=run_id,
                    status='error',
                    message=result.get('message', 'Unknown error')
                ))
                failed += 1

        return ProcessResponse(
            total=len(request.run_ids),
            successful=successful,
            failed=failed,
            results=results
        )

    except Exception as e:
        logger.error(f"Error processing statements: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
