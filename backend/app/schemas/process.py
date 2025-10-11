"""
Process endpoint schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class ProcessRequest(BaseModel):
    """Request to process statements"""
    run_ids: List[str]


class ProcessResult(BaseModel):
    """Result for a single processed statement"""
    run_id: str
    status: str  # 'success', 'error'
    message: Optional[str] = None
    processed_count: Optional[int] = None
    duplicate_count: Optional[int] = None
    balance_match: Optional[str] = None
    verification_status: Optional[str] = None


class ProcessResponse(BaseModel):
    """Response for process endpoint"""
    total: int
    successful: int
    failed: int
    results: List[ProcessResult]
