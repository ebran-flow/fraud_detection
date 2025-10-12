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
                pdf_format=meta.pdf_format,  # Property that extracts from format string
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
    page_size: int = Query(20, ge=1, le=500),
    search: Optional[str] = Query(None, description="Search by run_id or acc_number"),
    acc_number: Optional[str] = Query(None),
    acc_prvdr_code: Optional[str] = Query(None),
    rm_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),  # Consolidated status: IMPORT_FAILED, IMPORTED, VERIFIED, VERIFIED_WITH_WARNINGS, VERIFICATION_FAILED, FLAGGED
    processing_status: Optional[str] = Query(None),  # IMPORTED or PROCESSED (deprecated, use 'status')
    parsing_status: Optional[str] = Query(None),  # SUCCESS or FAILED (deprecated, use 'status')
    verification_status: Optional[str] = Query(None),  # PASS or FAIL (deprecated, use 'status')
    from_date: Optional[str] = Query(None, description="Filter by submitted_date >= from_date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter by submitted_date <= to_date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get paginated list of unified statements (metadata + summary)
    Shows consolidated status for each statement

    Supports filtering by:
    - search: Search in run_id or acc_number
    - acc_number: Account number
    - acc_prvdr_code: Provider code (UATL, UMTN)
    - rm_name: RM name
    - status: IMPORT_FAILED, IMPORTED, VERIFIED, VERIFIED_WITH_WARNINGS, VERIFICATION_FAILED, FLAGGED
    - from_date, to_date: Date range for submitted_date
    """
    try:
        # Build query
        where_clauses = []

        # Search filter
        if search:
            where_clauses.append(f"(run_id LIKE '%{search}%' OR acc_number LIKE '%{search}%')")

        if acc_number:
            where_clauses.append(f"acc_number = '{acc_number}'")
        if acc_prvdr_code:
            where_clauses.append(f"acc_prvdr_code = '{acc_prvdr_code}'")
        if rm_name:
            where_clauses.append(f"rm_name LIKE '%{rm_name}%'")

        # Consolidated status filter
        if status:
            where_clauses.append(f"status = '{status}'")

        # Backward compatibility filters (deprecated)
        if processing_status:
            where_clauses.append(f"processing_status = '{processing_status}'")
        if parsing_status:
            where_clauses.append(f"parsing_status = '{parsing_status}'")
        if verification_status:
            where_clauses.append(f"verification_status = '{verification_status}'")

        # Date range filters
        if from_date:
            where_clauses.append(f"submitted_date >= '{from_date}'")
        if to_date:
            where_clauses.append(f"submitted_date <= '{to_date}'")

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
                format,
                mime,
                submitted_date,
                start_date,
                end_date,
                rm_name,
                num_rows,
                parsing_status,
                parsing_error,
                imported_at,
                status,
                processing_status,
                verification_status,
                verification_reason,
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
                'format': row[4],
                'mime': row[5],
                'submitted_date': row[6].isoformat() if row[6] else None,
                'start_date': row[7].isoformat() if row[7] else None,
                'end_date': row[8].isoformat() if row[8] else None,
                'rm_name': row[9],
                'num_rows': row[10],
                'parsing_status': row[11],
                'parsing_error': row[12],
                'imported_at': row[13].isoformat() if row[13] else None,
                'status': row[14],  # Consolidated status
                'processing_status': row[15],
                'verification_status': row[16],
                'verification_reason': row[17],
                'balance_match': row[18],
                'duplicate_count': row[19],
                'processed_at': row[20].isoformat() if row[20] else None,
                'balance_diff_changes': row[21],
                'balance_diff_change_ratio': float(row[22]) if row[22] else None,
                'calculated_closing_balance': float(row[23]) if row[23] else None,
                'stmt_closing_balance': float(row[24]) if row[24] else None,
                'meta_title': row[25],
                'meta_author': row[26],
                'meta_producer': row[27],
                'meta_created_at': row[28].isoformat() if row[28] else None,
                'meta_modified_at': row[29].isoformat() if row[29] else None
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
