"""
List endpoint schemas
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MetadataItem(BaseModel):
    """Metadata item for list view"""
    id: int
    run_id: str
    acc_number: Optional[str]
    acc_prvdr_code: Optional[str]
    rm_name: Optional[str]
    num_rows: Optional[int]
    pdf_format: Optional[int]
    stmt_opening_balance: Optional[float]
    stmt_closing_balance: Optional[float]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination information"""
    page: int
    page_size: int
    total: int
    total_pages: int


class ListResponse(BaseModel):
    """Response for list endpoint"""
    items: List[MetadataItem]
    pagination: PaginationInfo
