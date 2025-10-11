-- Fraud Detection Database Schema
-- Database: fraud_detection
-- Execute this on your existing MySQL instance (port 3307)

CREATE DATABASE IF NOT EXISTS fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE fraud_detection;

-- 1. Raw Statements Table
-- Stores minimally processed transactions from PDF parsing
-- Supports multiple providers (UATL, UMTN, etc.) in single table
CREATE TABLE IF NOT EXISTS raw_statements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL,
  acc_prvdr_code VARCHAR(16),    -- Provider code: UATL, UMTN, etc.
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  txn_type VARCHAR(64),
  description TEXT,
  from_acc VARCHAR(64),
  to_acc VARCHAR(64),
  status VARCHAR(32),            -- 'success','failed', etc.
  txn_direction VARCHAR(16),     -- 'Credit', 'Debit' (optional for format1)
  amount DECIMAL(18,2),          -- signed amount, negative = debit, positive = credit
  fee DECIMAL(18,2) DEFAULT 0,
  balance DECIMAL(18,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_run_txn (run_id, txn_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_run_id (run_id),
  INDEX idx_provider (acc_prvdr_code),
  INDEX idx_provider_acc (acc_prvdr_code, acc_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Metadata Table
-- Stores document-level and parsing-related info (one row per run_id)
CREATE TABLE IF NOT EXISTS metadata (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL UNIQUE,
  acc_prvdr_code VARCHAR(16),
  acc_number VARCHAR(64),
  pdf_format TINYINT,            -- 1 or 2
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
  pdf_path VARCHAR(512),         -- Path to stored PDF file
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_acc_number (acc_number),
  INDEX idx_run_id (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Processed Statements Table
-- Adds processing-level information for transactions
-- Supports multiple providers (UATL, UMTN, etc.) in single table
CREATE TABLE IF NOT EXISTS processed_statements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_id BIGINT NOT NULL,                -- FK to raw_statements.id
  run_id VARCHAR(64),
  acc_prvdr_code VARCHAR(16),            -- Provider code: UATL, UMTN, etc.
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
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_run_id (run_id),
  INDEX idx_acc_number (acc_number),
  INDEX idx_provider (acc_prvdr_code),
  INDEX idx_provider_acc (acc_prvdr_code, acc_number),
  FOREIGN KEY (raw_id) REFERENCES raw_statements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Summary Table
-- Provides final-level verification and balance summary (one row per run_id)
CREATE TABLE IF NOT EXISTS summary (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id VARCHAR(64) NOT NULL UNIQUE,
  acc_number VARCHAR(64),
  acc_prvdr_code VARCHAR(16),
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
  INDEX idx_acc_number (acc_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
