"""
Summary Model
Provides final-level verification and balance summary (one row per run_id)
"""
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, DateTime, Text, Float, TIMESTAMP, Index, Enum, Boolean
from sqlalchemy.sql import func
from .base import Base


class Summary(Base):
    __tablename__ = 'summary'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True)
    acc_number = Column(String(64))
    acc_prvdr_code = Column(String(16))
    rm_name = Column(String(256))
    num_rows = Column(Integer)
    sheet_md5 = Column(String(64))
    summary_opening_balance = Column(Numeric(18, 2))
    summary_closing_balance = Column(Numeric(18, 2))
    first_balance = Column(Numeric(18, 2))
    last_balance = Column(Numeric(18, 2))
    duplicate_count = Column(Integer, default=0)
    missing_days_detected = Column(Boolean, default=False)
    gap_related_balance_changes = Column(Integer, default=0)
    balance_match = Column(Enum('Success', 'Failed', name='balance_match_enum'))
    verification_status = Column(String(64))
    verification_reason = Column(Text)
    credits = Column(Numeric(18, 2))
    debits = Column(Numeric(18, 2))
    fees = Column(Numeric(18, 2))
    charges = Column(Numeric(18, 2))
    calculated_closing_balance = Column(Numeric(18, 2))
    balance_diff_changes = Column(Integer, default=0)
    balance_diff_change_ratio = Column(Float, default=0.0)
    meta_title = Column(String(512))
    meta_author = Column(String(256))
    meta_producer = Column(String(256))
    meta_created_at = Column(DateTime)
    meta_modified_at = Column(DateTime)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_run_id', 'run_id'),
        Index('idx_acc_number', 'acc_number'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'acc_number': self.acc_number,
            'acc_prvdr_code': self.acc_prvdr_code,
            'rm_name': self.rm_name,
            'num_rows': self.num_rows,
            'sheet_md5': self.sheet_md5,
            'summary_opening_balance': float(self.summary_opening_balance) if self.summary_opening_balance else None,
            'summary_closing_balance': float(self.summary_closing_balance) if self.summary_closing_balance else None,
            'first_balance': float(self.first_balance) if self.first_balance else None,
            'last_balance': float(self.last_balance) if self.last_balance else None,
            'duplicate_count': self.duplicate_count,
            'missing_days_detected': self.missing_days_detected,
            'gap_related_balance_changes': self.gap_related_balance_changes,
            'balance_match': self.balance_match,
            'verification_status': self.verification_status,
            'verification_reason': self.verification_reason,
            'credits': float(self.credits) if self.credits else None,
            'debits': float(self.debits) if self.debits else None,
            'fees': float(self.fees) if self.fees else None,
            'charges': float(self.charges) if self.charges else None,
            'calculated_closing_balance': float(self.calculated_closing_balance) if self.calculated_closing_balance else None,
            'balance_diff_changes': self.balance_diff_changes,
            'balance_diff_change_ratio': self.balance_diff_change_ratio,
            'meta_title': self.meta_title,
            'meta_author': self.meta_author,
            'meta_producer': self.meta_producer,
            'meta_created_at': self.meta_created_at.isoformat() if self.meta_created_at else None,
            'meta_modified_at': self.meta_modified_at.isoformat() if self.meta_modified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
