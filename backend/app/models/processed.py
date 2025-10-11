"""
Processed Statements Model
Adds processing-level information for transactions
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, Text, Boolean, Integer, TIMESTAMP, Index, ForeignKey
from sqlalchemy.sql import func
from .base import Base


class ProcessedStatement(Base):
    __tablename__ = 'processed_statements'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_id = Column(BigInteger, ForeignKey('raw_statements.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(String(64))
    acc_prvdr_code = Column(String(16))
    acc_number = Column(String(64))
    txn_id = Column(String(128))
    txn_date = Column(DateTime)
    txn_type = Column(String(64))
    description = Column(Text)
    status = Column(String(32))
    amount = Column(Numeric(18, 2))
    fee = Column(Numeric(18, 2), default=0)
    balance = Column(Numeric(18, 2))
    is_duplicate = Column(Boolean, default=False)
    is_special_txn = Column(Boolean, default=False)
    special_txn_type = Column(String(64))
    calculated_running_balance = Column(Numeric(18, 2))
    balance_diff = Column(Numeric(18, 2))
    balance_diff_change_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_run_id', 'run_id'),
        Index('idx_acc_number', 'acc_number'),
        Index('idx_provider', 'acc_prvdr_code'),
        Index('idx_provider_acc', 'acc_prvdr_code', 'acc_number'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'raw_id': self.raw_id,
            'run_id': self.run_id,
            'acc_prvdr_code': self.acc_prvdr_code,
            'acc_number': self.acc_number,
            'txn_id': self.txn_id,
            'txn_date': self.txn_date.isoformat() if self.txn_date else None,
            'txn_type': self.txn_type,
            'description': self.description,
            'status': self.status,
            'amount': float(self.amount) if self.amount else None,
            'fee': float(self.fee) if self.fee else None,
            'balance': float(self.balance) if self.balance else None,
            'is_duplicate': self.is_duplicate,
            'is_special_txn': self.is_special_txn,
            'special_txn_type': self.special_txn_type,
            'calculated_running_balance': float(self.calculated_running_balance) if self.calculated_running_balance else None,
            'balance_diff': float(self.balance_diff) if self.balance_diff else None,
            'balance_diff_change_count': self.balance_diff_change_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
