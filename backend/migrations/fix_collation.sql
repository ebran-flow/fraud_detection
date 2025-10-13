-- Fix collation mismatch in unified_statements view
-- This resolves: Illegal mix of collations (utf8mb4_0900_ai_ci,COERCIBLE) and (utf8mb4_unicode_ci,COERCIBLE)

DROP VIEW IF EXISTS unified_statements;

CREATE VIEW unified_statements AS
SELECT
    m.id AS metadata_id,
    m.run_id,
    m.acc_number,
    m.acc_prvdr_code,
    m.format,
    m.mime,
    m.submitted_date,
    m.start_date,
    m.end_date,
    m.rm_name,
    m.num_rows,
    m.parsing_status,
    m.parsing_error,
    m.created_at AS imported_at,

    -- Consolidated status - CONVERT output to utf8mb4_unicode_ci to match table collation
    -- This ensures WHERE clauses work correctly: WHERE status = 'FLAGGED'
    CONVERT(
        CASE
            WHEN m.parsing_status = 'FAILED' COLLATE utf8mb4_unicode_ci THEN 'IMPORT_FAILED'
            WHEN s.id IS NULL THEN 'IMPORTED'
            WHEN s.verification_status = 'FAIL' COLLATE utf8mb4_unicode_ci
                 AND s.balance_match = 'Failed' COLLATE utf8mb4_unicode_ci THEN 'FLAGGED'
            WHEN s.verification_status = 'FAIL' COLLATE utf8mb4_unicode_ci THEN 'VERIFICATION_FAILED'
            WHEN s.verification_status = 'PASS' COLLATE utf8mb4_unicode_ci
                 AND s.balance_match = 'Failed' COLLATE utf8mb4_unicode_ci THEN 'VERIFIED_WITH_WARNINGS'
            WHEN s.verification_status = 'PASS' COLLATE utf8mb4_unicode_ci THEN 'VERIFIED'
            ELSE 'IMPORTED'
        END
    USING utf8mb4) COLLATE utf8mb4_unicode_ci AS status,

    -- Processing status - CONVERT output to utf8mb4_unicode_ci
    CONVERT(
        CASE
            WHEN s.id IS NOT NULL THEN 'PROCESSED'
            ELSE 'IMPORTED'
        END
    USING utf8mb4) COLLATE utf8mb4_unicode_ci AS processing_status,

    s.verification_status,
    s.verification_reason,
    s.balance_match,
    s.duplicate_count,
    s.missing_days_detected,
    s.gap_related_balance_changes,
    s.created_at AS processed_at,
    s.balance_diff_changes,
    s.balance_diff_change_ratio,
    s.calculated_closing_balance,
    m.last_balance AS stmt_closing_balance,
    m.meta_title,
    m.meta_author,
    m.meta_producer,
    m.meta_created_at,
    m.meta_modified_at
FROM metadata m
LEFT JOIN summary s ON m.run_id = s.run_id
ORDER BY m.created_at DESC;
