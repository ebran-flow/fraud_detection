"""
Delete endpoint
Handles deletion of processed data or all data for run_ids
Supports multi-provider deletion
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...services.db import get_db
from ...services import crud_v2 as crud
from ...schemas.delete import DeleteRequest, DeleteResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/delete", response_model=DeleteResponse)
async def delete_data(
    request: DeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Delete data for specified run_ids
    - If delete_all=False: Delete processed data only (keeps raw + metadata)
    - If delete_all=True: Delete all data (raw, metadata, processed, summary)
    - Requires confirm=True for safety
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires confirmation. Set 'confirm' to true."
        )

    if not request.run_ids:
        raise HTTPException(status_code=400, detail="No run_ids provided")

    logger.info(f"Deleting data for {len(request.run_ids)} run_ids (delete_all={request.delete_all})")

    try:
        if request.delete_all:
            # Delete all data (provider-specific tables + metadata)
            results = crud.batch_delete_all_data(db, request.run_ids)
        else:
            # Delete processed data only (provider-specific processed tables)
            results = crud.batch_delete_processed_data(db, request.run_ids)

        db.commit()

        # Count successes and failures
        successful = sum(1 for r in results.values() if r['status'] == 'success')
        failed = len(results) - successful

        logger.info(f"Deletion complete: {successful} successful, {failed} failed")

        return DeleteResponse(
            total=len(request.run_ids),
            successful=successful,
            failed=failed,
            results=results
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting data: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")
