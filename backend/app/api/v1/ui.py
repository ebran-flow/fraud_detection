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
from ...services.crud import list_metadata_with_pagination

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

        metadata_list, total = list_metadata_with_pagination(
            db,
            page=page,
            page_size=page_size,
            filters=filters
        )

        import math
        total_pages = math.ceil(total / page_size)

        return templates.TemplateResponse("statements_table.html", {
            "request": request,
            "statements": metadata_list,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        })

    except Exception as e:
        logger.error(f"Error rendering statements table: {e}")
        return f'<div class="text-red-500">Error loading statements: {str(e)}</div>'
