"""
Download endpoint
Handles CSV/Excel exports of processed statements and summaries
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io

from ...services.db import get_db
from ...services.export import (
    export_processed_statements_csv,
    export_summary_csv,
    export_processed_statements_excel,
    export_summary_excel
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/download/processed")
async def download_processed_statements(
    run_ids: Optional[List[str]] = Query(None),
    run_id: Optional[str] = Query(None),  # Single run_id (preferred)
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    format: str = Query('csv', regex='^(csv|excel)$'),
    db: Session = Depends(get_db)
):
    """
    Download processed statements as CSV or Excel
    Use run_id parameter for single statement download (recommended)
    Use run_ids for multiple statements
    """
    # Prioritize single run_id if provided
    if run_id:
        run_ids = [run_id]
    try:
        if format == 'csv':
            csv_data = export_processed_statements_csv(db, run_ids, acc_number, acc_prvdr_code)

            if not csv_data:
                raise HTTPException(status_code=404, detail="No data found")

            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=processed_statements.csv"}
            )
        else:  # excel
            excel_data = export_processed_statements_excel(db, run_ids, acc_number, acc_prvdr_code)

            if not excel_data:
                raise HTTPException(status_code=404, detail="No data found")

            return StreamingResponse(
                io.BytesIO(excel_data),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=processed_statements.xlsx"}
            )

    except Exception as e:
        logger.error(f"Error downloading processed statements: {e}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")


@router.get("/download/summary")
async def download_summary(
    run_ids: Optional[List[str]] = Query(None),
    run_id: Optional[str] = Query(None),  # Single run_id (preferred)
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    format: str = Query('csv', regex='^(csv|excel)$'),
    db: Session = Depends(get_db)
):
    """
    Download summary data as CSV or Excel
    Use run_id parameter for single statement download (recommended)
    Use run_ids for multiple statements
    """
    # Prioritize single run_id if provided
    if run_id:
        run_ids = [run_id]
    try:
        if format == 'csv':
            csv_data = export_summary_csv(db, run_ids, acc_number, acc_prvdr_code)

            if not csv_data:
                raise HTTPException(status_code=404, detail="No data found")

            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=summary.csv"}
            )
        else:  # excel
            excel_data = export_summary_excel(db, run_ids, acc_number, acc_prvdr_code)

            if not excel_data:
                raise HTTPException(status_code=404, detail="No data found")

            return StreamingResponse(
                io.BytesIO(excel_data),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=summary.xlsx"}
            )

    except Exception as e:
        logger.error(f"Error downloading summary: {e}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
