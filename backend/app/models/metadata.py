"""
Metadata Model
Stores document-level and parsing-related info (one row per run_id)
"""
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, DateTime, TIMESTAMP, Index, SmallInteger, Text
from sqlalchemy.sql import func
from .base import Base


class Metadata(Base):
    __tablename__ = 'metadata'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True)
    acc_prvdr_code = Column(String(16))
    acc_number = Column(String(64))
    pdf_format = Column(SmallInteger)  # 1 or 2
    rm_name = Column(String(256))
    num_rows = Column(Integer)
    parsing_status = Column(String(32), default='SUCCESS')
    parsing_error = Column(Text)
    sheet_md5 = Column(String(64))
    summary_opening_balance = Column(Numeric(18, 2))
    summary_closing_balance = Column(Numeric(18, 2))
    stmt_opening_balance = Column(Numeric(18, 2))
    stmt_closing_balance = Column(Numeric(18, 2))
    meta_title = Column(String(512))
    meta_author = Column(String(256))
    meta_producer = Column(String(256))
    meta_created_at = Column(DateTime)
    meta_modified_at = Column(DateTime)
    pdf_path = Column(String(512))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_acc_number', 'acc_number'),
        Index('idx_run_id', 'run_id'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'acc_prvdr_code': self.acc_prvdr_code,
            'acc_number': self.acc_number,
            'pdf_format': self.pdf_format,
            'rm_name': self.rm_name,
            'num_rows': self.num_rows,
            'parsing_status': self.parsing_status,
            'parsing_error': self.parsing_error,
            'sheet_md5': self.sheet_md5,
            'summary_opening_balance': float(self.summary_opening_balance) if self.summary_opening_balance else None,
            'summary_closing_balance': float(self.summary_closing_balance) if self.summary_closing_balance else None,
            'stmt_opening_balance': float(self.stmt_opening_balance) if self.stmt_opening_balance else None,
            'stmt_closing_balance': float(self.stmt_closing_balance) if self.stmt_closing_balance else None,
            'meta_title': self.meta_title,
            'meta_author': self.meta_author,
            'meta_producer': self.meta_producer,
            'meta_created_at': self.meta_created_at.isoformat() if self.meta_created_at else None,
            'meta_modified_at': self.meta_modified_at.isoformat() if self.meta_modified_at else None,
            'pdf_path': self.pdf_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
