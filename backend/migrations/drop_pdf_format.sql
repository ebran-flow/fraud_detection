-- Cleanup: Drop pdf_format column after confirming format column is working
-- Run this ONLY after verifying that the format column is populated correctly
-- Date: 2025-10-12

USE fraud_detection;

-- Before dropping, let's verify the format column is populated
SELECT
    COUNT(*) as total_records,
    SUM(CASE WHEN format IS NOT NULL THEN 1 ELSE 0 END) as has_format,
    SUM(CASE WHEN pdf_format IS NOT NULL THEN 1 ELSE 0 END) as has_pdf_format
FROM metadata;

-- Uncomment the line below ONLY after verifying the data above looks good
ALTER TABLE metadata DROP COLUMN pdf_format;

SELECT '✅ To drop pdf_format, uncomment the ALTER TABLE statement in this file' as reminder;
