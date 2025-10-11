"""
Download endpoint schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class DownloadRequest(BaseModel):
    """Request for download"""
    run_ids: Optional[List[str]] = None
    acc_number: Optional[str] = None
    format: str = 'csv'  # 'csv' or 'excel'
