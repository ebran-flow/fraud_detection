"""
Delete endpoint schemas
"""
from pydantic import BaseModel
from typing import List, Dict, Any


class DeleteRequest(BaseModel):
    """Request to delete data"""
    run_ids: List[str]
    delete_all: bool = False  # If True, delete all data; if False, delete processed only
    confirm: bool = False  # Confirmation flag


class DeleteResponse(BaseModel):
    """Response for delete endpoint"""
    total: int
    successful: int
    failed: int
    results: Dict[str, Any]
