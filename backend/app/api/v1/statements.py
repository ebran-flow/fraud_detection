"""
Statements list endpoint
Provides paginated list of statements with filtering
Supports multi-provider filtering
"""
import logging
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ...services.db import get_db
from ...services import crud_v2 as crud
from ...schemas.list import ListResponse, MetadataItem, PaginationInfo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list", response_model=ListResponse)
async def list_statements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    rm_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of statements
    Supports filtering by acc_number, acc_prvdr_code, rm_name
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

        # Convert to response format
        items = [
            MetadataItem(
                id=meta.id,
                run_id=meta.run_id,
                acc_number=meta.acc_number,
                acc_prvdr_code=meta.acc_prvdr_code,
                rm_name=meta.rm_name,
                num_rows=meta.num_rows,
                pdf_format=meta.pdf_format,
                stmt_opening_balance=float(meta.stmt_opening_balance) if meta.stmt_opening_balance else None,
                stmt_closing_balance=float(meta.stmt_closing_balance) if meta.stmt_closing_balance else None,
                created_at=meta.created_at.isoformat() if meta.created_at else None
            )
            for meta in metadata_list
        ]

        total_pages = math.ceil(total / page_size)

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )

        return ListResponse(items=items, pagination=pagination)

    except Exception as e:
        logger.error(f"Error listing statements: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing statements: {str(e)}")
