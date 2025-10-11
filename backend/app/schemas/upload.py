"""
Upload endpoint schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class UploadFileResult(BaseModel):
    """Result for a single uploaded file"""
    filename: str
    run_id: str
    status: str  # 'success', 'skipped', 'error'
    message: str
    acc_number: Optional[str] = None
    num_transactions: Optional[int] = None


class UploadResponse(BaseModel):
    """Response for upload endpoint"""
    total_files: int
    successful: int
    skipped: int
    failed: int
    results: List[UploadFileResult]
