# Customer Details Integration

## Overview
This document describes how to integrate customer information from the Flow API database with the fraud detection system.

## Problem Statement
Currently, the fraud detection database only contains statement data (metadata, raw_statements, processed_statements, summary). To link fraud-flagged statements back to customers, we need to retrieve customer details from the Flow API database.

## Entity Relationship Structure

### Database: Flow API (flow_api)
Contains customer and statement request data:
- `partner_acc_stmt_requests` - Statement requests submitted by customers
- `customer_statements` - Customer statement records (can be a linking entity)
- `leads` - Customer lead information
- `reassessment_results` - Reassessment information
- `persons` - RM (Relationship Manager) information

### Database: Fraud Detection (fraud_detection)
Contains statement analysis data:
- `metadata` - Statement metadata (linked by run_id = flow_req_id)
- `raw_statements` - Raw transaction data
- `processed_statements` - Processed transaction data
- `summary` - Statement summaries with verification results

## Entity Linking Chain

```
partner_acc_stmt_requests (flow_req_id)
    ↓
    ├── entity = 'customer_statement' → customer_statements
    │       ↓
    │       ├── entity = 'lead' → leads (cust_id)
    │       └── entity = 'reassessment_result' → reassessment_results (cust_id)
    │
    ├── entity = 'lead' → leads (cust_id)
    │
    └── entity = 'reassessment_result' → reassessment_results (cust_id)
```

### Link Details

**1. Direct Links (partner_acc_stmt_requests → final entity)**
- `s.entity = 'lead' AND s.entity_id = leads.id`
- `s.entity = 'reassessment_result' AND s.entity_id = reassessment_results.id`

**2. Indirect Links (through customer_statements)**
- `s.entity = 'customer_statement' AND s.entity_id = customer_statements.id`
  - Then: `cs.entity = 'lead' AND cs.entity_id = leads.id`
  - Or: `cs.entity = 'reassessment_result' AND cs.entity_id = reassessment_results.id`

**3. Customer ID Retrieval**
- From `leads.cust_id`
- Or from `reassessment_results.cust_id`

## Cross-Database Linking

### Key Field: `run_id` / `flow_req_id`
Links fraud_detection to Flow API:
```sql
metadata.run_id = partner_acc_stmt_requests.flow_req_id
```

## Solution Components

### 1. SQL Query (`scripts/analysis/get_customer_details.sql`)
Comprehensive query that:
- Joins all entity relationships
- Handles both direct and indirect links
- Retrieves customer information
- Resolves to final `cust_id`

### 2. Python Script (`scripts/analysis/export_customer_details.py`)
Features:
- Executes the customer details query
- Exports to CSV or JSON
- Analyzes entity distribution
- Provides coverage statistics

### 3. Cross-Database Integration Script (TODO)
Needs to be created to:
- Connect to both databases
- Join fraud_detection data with Flow API data
- Create unified customer + fraud view

## Required Credentials

### Flow API Database
```env
FLOW_DB_HOST=<host>
FLOW_DB_PORT=3306
FLOW_DB_USER=<user>
FLOW_DB_PASSWORD=<password>
FLOW_DB_NAME=flow_api
```

### Fraud Detection Database
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=fraud_user
DB_PASSWORD=fraud_password
DB_NAME=fraud_detection
```

## Usage

### Step 1: Export Customer Details from Flow API
```bash
# Connect to Flow API database and export
python scripts/analysis/export_customer_details.py \
    --output customer_details.csv \
    --cutoff-date "2025-10-10 19:07:24" \
    --max-id 30668
```

### Step 2: Create Cross-Database View (TODO)
```python
# scripts/analysis/create_customer_fraud_view.py
# This script will:
# 1. Read customer_details.csv
# 2. Join with fraud_detection.metadata on run_id
# 3. Create unified view with customer + fraud flags
```

### Step 3: Query Unified Data
```sql
SELECT
    c.cust_id,
    c.lead_first_name,
    c.lead_last_name,
    c.lead_mobile,
    c.lead_biz_name,
    m.run_id,
    m.acc_number,
    s.verification_status,
    s.balance_match,
    s.duplicate_count,
    s.quality_issues_count
FROM customer_details c
INNER JOIN fraud_detection.metadata m ON c.run_id = m.run_id
LEFT JOIN fraud_detection.summary s ON m.run_id = s.run_id
WHERE s.verification_status = 'FAIL'
```

## Customer Data Fields

### From Leads
- `cust_id` - Unique customer identifier
- `mobile_num` - Customer mobile number
- `biz_name` - Business name
- `first_name`, `last_name` - Customer name
- `id_proof_num` - ID proof number
- `national_id` - National ID
- `location` - Customer location
- `territory` - Sales territory
- `status` - Lead status
- `profile_status` - Profile status
- `lead_date`, `assessment_date`, `onboarded_date` - Timeline

### From Reassessment Results
- `cust_id` - Unique customer identifier
- `prev_limit` - Previous credit limit
- `status` - Reassessment status
- `type` - Reassessment type

### From Customer Statements
- `holder_name` - Account holder name
- `distributor_code` - Distributor code
- `acc_ownership` - Account ownership type
- `result` - Assessment result
- `score` - Credit score
- `limit` - Credit limit
- `assessment_date` - When assessed

### From RM (Persons)
- `rm_id` - Relationship manager ID
- `rm_name` - RM full name

## Next Steps

1. **Get Flow API database credentials** - Required to access customer data
2. **Test customer details export** - Verify entity linking works correctly
3. **Create cross-database integration** - Join customer + fraud data
4. **Build customer fraud report** - Show which customers have flagged statements
5. **Implement real-time lookup** - API to get customer details for a run_id

## Example Output

```csv
stmt_request_id,run_id,acc_number,cust_id,lead_first_name,lead_last_name,lead_mobile,lead_biz_name,verification_status,balance_match
12345,68b5866aef104,256700123456,CUST001,John,Doe,0700123456,Doe Enterprises,FAIL,Failed
12346,68b69a2e794cb,256700234567,CUST002,Jane,Smith,0700234567,Smith Trading,PASS,Passed
```

## Security Considerations

1. **Data Access** - Ensure proper permissions to access Flow API database
2. **Data Privacy** - Customer data should be handled securely
3. **Audit Trail** - Log all customer data exports
4. **Data Retention** - Follow data retention policies
5. **Cross-Database Queries** - Use read-only accounts where possible

## Performance Considerations

1. **Batch Processing** - Export customer details in batches
2. **Caching** - Cache customer lookups to avoid repeated queries
3. **Indexing** - Ensure indexes on run_id/flow_req_id for fast joins
4. **Materialized Views** - Consider creating materialized view for frequently accessed data
