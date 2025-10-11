"""
UI endpoints that return HTML fragments for HTMX
"""
import logging
from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path

from ...services.db import get_db
from ...services import crud_v2 as crud
from ...models.summary import Summary

router = APIRouter()
logger = logging.getLogger(__name__)

templates_path = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


@router.get("/ui/statements-table", response_class=HTMLResponse)
async def get_statements_table(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    rm_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Return HTML table fragment for HTMX
    """
    try:
        filters = {}
        if acc_number:
            filters['acc_number'] = acc_number
        if acc_prvdr_code:
            filters['acc_prvdr_code'] = acc_prvdr_code
        if rm_name:
            filters['rm_name'] = rm_name

        metadata_list, total = crud.list_metadata_with_pagination(
            db,
            page=page,
            page_size=page_size,
            filters=filters
        )

        # Enrich metadata with summary data (balance_match, verification_reason)
        enriched_statements = []
        for metadata in metadata_list:
            # Get summary for this run_id
            summary = crud.get_summary_by_run_id(db, metadata.run_id)

            # Create enriched object with both metadata and summary data
            stmt_data = {
                'run_id': metadata.run_id,
                'acc_number': metadata.acc_number,
                'acc_prvdr_code': metadata.acc_prvdr_code,
                'rm_name': metadata.rm_name,
                'num_rows': metadata.num_rows,
                'pdf_format': metadata.pdf_format,
                'stmt_opening_balance': metadata.stmt_opening_balance,
                'stmt_closing_balance': metadata.stmt_closing_balance,
                'created_at': metadata.created_at,
                # Add summary fields
                'balance_match': summary.balance_match if summary else None,
                'verification_status': summary.verification_status if summary else None,
                'verification_reason': summary.verification_reason if summary else None,
                'calculated_closing_balance': summary.calculated_closing_balance if summary else None,
            }
            enriched_statements.append(stmt_data)

        import math
        total_pages = math.ceil(total / page_size)

        return templates.TemplateResponse("statements_table.html", {
            "request": request,
            "statements": enriched_statements,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        })

    except Exception as e:
        logger.error(f"Error rendering statements table: {e}")
        return f'<div class="text-red-500">Error loading statements: {str(e)}</div>'
