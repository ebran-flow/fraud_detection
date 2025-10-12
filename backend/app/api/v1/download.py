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
from ...services.google_sheets import export_summary_to_google_sheets, create_spreadsheet_from_csv_data

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
    run_ids: Optional[str] = Query(None),  # Accept as string (comma-separated or single)
    run_id: Optional[str] = Query(None),  # Single run_id (preferred)
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    format: str = Query('csv', regex='^(csv|excel)$'),
    db: Session = Depends(get_db)
):
    """
    Download summary data as CSV or Excel
    Use run_id parameter for single statement download (recommended)
    Use run_ids for multiple statements (comma-separated)
    """
    # Convert run_ids string to list
    run_ids_list = None
    if run_ids:
        run_ids_list = [rid.strip() for rid in run_ids.split(',')]
    elif run_id:
        run_ids_list = [run_id]
    try:
        if format == 'csv':
            csv_data = export_summary_csv(db, run_ids_list, acc_number, acc_prvdr_code)

            if not csv_data:
                raise HTTPException(status_code=404, detail="No data found")

            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=summary.csv"}
            )
        else:  # excel
            excel_data = export_summary_excel(db, run_ids_list, acc_number, acc_prvdr_code)

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


@router.get("/export/google-sheets")
async def export_to_google_sheets(
    run_ids: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    data_type: str = Query('processed', regex='^(processed|summary)$'),
    db: Session = Depends(get_db)
):
    """
    Export processed statements or summary data to Google Sheets
    Returns URL to the created spreadsheet

    Args:
        data_type: 'processed' for detailed transactions, 'summary' for summary data
    """
    # Convert run_ids string to list
    run_ids_list = None
    if run_ids:
        run_ids_list = [rid.strip() for rid in run_ids.split(',')]
    elif run_id:
        run_ids_list = [run_id]

    try:
        # Get CSV data based on type
        if data_type == 'processed':
            csv_data = export_processed_statements_csv(db, run_ids_list, acc_number, acc_prvdr_code)
            data_label = "Processed Statements"
        else:
            csv_data = export_summary_csv(db, run_ids_list, acc_number, acc_prvdr_code)
            data_label = "Summary"

        if not csv_data:
            raise HTTPException(status_code=404, detail="No data found")

        # Generate title based on format: {acc_number}_{run_id}
        if run_ids_list and len(run_ids_list) == 1 and data_type == 'processed':
            # For single processed statement, get account number from database
            from ...services import crud_v2 as crud
            metadata = crud.get_metadata_by_run_id(db, run_ids_list[0])
            if metadata and metadata.acc_number:
                title = f"{metadata.acc_number}_{run_ids_list[0]}"
            else:
                title = f"unknown_{run_ids_list[0]}"
        elif run_ids_list and len(run_ids_list) == 1:
            title = f"{data_label} - {run_ids_list[0]}"
        elif run_ids_list:
            title = f"{data_label} - {len(run_ids_list)} statements"
        else:
            title = f"{data_label} - All"

        # Create Google Sheet
        sheet_url = create_spreadsheet_from_csv_data(csv_data, title)

        return {
            "success": True,
            "url": sheet_url,
            "title": title
        }

    except Exception as e:
        logger.error(f"Error exporting to Google Sheets: {e}")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")
