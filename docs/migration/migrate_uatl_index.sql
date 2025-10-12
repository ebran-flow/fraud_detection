-- Migration: Remove unique constraint and add index on txn_id
-- Date: 2025-10-12
-- Purpose: Allow duplicate txn_id within same run_id (for legitimate duplicate transactions)

-- Step 1: Drop the unique constraint
ALTER TABLE uatl_raw_statements DROP INDEX uq_uatl_run_txn;

-- Step 2: Add non-unique index on txn_id for performance
CREATE INDEX idx_uatl_txn_id ON uatl_raw_statements(txn_id);

-- Verify changes
SHOW INDEX FROM uatl_raw_statements WHERE Key_name IN ('uq_uatl_run_txn', 'idx_uatl_txn_id');
