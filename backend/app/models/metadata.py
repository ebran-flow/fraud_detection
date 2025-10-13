"""
Metadata Model
Stores document-level and parsing-related info (one row per run_id)
"""
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, DateTime, TIMESTAMP, Date, Index, SmallInteger, Text
from sqlalchemy.sql import func
from .base import Base


class Metadata(Base):
    __tablename__ = 'metadata'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True)
    acc_prvdr_code = Column(String(16))
    acc_number = Column(String(64))
    rm_name = Column(String(256))
    num_rows = Column(Integer)
    quality_issues_count = Column(Integer, default=0)
    parsing_status = Column(String(32), default='SUCCESS')
    parsing_error = Column(Text)
    sheet_md5 = Column(String(64))
    summary_opening_balance = Column(Numeric(18, 2))
    summary_closing_balance = Column(Numeric(18, 2))
    first_balance = Column(Numeric(18, 2))
    last_balance = Column(Numeric(18, 2))
    # Summary fields extracted from Airtel Format 1 PDFs
    summary_email_address = Column(String(255))  # Email Address from format 1
    summary_customer_name = Column(String(255))  # Customer Name from format 1
    summary_mobile_number = Column(String(50))  # Mobile Number from format 1
    summary_statement_period = Column(String(100))  # Statement Period from format 1
    summary_request_date = Column(Date)  # Request Date from format 1
    meta_title = Column(String(512))
    meta_author = Column(String(256))
    meta_producer = Column(String(256))
    meta_created_at = Column(DateTime)
    meta_modified_at = Column(DateTime)
    pdf_path = Column(String(512))
    # New columns
    format = Column(String(20))  # Format of the statement (e.g., format_1, format_2)
    mime = Column(String(50))  # MIME type (e.g., application/pdf, text/csv)
    submitted_date = Column(Date)  # From mapper.csv using run_id → created_date
    start_date = Column(Date)  # min(txn_date) from raw_statements
    end_date = Column(Date)  # max(txn_date) from raw_statements
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_acc_number', 'acc_number'),
        Index('idx_run_id', 'run_id'),
        Index('idx_submitted_date', 'submitted_date'),
    )

    @property
    def pdf_format(self):
        """
        Extract numeric format from the format string for backward compatibility.
        Returns: int (1, 2) or None
        """
        if not self.format:
            return None
        if self.format == 'format_1':
            return 1
        elif self.format == 'format_2':
            return 2
        elif self.format == 'excel':
            return None  # Excel doesn't have a pdf_format
        # Try to extract number from format string
        import re
        match = re.search(r'format_(\d+)', self.format)
        if match:
            return int(match.group(1))
        return None

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'acc_prvdr_code': self.acc_prvdr_code,
            'acc_number': self.acc_number,
            'rm_name': self.rm_name,
            'num_rows': self.num_rows,
            'quality_issues_count': self.quality_issues_count,
            'parsing_status': self.parsing_status,
            'parsing_error': self.parsing_error,
            'sheet_md5': self.sheet_md5,
            'summary_opening_balance': float(self.summary_opening_balance) if self.summary_opening_balance else None,
            'summary_closing_balance': float(self.summary_closing_balance) if self.summary_closing_balance else None,
            'first_balance': float(self.first_balance) if self.first_balance else None,
            'last_balance': float(self.last_balance) if self.last_balance else None,
            'summary_email_address': self.summary_email_address,
            'summary_customer_name': self.summary_customer_name,
            'summary_mobile_number': self.summary_mobile_number,
            'summary_statement_period': self.summary_statement_period,
            'summary_request_date': self.summary_request_date.isoformat() if self.summary_request_date else None,
            'meta_title': self.meta_title,
            'meta_author': self.meta_author,
            'meta_producer': self.meta_producer,
            'meta_created_at': self.meta_created_at.isoformat() if self.meta_created_at else None,
            'meta_modified_at': self.meta_modified_at.isoformat() if self.meta_modified_at else None,
            'pdf_path': self.pdf_path,
            'format': self.format,
            'mime': self.mime,
            'submitted_date': self.submitted_date.isoformat() if self.submitted_date else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
