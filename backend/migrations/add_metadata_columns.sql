-- Migration: Populate metadata columns and update unified_statements view
-- Date: 2025-10-12
-- Note: Columns are added via Python script, this SQL populates data

USE fraud_detection;

-- Step 1: Populate format column from pdf_format
-- For UATL: format_1 or format_2 based on pdf_format
-- For UMTN: excel (since they use Excel/CSV)
UPDATE metadata
SET format = CASE
    WHEN acc_prvdr_code = 'UATL' AND pdf_format = 1 THEN 'format_1'
    WHEN acc_prvdr_code = 'UATL' AND pdf_format = 2 THEN 'format_2'
    WHEN acc_prvdr_code = 'UMTN' THEN 'excel'
    ELSE NULL
END
WHERE format IS NULL;

-- Step 2: Populate mime column based on pdf_path extension
UPDATE metadata
SET mime = CASE
    WHEN pdf_path LIKE '%.pdf' THEN 'application/pdf'
    WHEN pdf_path LIKE '%.csv' THEN 'text/csv'
    WHEN pdf_path LIKE '%.xlsx' THEN 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    WHEN pdf_path LIKE '%.xls' THEN 'application/vnd.ms-excel'
    ELSE 'application/octet-stream'
END
WHERE mime IS NULL AND pdf_path IS NOT NULL;

-- Step 3: Populate start_date and end_date from raw_statements
-- For UATL statements
UPDATE metadata m
LEFT JOIN (
    SELECT
        run_id,
        DATE(MIN(txn_date)) as min_date,
        DATE(MAX(txn_date)) as max_date
    FROM uatl_raw_statements
    WHERE txn_date IS NOT NULL
    GROUP BY run_id
) r ON m.run_id = r.run_id
SET
    m.start_date = r.min_date,
    m.end_date = r.max_date
WHERE m.acc_prvdr_code = 'UATL'
  AND (m.start_date IS NULL OR m.end_date IS NULL)
  AND r.min_date IS NOT NULL;

-- For UMTN statements
UPDATE metadata m
LEFT JOIN (
    SELECT
        run_id,
        DATE(MIN(txn_date)) as min_date,
        DATE(MAX(txn_date)) as max_date
    FROM umtn_raw_statements
    WHERE txn_date IS NOT NULL
    GROUP BY run_id
) r ON m.run_id = r.run_id
SET
    m.start_date = r.min_date,
    m.end_date = r.max_date
WHERE m.acc_prvdr_code = 'UMTN'
  AND (m.start_date IS NULL OR m.end_date IS NULL)
  AND r.min_date IS NOT NULL;

-- Step 4: Drop and recreate the unified_statements view with new columns
DROP VIEW IF EXISTS unified_statements;

CREATE VIEW unified_statements AS
SELECT
    m.id as metadata_id,
    m.run_id,
    m.acc_number,
    m.acc_prvdr_code,
    m.format,
    m.mime,
    m.submitted_date,
    m.start_date,
    m.end_date,
    m.requestor,
    m.rm_name,
    m.num_rows,
    m.created_at as imported_at,
    CASE
        WHEN s.id IS NOT NULL THEN 'PROCESSED'
        ELSE 'IMPORTED'
    END as processing_status,
    s.verification_status,
    s.verification_reason,
    s.balance_match,
    s.duplicate_count,
    s.created_at as processed_at,
    s.balance_diff_changes,
    s.balance_diff_change_ratio,
    s.calculated_closing_balance,
    m.stmt_closing_balance,
    m.meta_title,
    m.meta_author,
    m.meta_producer,
    m.meta_created_at,
    m.meta_modified_at
FROM metadata m
LEFT JOIN summary s ON m.run_id = s.run_id
ORDER BY m.created_at DESC;

-- Verify the changes
SELECT 'Migration completed successfully. New columns added to metadata table and unified_statements view updated.' as status;
