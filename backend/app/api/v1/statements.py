"""
Statements list endpoint
Provides paginated list of statements with filtering
Supports multi-provider filtering
"""
import logging
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any

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


@router.get("/unified-list")
async def list_unified_statements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    rm_name: Optional[str] = Query(None),
    processing_status: Optional[str] = Query(None),  # IMPORTED or PROCESSED
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get paginated list of unified statements (metadata + summary)
    Shows import and processing status

    Supports filtering by:
    - acc_number: Account number
    - acc_prvdr_code: Provider code (UATL, UMTN)
    - rm_name: RM name
    - processing_status: IMPORTED or PROCESSED
    """
    try:
        # Build query
        where_clauses = []
        if acc_number:
            where_clauses.append(f"acc_number = '{acc_number}'")
        if acc_prvdr_code:
            where_clauses.append(f"acc_prvdr_code = '{acc_prvdr_code}'")
        if rm_name:
            where_clauses.append(f"rm_name LIKE '%{rm_name}%'")
        if processing_status:
            where_clauses.append(f"processing_status = '{processing_status}'")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM unified_statements WHERE {where_clause}"
        count_result = db.execute(text(count_query)).fetchone()
        total = count_result[0] if count_result else 0

        # Get paginated data
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT
                metadata_id,
                run_id,
                acc_number,
                acc_prvdr_code,
                rm_name,
                num_rows,
                imported_at,
                processing_status,
                verification_status,
                balance_match,
                duplicate_count,
                processed_at,
                balance_diff_changes,
                balance_diff_change_ratio,
                calculated_closing_balance,
                stmt_closing_balance,
                meta_title,
                meta_author,
                meta_producer,
                meta_created_at,
                meta_modified_at
            FROM unified_statements
            WHERE {where_clause}
            ORDER BY imported_at DESC
            LIMIT {page_size} OFFSET {offset}
        """

        result = db.execute(text(data_query))
        rows = result.fetchall()

        # Convert to list of dicts
        items = []
        for row in rows:
            items.append({
                'metadata_id': row[0],
                'run_id': row[1],
                'acc_number': row[2],
                'acc_prvdr_code': row[3],
                'rm_name': row[4],
                'num_rows': row[5],
                'imported_at': row[6].isoformat() if row[6] else None,
                'processing_status': row[7],
                'verification_status': row[8],
                'balance_match': row[9],
                'duplicate_count': row[10],
                'processed_at': row[11].isoformat() if row[11] else None,
                'balance_diff_changes': row[12],
                'balance_diff_change_ratio': float(row[13]) if row[13] else None,
                'calculated_closing_balance': float(row[14]) if row[14] else None,
                'stmt_closing_balance': float(row[15]) if row[15] else None,
                'meta_title': row[16],
                'meta_author': row[17],
                'meta_producer': row[18],
                'meta_created_at': row[19].isoformat() if row[19] else None,
                'meta_modified_at': row[20].isoformat() if row[20] else None
            })

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return {
            'items': items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages
            }
        }

    except Exception as e:
        logger.error(f"Error listing unified statements: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing unified statements: {str(e)}")
