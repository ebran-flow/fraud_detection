"""
UMTN (MTN Uganda) Models
Handles MTN Mobile Money statements with commission and float tracking
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, Text, TIMESTAMP, Index, Boolean, Integer, ForeignKey
from sqlalchemy.sql import func
from ..base import Base


class UMTNRawStatement(Base):
    __tablename__ = 'umtn_raw_statements'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False)
    acc_number = Column(String(64))
    txn_id = Column(String(128))
    txn_date = Column(DateTime)
    txn_type = Column(String(64))         # BILL PAYMENT, CASH_IN, CASH_OUT, etc.
    description = Column(Text)
    from_acc = Column(String(64))
    to_acc = Column(String(128))          # Can be longer (includes @domain)
    status = Column(String(32))           # Always 'success' for UMTN
    txn_direction = Column(String(16))    # Derived from amount sign
    amount = Column(Numeric(18, 2))       # Signed: negative=outgoing, positive=incoming
    fee = Column(Numeric(18, 2), default=0)
    # UMTN-specific fields
    commission_amount = Column(Numeric(18, 2))
    tax = Column(Numeric(18, 2))
    commission_receiving_no = Column(String(64))
    commission_balance = Column(Numeric(18, 2))
    float_balance = Column(Numeric(18, 2))  # This is the balance!
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_umtn_acc_number', 'acc_number'),
        Index('idx_umtn_run_id', 'run_id'),
        Index('idx_umtn_txn_date', 'txn_date'),
        Index('uq_umtn_run_txn', 'run_id', 'txn_id', unique=True),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'run_id': self.run_id,
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
            'commission_amount': float(self.commission_amount) if self.commission_amount else None,
            'tax': float(self.tax) if self.tax else None,
            'commission_receiving_no': self.commission_receiving_no,
            'commission_balance': float(self.commission_balance) if self.commission_balance else None,
            'float_balance': float(self.float_balance) if self.float_balance else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UMTNProcessedStatement(Base):
    __tablename__ = 'umtn_processed_statements'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_id = Column(BigInteger, ForeignKey('umtn_raw_statements.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(String(64))
    acc_number = Column(String(64))
    txn_id = Column(String(128))
    txn_date = Column(DateTime)
    txn_type = Column(String(64))
    description = Column(Text)
    status = Column(String(32))
    amount = Column(Numeric(18, 2))
    fee = Column(Numeric(18, 2), default=0)
    float_balance = Column(Numeric(18, 2))     # UMTN uses float_balance
    commission_amount = Column(Numeric(18, 2))
    commission_balance = Column(Numeric(18, 2))
    is_duplicate = Column(Boolean, default=False)
    is_special_txn = Column(Boolean, default=False)
    special_txn_type = Column(String(64))
    calculated_running_balance = Column(Numeric(18, 2))
    balance_diff = Column(Numeric(18, 2))
    balance_diff_change_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_umtn_proc_run_id', 'run_id'),
        Index('idx_umtn_proc_acc_number', 'acc_number'),
        Index('idx_umtn_proc_txn_date', 'txn_date'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'raw_id': self.raw_id,
            'run_id': self.run_id,
            'acc_number': self.acc_number,
            'txn_id': self.txn_id,
            'txn_date': self.txn_date.isoformat() if self.txn_date else None,
            'txn_type': self.txn_type,
            'description': self.description,
            'status': self.status,
            'amount': float(self.amount) if self.amount else None,
            'fee': float(self.fee) if self.fee else None,
            'float_balance': float(self.float_balance) if self.float_balance else None,
            'commission_amount': float(self.commission_amount) if self.commission_amount else None,
            'commission_balance': float(self.commission_balance) if self.commission_balance else None,
            'is_duplicate': self.is_duplicate,
            'is_special_txn': self.is_special_txn,
            'special_txn_type': self.special_txn_type,
            'calculated_running_balance': float(self.calculated_running_balance) if self.calculated_running_balance else None,
            'balance_diff': float(self.balance_diff) if self.balance_diff else None,
            'balance_diff_change_count': self.balance_diff_change_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
