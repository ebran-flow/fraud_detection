-- Fraud Detection Database Schema - Multi-Provider Version
-- Database: fraud_detection
-- Supports multiple providers with different data formats

CREATE DATABASE IF NOT EXISTS fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE fraud_detection;

-- ============================================================================
-- UATL (Airtel Uganda) Tables
-- ============================================================================

-- 1. UATL Raw Statements
-- Stores Airtel-specific transaction data (Format 1 & 2)
CREATE TABLE IF NOT EXISTS uatl_raw_statements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL,
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  txn_type VARCHAR(64),
  description TEXT,
  from_acc VARCHAR(64),
  to_acc VARCHAR(64),
  status VARCHAR(32),            -- 'success','failed', etc.
  txn_direction VARCHAR(16),     -- 'Credit', 'Debit' (Airtel Format 1)
  amount DECIMAL(18,2),          -- signed amount for Format 2
  fee DECIMAL(18,2) DEFAULT 0,
  balance DECIMAL(18,2),
  pdf_format TINYINT,            -- 1 or 2 (Airtel specific)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_run_txn (run_id, txn_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_run_id (run_id),
  INDEX idx_txn_date (txn_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. UATL Processed Statements
-- Airtel-specific processed data with fraud detection
CREATE TABLE IF NOT EXISTS uatl_processed_statements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_id BIGINT NOT NULL,
  run_id VARCHAR(64),
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  txn_type VARCHAR(64),
  description TEXT,
  status VARCHAR(32),
  amount DECIMAL(18,2),
  fee DECIMAL(18,2) DEFAULT 0,
  balance DECIMAL(18,2),
  is_duplicate BOOLEAN DEFAULT FALSE,
  is_special_txn BOOLEAN DEFAULT FALSE,
  special_txn_type VARCHAR(64),    -- Commission Disbursement, Reversal, etc.
  calculated_running_balance DECIMAL(18,2),
  balance_diff DECIMAL(18,2),
  balance_diff_change_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_run_id (run_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_txn_date (txn_date),
  FOREIGN KEY (raw_id) REFERENCES uatl_raw_statements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- UMTN (MTN Uganda) Tables
-- ============================================================================

-- 3. UMTN Raw Statements
-- Stores MTN-specific transaction data (may have different structure)
CREATE TABLE IF NOT EXISTS umtn_raw_statements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL,
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  txn_type VARCHAR(64),
  description TEXT,
  from_acc VARCHAR(64),
  to_acc VARCHAR(64),
  status VARCHAR(32),
  txn_direction VARCHAR(16),
  amount DECIMAL(18,2),
  fee DECIMAL(18,2) DEFAULT 0,
  balance DECIMAL(18,2),
  -- Add MTN-specific columns here as needed
  -- merchant_id VARCHAR(64),
  -- service_code VARCHAR(32),
  -- channel VARCHAR(32),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_run_txn (run_id, txn_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_run_id (run_id),
  INDEX idx_txn_date (txn_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. UMTN Processed Statements
-- MTN-specific processed data with fraud detection
CREATE TABLE IF NOT EXISTS umtn_processed_statements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_id BIGINT NOT NULL,
  run_id VARCHAR(64),
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  txn_type VARCHAR(64),
  description TEXT,
  status VARCHAR(32),
  amount DECIMAL(18,2),
  fee DECIMAL(18,2) DEFAULT 0,
  balance DECIMAL(18,2),
  is_duplicate BOOLEAN DEFAULT FALSE,
  is_special_txn BOOLEAN DEFAULT FALSE,
  special_txn_type VARCHAR(64),
  calculated_running_balance DECIMAL(18,2),
  balance_diff DECIMAL(18,2),
  balance_diff_change_count INT DEFAULT 0,
  -- Add MTN-specific processed columns here
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_run_id (run_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_txn_date (txn_date),
  FOREIGN KEY (raw_id) REFERENCES umtn_raw_statements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Shared Tables (All Providers)
-- ============================================================================

-- 5. Metadata Table (Shared across all providers)
-- Stores document-level and parsing-related info
CREATE TABLE IF NOT EXISTS metadata (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL UNIQUE,
  acc_prvdr_code VARCHAR(16) NOT NULL,  -- 'UATL', 'UMTN', etc.
  acc_number VARCHAR(64),
  pdf_format TINYINT,
  rm_name VARCHAR(256),
  num_rows INT,
  sheet_md5 VARCHAR(64),
  summary_opening_balance DECIMAL(18,2),
  summary_closing_balance DECIMAL(18,2),
  stmt_opening_balance DECIMAL(18,2),
  stmt_closing_balance DECIMAL(18,2),
  meta_title VARCHAR(512),
  meta_author VARCHAR(256),
  meta_producer VARCHAR(256),
  meta_created_at DATETIME,
  meta_modified_at DATETIME,
  pdf_path VARCHAR(512),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_acc_number (acc_number),
  INDEX idx_run_id (run_id),
  INDEX idx_provider (acc_prvdr_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Summary Table (Shared across all providers)
-- Provides final-level verification and balance summary
CREATE TABLE IF NOT EXISTS summary (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL UNIQUE,
  acc_prvdr_code VARCHAR(16) NOT NULL,  -- 'UATL', 'UMTN', etc.
  acc_number VARCHAR(64),
  rm_name VARCHAR(256),
  num_rows INT,
  sheet_md5 VARCHAR(64),
  summary_opening_balance DECIMAL(18,2),
  summary_closing_balance DECIMAL(18,2),
  stmt_opening_balance DECIMAL(18,2),
  stmt_closing_balance DECIMAL(18,2),
  duplicate_count INT DEFAULT 0,
  balance_match ENUM('Success','Failed'),
  verification_status VARCHAR(64),
  verification_reason TEXT,
  credits DECIMAL(18,2),
  debits DECIMAL(18,2),
  fees DECIMAL(18,2),
  charges DECIMAL(18,2),
  calculated_closing_balance DECIMAL(18,2),
  balance_diff_changes INT DEFAULT 0,
  balance_diff_change_ratio FLOAT DEFAULT 0.0,
  meta_title VARCHAR(512),
  meta_author VARCHAR(256),
  meta_producer VARCHAR(256),
  meta_created_at DATETIME,
  meta_modified_at DATETIME,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_run_id (run_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_provider (acc_prvdr_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Views for Unified Access (Optional)
-- ============================================================================

-- Unified view of all raw statements
CREATE OR REPLACE VIEW all_raw_statements AS
SELECT 'UATL' as acc_prvdr_code, id, run_id, acc_number, txn_id, txn_date,
       txn_type, description, status, amount, fee, balance, created_at
FROM uatl_raw_statements
UNION ALL
SELECT 'UMTN' as acc_prvdr_code, id, run_id, acc_number, txn_id, txn_date,
       txn_type, description, status, amount, fee, balance, created_at
FROM umtn_raw_statements;

-- Unified view of all processed statements
CREATE OR REPLACE VIEW all_processed_statements AS
SELECT 'UATL' as acc_prvdr_code, id, run_id, acc_number, txn_id, txn_date,
       description, status, amount, balance, is_duplicate, is_special_txn,
       calculated_running_balance, balance_diff, created_at
FROM uatl_processed_statements
UNION ALL
SELECT 'UMTN' as acc_prvdr_code, id, run_id, acc_number, txn_id, txn_date,
       description, status, amount, balance, is_duplicate, is_special_txn,
       calculated_running_balance, balance_diff, created_at
FROM umtn_processed_statements;
