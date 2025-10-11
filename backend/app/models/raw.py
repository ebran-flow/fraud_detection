"""
Raw Statements Model
Stores minimally processed transactions from PDF parsing
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, Text, TIMESTAMP, Index
from sqlalchemy.sql import func
from .base import Base


class RawStatement(Base):
    __tablename__ = 'raw_statements'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False)
    acc_prvdr_code = Column(String(16))
    acc_number = Column(String(64))
    txn_id = Column(String(128))
    txn_date = Column(DateTime)
    txn_type = Column(String(64))
    description = Column(Text)
    from_acc = Column(String(64))
    to_acc = Column(String(64))
    status = Column(String(32))
    txn_direction = Column(String(16))
    amount = Column(Numeric(18, 2))
    fee = Column(Numeric(18, 2), default=0)
    balance = Column(Numeric(18, 2))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_acc_number', 'acc_number'),
        Index('idx_run_id', 'run_id'),
        Index('idx_provider', 'acc_prvdr_code'),
        Index('idx_provider_acc', 'acc_prvdr_code', 'acc_number'),
        Index('uq_run_txn', 'run_id', 'txn_id', unique=True),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'acc_prvdr_code': self.acc_prvdr_code,
            'acc_number': self.acc_number,
            'txn_id': self.txn_id,
            'txn_date': self.txn_date.isoformat() if self.txn_date else None,
            'txn_type': self.txn_type,
            'description': self.description,
            'from_acc': self.from_acc,
            'to_acc': self.to_acc,
            'status': self.status,
            'txn_direction': self.txn_direction,
            'amount': float(self.amount) if self.amount else None,
            'fee': float(self.fee) if self.fee else None,
            'balance': float(self.balance) if self.balance else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
