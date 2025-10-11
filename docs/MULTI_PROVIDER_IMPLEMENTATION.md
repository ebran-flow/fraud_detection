# Multi-Provider Implementation Guide
## Separate Tables Architecture

## Overview

This architecture uses **provider-specific tables** for raw and processed data, while sharing metadata and summary tables. This allows each provider to have its own schema optimized for its data format.

## Table Structure

```
Provider-Specific (Different Schemas):
  - uatl_raw_statements
  - uatl_processed_statements
  - umtn_raw_statements
  - umtn_processed_statements

Shared (Normalized Data):
  - metadata (with acc_prvdr_code column)
  - summary (with acc_prvdr_code column)
```

## Benefits

✅ **Different Formats**: Each provider can have completely different columns
✅ **No NULL Pollution**: No unused columns full of NULLs
✅ **Clear Separation**: Easy to understand which fields belong to which provider
✅ **Flexible**: Add UMTN-specific columns without affecting UATL
✅ **Shared Logic**: Metadata and Summary still shared for unified reporting

## Implementation Strategy

### 1. Create Provider-Specific Models

**File: `backend/app/models/providers/__init__.py`**
```python
from .uatl import UATLRawStatement, UATLProcessedStatement
from .umtn import UMTNRawStatement, UMTNProcessedStatement
```

**File: `backend/app/models/providers/uatl.py`**
```python
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, Text, SmallInteger
from ..base import Base

class UATLRawStatement(Base):
    __tablename__ = 'uatl_raw_statements'

    id = Column(BigInteger, primary_key=True)
    run_id = Column(String(64), nullable=False)
    acc_number = Column(String(64))
    txn_id = Column(String(128))
    # ... Airtel-specific fields
    pdf_format = Column(SmallInteger)  # 1 or 2
    # ...

class UATLProcessedStatement(Base):
    __tablename__ = 'uatl_processed_statements'
    # ... similar structure
```

**File: `backend/app/models/providers/umtn.py`**
```python
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, Text
from ..base import Base

class UMTNRawStatement(Base):
    __tablename__ = 'umtn_raw_statements'

    id = Column(BigInteger, primary_key=True)
    run_id = Column(String(64), nullable=False)
    acc_number = Column(String(64))
    # ... MTN-specific fields (may differ from Airtel)
    # merchant_id = Column(String(64))
    # service_code = Column(String(32))
    # ...

class UMTNProcessedStatement(Base):
    __tablename__ = 'umtn_processed_statements'
    # ... similar structure
```

### 2. Create Provider Factory Pattern

**File: `backend/app/services/provider_factory.py`**
```python
"""
Provider Factory - Routes to correct tables based on provider code
"""
from typing import Type
from ..models.base import Base
from ..models.providers.uatl import UATLRawStatement, UATLProcessedStatement
from ..models.providers.umtn import UMTNRawStatement, UMTNProcessedStatement


class ProviderFactory:
    """Factory for getting provider-specific models"""

    PROVIDERS = {
        'UATL': {
            'raw': UATLRawStatement,
            'processed': UATLProcessedStatement,
        },
        'UMTN': {
            'raw': UMTNRawStatement,
            'processed': UMTNProcessedStatement,
        }
    }

    @classmethod
    def get_raw_model(cls, provider_code: str) -> Type[Base]:
        """Get raw statements model for provider"""
        if provider_code not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_code}")
        return cls.PROVIDERS[provider_code]['raw']

    @classmethod
    def get_processed_model(cls, provider_code: str) -> Type[Base]:
        """Get processed statements model for provider"""
        if provider_code not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_code}")
        return cls.PROVIDERS[provider_code]['processed']

    @classmethod
    def is_supported(cls, provider_code: str) -> bool:
        """Check if provider is supported"""
        return provider_code in cls.PROVIDERS
```

### 3. Update CRUD Service

**File: `backend/app/services/crud.py`**
```python
from .provider_factory import ProviderFactory

def check_run_id_exists(db: Session, run_id: str, provider_code: str) -> bool:
    """Check if run_id exists for given provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    return db.query(RawModel).filter(RawModel.run_id == run_id).first() is not None

def get_raw_statements_by_run_id(db: Session, run_id: str, provider_code: str):
    """Get raw statements for provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    return db.query(RawModel).filter(RawModel.run_id == run_id).order_by(RawModel.txn_date).all()

def bulk_create_raw(db: Session, provider_code: str, data_list: List[Dict]):
    """Bulk insert raw statements for provider"""
    RawModel = ProviderFactory.get_raw_model(provider_code)
    instances = [RawModel(**data) for data in data_list]
    db.bulk_save_objects(instances, return_defaults=True)
    db.flush()
    return instances
```

### 4. Create Provider-Specific Parsers

**File: `backend/app/services/parsers/__init__.py`**
```python
from .uatl_parser import parse_uatl_pdf
from .umtn_parser import parse_umtn_pdf

def get_parser(provider_code: str):
    """Get parser function for provider"""
    parsers = {
        'UATL': parse_uatl_pdf,
        'UMTN': parse_umtn_pdf,
    }
    if provider_code not in parsers:
        raise ValueError(f"No parser for provider: {provider_code}")
    return parsers[provider_code]
```

**File: `backend/app/services/parsers/uatl_parser.py`**
```python
"""Airtel-specific PDF parser - reuses existing logic"""
import sys
from pathlib import Path

# Import existing parsing logic
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from process_statements import extract_data_from_pdf, compute_balance_summary
from fraud import get_metadata as extract_pdf_metadata

def parse_uatl_pdf(pdf_path: str, run_id: str):
    """Parse Airtel PDF - reuses existing logic"""
    df, acc_number = extract_data_from_pdf(pdf_path)

    # Convert to list of dicts for UATL model
    raw_statements = []
    for idx, row in df.iterrows():
        raw_stmt = {
            'run_id': run_id,
            'acc_number': acc_number,
            'txn_id': str(row.get('txn_id')),
            'txn_date': row['txn_date'],
            'txn_type': row.get('txn_type'),
            'description': str(row.get('description', '')),
            'from_acc': row.get('from_acc'),
            'to_acc': row.get('to_acc'),
            'status': str(row.get('status', '')),
            'txn_direction': str(row.get('txn_direction', '')),
            'amount': float(row['amount']) if row['amount'] is not None else None,
            'fee': float(row['fee']) if row['fee'] is not None else 0.0,
            'balance': float(row['balance']) if row['balance'] is not None else None,
            'pdf_format': df.iloc[0].get('pdf_format', 1),
        }
        raw_statements.append(raw_stmt)

    # Get metadata
    pdf_meta = extract_pdf_metadata(pdf_path)
    balance_summary = compute_balance_summary(df, acc_number, pdf_path)

    metadata = {
        'run_id': run_id,
        'acc_prvdr_code': 'UATL',
        'acc_number': acc_number,
        'pdf_format': df.iloc[0].get('pdf_format', 1),
        'num_rows': len(df),
        # ... rest of metadata
    }

    return raw_statements, metadata
```

**File: `backend/app/services/parsers/umtn_parser.py`**
```python
"""MTN-specific PDF parser"""

def parse_umtn_pdf(pdf_path: str, run_id: str):
    """Parse MTN PDF - implement MTN-specific logic here"""
    # TODO: Implement MTN-specific parsing
    # This will have different logic than Airtel

    # Example structure:
    raw_statements = []
    # ... MTN parsing logic

    metadata = {
        'run_id': run_id,
        'acc_prvdr_code': 'UMTN',
        'acc_number': '...',
        # ... MTN metadata
    }

    return raw_statements, metadata
```

### 5. Update Upload Endpoint

**File: `backend/app/api/v1/upload.py`**
```python
from ...services.provider_factory import ProviderFactory
from ...services.parsers import get_parser
from ...services.crud import bulk_create_raw, check_run_id_exists

@router.post("/upload")
async def upload_pdfs(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    results = []

    for file in files:
        run_id = extract_run_id_from_filename(file.filename)

        # Get provider code from mapper
        mapping = get_mapping_by_run_id(run_id)
        provider_code = mapping.get('acc_prvdr_code', 'UATL') if mapping else 'UATL'

        # Check if already exists (provider-specific table)
        if check_run_id_exists(db, run_id, provider_code):
            results.append(UploadFileResult(
                filename=file.filename,
                run_id=run_id,
                status='skipped',
                message='Already exists'
            ))
            continue

        # Save PDF file
        pdf_path = save_uploaded_file(file)

        try:
            # Get provider-specific parser
            parser = get_parser(provider_code)
            raw_statements, metadata = parser(pdf_path, run_id)

            # Enrich metadata from mapper
            metadata = enrich_metadata_with_mapper(metadata, run_id)

            # Insert metadata (shared table)
            create(db, Metadata, metadata)

            # Bulk insert raw statements (provider-specific table)
            bulk_create_raw(db, provider_code, raw_statements)

            db.commit()

            results.append(UploadFileResult(
                filename=file.filename,
                run_id=run_id,
                status='success',
                message=f'Parsed {len(raw_statements)} transactions'
            ))

        except Exception as e:
            db.rollback()
            results.append(UploadFileResult(
                filename=file.filename,
                run_id=run_id,
                status='error',
                message=str(e)
            ))

    return UploadResponse(...)
```

### 6. Update Processor Service

**File: `backend/app/services/processor.py`**
```python
from .provider_factory import ProviderFactory

def process_statement(db: Session, run_id: str, provider_code: str):
    """Process statement - provider-agnostic"""

    # Get provider-specific models
    RawModel = ProviderFactory.get_raw_model(provider_code)
    ProcessedModel = ProviderFactory.get_processed_model(provider_code)

    # Load raw statements (provider-specific table)
    raw_statements = db.query(RawModel).filter(RawModel.run_id == run_id).all()

    # Load metadata (shared table)
    metadata = get_metadata_by_run_id(db, run_id)

    # Process (same logic for all providers)
    df = pd.DataFrame([stmt.__dict__ for stmt in raw_statements])
    df = detect_duplicates(df)
    df = calculate_running_balance(df, metadata.pdf_format)

    # Create processed statements (provider-specific table)
    processed_data = []
    for idx, row in df.iterrows():
        processed_data.append({
            'raw_id': row['id'],
            'run_id': run_id,
            'acc_number': row['acc_number'],
            # ... fields
        })

    # Bulk insert (provider-specific table)
    processed_instances = [ProcessedModel(**data) for data in processed_data]
    db.bulk_save_objects(processed_instances)

    # Generate summary (shared table)
    summary_data = generate_summary(df, metadata, run_id)
    summary_data['acc_prvdr_code'] = provider_code
    create(db, Summary, summary_data)

    db.commit()

    return {'status': 'success', ...}
```

### 7. Update Export Service

**File: `backend/app/services/export.py`**
```python
from sqlalchemy import union_all
from .provider_factory import ProviderFactory

def export_processed_statements_csv(db: Session, provider_codes: List[str] = None, ...):
    """Export processed statements - can span multiple providers"""

    if not provider_codes:
        provider_codes = ['UATL', 'UMTN']  # All supported

    # Build union query across provider tables
    queries = []
    for provider_code in provider_codes:
        ProcessedModel = ProviderFactory.get_processed_model(provider_code)
        query = db.query(
            ProcessedModel.run_id,
            ProcessedModel.acc_number,
            ProcessedModel.txn_date,
            ProcessedModel.amount,
            ProcessedModel.balance,
            # ... other fields
        ).filter(...)  # Apply filters
        queries.append(query)

    # Union all providers
    if len(queries) > 1:
        final_query = union_all(*[q.statement for q in queries])
        statements = db.execute(final_query).fetchall()
    else:
        statements = queries[0].all()

    # Convert to CSV
    df = pd.DataFrame(statements)
    return df.to_csv(index=False)
```

## Database Views for Unified Queries

The schema includes views for easy cross-provider queries:

```sql
-- Query all providers at once
SELECT * FROM all_raw_statements WHERE txn_date > '2024-01-01';

-- Provider-specific query
SELECT * FROM uatl_raw_statements WHERE run_id = '68babf7f23139';

-- Cross-provider analytics
SELECT
    acc_prvdr_code,
    COUNT(*) as transactions,
    SUM(amount) as total_amount
FROM all_raw_statements
GROUP BY acc_prvdr_code;
```

## Adding a New Provider

### Step 1: Database Schema
```sql
-- Add new provider tables
CREATE TABLE IF NOT EXISTS new_provider_raw_statements (...);
CREATE TABLE IF NOT EXISTS new_provider_processed_statements (...);
```

### Step 2: Models
```python
# backend/app/models/providers/new_provider.py
class NewProviderRawStatement(Base):
    __tablename__ = 'new_provider_raw_statements'
    # ... provider-specific schema
```

### Step 3: Register in Factory
```python
# backend/app/services/provider_factory.py
PROVIDERS = {
    'UATL': {...},
    'UMTN': {...},
    'NEWP': {
        'raw': NewProviderRawStatement,
        'processed': NewProviderProcessedStatement,
    }
}
```

### Step 4: Create Parser
```python
# backend/app/services/parsers/new_provider_parser.py
def parse_new_provider_pdf(pdf_path: str, run_id: str):
    # Provider-specific parsing logic
    ...
```

### Step 5: Register Parser
```python
# backend/app/services/parsers/__init__.py
parsers = {
    'UATL': parse_uatl_pdf,
    'UMTN': parse_umtn_pdf,
    'NEWP': parse_new_provider_pdf,
}
```

**Done!** No changes to endpoints or core logic needed.

## Code Reuse Strategy

**Shared Code** (all providers use same logic):
- ✅ Duplicate detection algorithm
- ✅ Balance verification logic
- ✅ Summary generation
- ✅ Export functionality
- ✅ API endpoints
- ✅ CRUD operations (via factory)

**Provider-Specific Code** (different per provider):
- ❌ PDF parsing logic
- ❌ Table schemas
- ❌ Field mappings
- ❌ Special transaction rules (optional)

## Summary

| Aspect | Implementation |
|--------|----------------|
| Raw Data | Separate tables per provider |
| Processed Data | Separate tables per provider |
| Metadata | Shared table with provider code |
| Summary | Shared table with provider code |
| Code Reuse | Factory pattern + shared services |
| New Provider | 5 steps (schema, model, factory, parser, register) |
| Queries | Use views for unified access |
| API | Provider-agnostic via factory |

This architecture gives you:
- ✅ **Flexibility**: Different schemas per provider
- ✅ **Maintainability**: Shared business logic
- ✅ **Scalability**: Easy to add new providers
- ✅ **Performance**: Optimized per-provider tables
- ✅ **Clarity**: Clear separation of provider data
