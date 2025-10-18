-- MySQL dump 10.13  Distrib 8.0.43, for Linux (x86_64)
--
-- Host: localhost    Database: fraud_detection
-- ------------------------------------------------------
-- Server version	8.0.43-0ubuntu0.24.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `fraud_detection`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `fraud_detection` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `fraud_detection`;

--
-- Table structure for table `customer_details`
--

DROP TABLE IF EXISTS `customer_details`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customer_details` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `run_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'flow_req_id from partner_acc_stmt_requests',
  `stmt_request_id` bigint unsigned DEFAULT NULL COMMENT 'ID from partner_acc_stmt_requests',
  `acc_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Primary account number',
  `alt_acc_num` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Alternative account number',
  `acc_prvdr_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Provider code (UATL/UMTN)',
  `stmt_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Statement request status',
  `object_key` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'S3 object key',
  `lambda_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lambda processing status',
  `created_date` date DEFAULT NULL COMMENT 'Date of statement request',
  `created_at` datetime DEFAULT NULL COMMENT 'Timestamp of statement request',
  `rm_id` bigint unsigned DEFAULT NULL COMMENT 'ID of RM who created request',
  `rm_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Name of RM who created request',
  `direct_entity` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Direct entity type from request',
  `direct_entity_id` bigint unsigned DEFAULT NULL COMMENT 'Direct entity ID from request',
  `customer_statement_id` bigint unsigned DEFAULT NULL COMMENT 'customer_statements.id',
  `cs_entity` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Entity type from customer_statement',
  `cs_entity_id` bigint unsigned DEFAULT NULL COMMENT 'Entity ID from customer_statement',
  `holder_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Account holder name',
  `distributor_code` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Distributor code',
  `acc_ownership` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Account ownership type',
  `cs_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Customer statement status',
  `cs_result` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Customer statement result',
  `cs_score` decimal(10,2) DEFAULT NULL COMMENT 'Customer statement score',
  `cs_limit` decimal(18,2) DEFAULT NULL COMMENT 'Customer statement limit',
  `cs_prev_limit` decimal(18,2) DEFAULT NULL COMMENT 'Previous limit from customer statement',
  `cs_assessment_date` datetime DEFAULT NULL COMMENT 'Customer statement assessment date',
  `final_entity_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Final entity type (lead/reassessment_result)',
  `final_entity_id` bigint unsigned DEFAULT NULL COMMENT 'Final entity ID',
  `cust_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lead_id` bigint unsigned DEFAULT NULL COMMENT 'leads.id',
  `lead_mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead mobile number',
  `lead_biz_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead business name',
  `lead_first_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead first name',
  `lead_last_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead last name',
  `lead_id_proof` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead ID proof number',
  `lead_national_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead national ID',
  `lead_location` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead location',
  `lead_territory` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead territory',
  `lead_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead status',
  `lead_profile_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead profile status',
  `lead_score_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead score status',
  `lead_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Lead type',
  `lead_date` date DEFAULT NULL COMMENT 'Lead date',
  `lead_assessment_date` datetime DEFAULT NULL COMMENT 'Lead assessment date',
  `lead_onboarded_date` datetime DEFAULT NULL COMMENT 'Lead onboarded date',
  `reassessment_id` bigint unsigned DEFAULT NULL COMMENT 'reassessment_results.id',
  `rr_prev_limit` decimal(18,2) DEFAULT NULL COMMENT 'Previous limit from reassessment',
  `rr_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Reassessment status',
  `rr_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Reassessment type',
  `rr_created_at` datetime DEFAULT NULL COMMENT 'Reassessment created timestamp',
  `borrower_id` bigint unsigned DEFAULT NULL COMMENT 'borrowers.id',
  `borrower_cust_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `borrower_biz_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower business name',
  `borrower_reg_date` date DEFAULT NULL COMMENT 'Borrower registration date',
  `tot_loans` int DEFAULT NULL COMMENT 'Total number of loans',
  `tot_default_loans` int DEFAULT NULL COMMENT 'Total number of defaulted loans',
  `crnt_fa_limit` decimal(18,2) DEFAULT NULL COMMENT 'Current FA limit',
  `prev_fa_limit` decimal(18,2) DEFAULT NULL COMMENT 'Previous FA limit',
  `borrower_last_assessment_date` datetime DEFAULT NULL COMMENT 'Borrower last assessment date',
  `borrower_kyc_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower KYC status',
  `borrower_activity_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower activity status',
  `borrower_profile_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower profile status',
  `borrower_fa_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower FA status',
  `borrower_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower status',
  `risk_category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Borrower risk category',
  `reg_rm_id` bigint unsigned DEFAULT NULL COMMENT 'Registered RM ID',
  `reg_rm_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Registered RM name',
  `current_rm_id` bigint unsigned DEFAULT NULL COMMENT 'Current RM ID',
  `current_rm_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Current RM name',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `synced_at` timestamp NULL DEFAULT NULL COMMENT 'Last sync from Flow API',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_run_id` (`run_id`),
  KEY `idx_stmt_request_id` (`stmt_request_id`),
  KEY `idx_cust_id` (`cust_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_acc_prvdr_code` (`acc_prvdr_code`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_final_entity` (`final_entity_type`,`final_entity_id`),
  KEY `idx_borrower_id` (`borrower_id`)
) ENGINE=InnoDB AUTO_INCREMENT=45277 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Customer and borrower details for statement requests - replaces mapper.csv';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `metadata`
--

DROP TABLE IF EXISTS `metadata`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `metadata` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_prvdr_code` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `format` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Format of the statement (e.g., format_1, format_2, excel)',
  `mime` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `submitted_date` date DEFAULT NULL COMMENT 'From mapper.csv using run_id → created_date',
  `start_date` date DEFAULT NULL COMMENT 'min(txn_date) from raw_statements',
  `end_date` date DEFAULT NULL COMMENT 'max(txn_date) from raw_statements',
  `rm_name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `num_rows` int DEFAULT NULL,
  `quality_issues_count` int DEFAULT '0' COMMENT 'Number of transactions with balance data quality issues in this statement',
  `header_row_manipulation_count` int DEFAULT '0',
  `parsing_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'SUCCESS',
  `parsing_error` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `sheet_md5` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `summary_opening_balance` decimal(18,2) DEFAULT NULL,
  `summary_closing_balance` decimal(18,2) DEFAULT NULL,
  `first_balance` decimal(18,2) DEFAULT NULL,
  `last_balance` decimal(18,2) DEFAULT NULL,
  `summary_request_date` date DEFAULT NULL COMMENT 'Request Date from Airtel Format 1',
  `summary_statement_period` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Statement Period from Airtel Format 1',
  `summary_mobile_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Mobile Number from Airtel Format 1',
  `summary_customer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Customer Name from Airtel Format 1',
  `summary_email_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Email Address from Airtel Format 1',
  `meta_title` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_author` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_producer` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_created_at` datetime DEFAULT NULL,
  `meta_modified_at` datetime DEFAULT NULL,
  `pdf_path` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `run_id` (`run_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_provider` (`acc_prvdr_code`),
  KEY `idx_quality_issues_count` (`quality_issues_count`)
) ENGINE=InnoDB AUTO_INCREMENT=20909 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `processed_statements`
--

DROP TABLE IF EXISTS `processed_statements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `processed_statements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `raw_id` bigint NOT NULL,
  `run_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_prvdr_code` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_number` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_date` datetime DEFAULT NULL,
  `txn_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `fee` decimal(18,2) DEFAULT NULL,
  `balance` decimal(18,2) DEFAULT NULL,
  `is_duplicate` tinyint(1) DEFAULT NULL,
  `is_special_txn` tinyint(1) DEFAULT NULL,
  `special_txn_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calculated_running_balance` decimal(18,2) DEFAULT NULL,
  `balance_diff` decimal(18,2) DEFAULT NULL,
  `balance_diff_change_count` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `raw_id` (`raw_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_provider` (`acc_prvdr_code`),
  KEY `idx_provider_acc` (`acc_prvdr_code`,`acc_number`),
  KEY `idx_run_id` (`run_id`),
  CONSTRAINT `processed_statements_ibfk_1` FOREIGN KEY (`raw_id`) REFERENCES `raw_statements` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `raw_statements`
--

DROP TABLE IF EXISTS `raw_statements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `raw_statements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_prvdr_code` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_number` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_date` datetime DEFAULT NULL,
  `txn_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `from_acc` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `to_acc` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_direction` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `fee` decimal(18,2) DEFAULT NULL,
  `balance` decimal(18,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_run_txn` (`run_id`,`txn_id`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_provider` (`acc_prvdr_code`),
  KEY `idx_provider_acc` (`acc_prvdr_code`,`acc_number`),
  KEY `idx_acc_number` (`acc_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `summary`
--

DROP TABLE IF EXISTS `summary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `summary` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_prvdr_code` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rm_name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `num_rows` int DEFAULT NULL,
  `sheet_md5` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `summary_opening_balance` decimal(18,2) DEFAULT NULL,
  `summary_closing_balance` decimal(18,2) DEFAULT NULL,
  `first_balance` decimal(18,2) DEFAULT NULL,
  `last_balance` decimal(18,2) DEFAULT NULL,
  `duplicate_count` int DEFAULT '0',
  `missing_days_detected` tinyint(1) DEFAULT '0',
  `gap_related_balance_changes` int DEFAULT '0',
  `balance_match` enum('Success','Failed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `verification_status` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `verification_reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `credits` decimal(18,2) DEFAULT NULL,
  `debits` decimal(18,2) DEFAULT NULL,
  `fees` decimal(18,2) DEFAULT NULL,
  `charges` decimal(18,2) DEFAULT NULL,
  `calculated_closing_balance` decimal(18,2) DEFAULT NULL,
  `balance_diff_changes` int DEFAULT '0',
  `balance_diff_change_ratio` float DEFAULT '0',
  `meta_title` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_author` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_producer` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_created_at` datetime DEFAULT NULL,
  `meta_modified_at` datetime DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `uses_implicit_cashback` tinyint(1) DEFAULT '1' COMMENT 'Whether statement applies 4% cashback on Merchant Payment Other Single Step',
  `uses_implicit_ind02_commission` tinyint(1) DEFAULT '1' COMMENT 'Whether statement applies 0.5% commission on IND02 transactions',
  `custom_verification` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Metadata-based verification: NO_ISSUES, WARNING, CRITICAL, FATAL',
  `flag_level` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Final flag level: NO_ISSUES, WARNING, CRITICAL, FATAL',
  `flag_reason` text COLLATE utf8mb4_unicode_ci COMMENT 'Explanation for the flag level',
  PRIMARY KEY (`id`),
  UNIQUE KEY `run_id` (`run_id`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_provider` (`acc_prvdr_code`)
) ENGINE=InnoDB AUTO_INCREMENT=47939 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `uatl_processed_statements`
--

DROP TABLE IF EXISTS `uatl_processed_statements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `uatl_processed_statements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `raw_id` bigint NOT NULL,
  `run_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_date` datetime DEFAULT NULL,
  `txn_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `fee` decimal(18,2) DEFAULT '0.00',
  `balance` decimal(18,2) DEFAULT NULL,
  `is_duplicate` tinyint(1) DEFAULT '0',
  `is_special_txn` tinyint(1) DEFAULT '0',
  `special_txn_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calculated_running_balance` decimal(18,2) DEFAULT NULL,
  `balance_diff` decimal(18,2) DEFAULT NULL,
  `balance_diff_change_count` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_txn_date` (`txn_date`),
  KEY `raw_id` (`raw_id`),
  CONSTRAINT `uatl_processed_statements_ibfk_1` FOREIGN KEY (`raw_id`) REFERENCES `uatl_raw_statements` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=97363318 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `uatl_raw_statements`
--

DROP TABLE IF EXISTS `uatl_raw_statements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `uatl_raw_statements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_date` datetime DEFAULT NULL,
  `txn_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `from_acc` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `to_acc` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_direction` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `amount_raw` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original amount value before cleaning',
  `fee` decimal(18,2) DEFAULT '0.00',
  `fee_raw` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original fee value before cleaning',
  `balance` decimal(18,2) DEFAULT NULL,
  `balance_raw` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original balance value before cleaning (e.g., "105608-", "52854II")',
  `has_quality_issue` tinyint(1) DEFAULT '0' COMMENT 'TRUE if balance required regex cleaning due to data quality issues',
  `pdf_format` tinyint DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_txn_date` (`txn_date`),
  KEY `idx_uatl_txn_id` (`txn_id`),
  KEY `idx_has_quality_issue` (`has_quality_issue`)
) ENGINE=InnoDB AUTO_INCREMENT=32799931 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `umtn_processed_statements`
--

DROP TABLE IF EXISTS `umtn_processed_statements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `umtn_processed_statements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `raw_id` bigint NOT NULL,
  `run_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_date` datetime DEFAULT NULL,
  `txn_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `fee` decimal(18,2) DEFAULT '0.00',
  `commission_amount` decimal(18,2) DEFAULT '0.00',
  `tax` decimal(18,2) DEFAULT '0.00',
  `commission_receiving_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `commission_balance` decimal(18,2) DEFAULT NULL,
  `float_balance` decimal(18,2) DEFAULT NULL,
  `is_duplicate` tinyint(1) DEFAULT '0',
  `is_special_txn` tinyint(1) DEFAULT '0',
  `special_txn_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calculated_running_balance` decimal(18,2) DEFAULT NULL,
  `balance_diff` decimal(18,2) DEFAULT NULL,
  `balance_diff_change_count` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_txn_date` (`txn_date`),
  KEY `raw_id` (`raw_id`),
  CONSTRAINT `umtn_processed_statements_ibfk_1` FOREIGN KEY (`raw_id`) REFERENCES `umtn_raw_statements` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=28000882 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `umtn_raw_statements`
--

DROP TABLE IF EXISTS `umtn_raw_statements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `umtn_raw_statements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_date` datetime DEFAULT NULL,
  `txn_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `from_acc` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `to_acc` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `txn_direction` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `fee` decimal(18,2) DEFAULT '0.00',
  `fee_raw` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original fee value before cleaning',
  `commission_amount` decimal(18,2) DEFAULT '0.00',
  `tax` decimal(18,2) DEFAULT '0.00',
  `commission_receiving_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `commission_balance` decimal(18,2) DEFAULT NULL,
  `float_balance` decimal(18,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_run_txn` (`run_id`,`txn_id`),
  KEY `idx_acc_number` (`acc_number`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_txn_date` (`txn_date`)
) ENGINE=InnoDB AUTO_INCREMENT=27995821 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary view structure for view `unified_statements`
--

DROP TABLE IF EXISTS `unified_statements`;
/*!50001 DROP VIEW IF EXISTS `unified_statements`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `unified_statements` AS SELECT 
 1 AS `metadata_id`,
 1 AS `run_id`,
 1 AS `acc_number`,
 1 AS `acc_prvdr_code`,
 1 AS `format`,
 1 AS `mime`,
 1 AS `submitted_date`,
 1 AS `start_date`,
 1 AS `end_date`,
 1 AS `rm_name`,
 1 AS `num_rows`,
 1 AS `parsing_status`,
 1 AS `parsing_error`,
 1 AS `imported_at`,
 1 AS `status`,
 1 AS `processing_status`,
 1 AS `verification_status`,
 1 AS `verification_reason`,
 1 AS `balance_match`,
 1 AS `custom_verification`,
 1 AS `custom_verification_reason`,
 1 AS `summary_opening_balance`,
 1 AS `summary_closing_balance`,
 1 AS `stmt_opening_balance`,
 1 AS `stmt_closing_balance`,
 1 AS `calculated_closing_balance`,
 1 AS `balance_diff_changes`,
 1 AS `balance_diff_change_ratio`,
 1 AS `credits`,
 1 AS `debits`,
 1 AS `fees`,
 1 AS `charges`,
 1 AS `duplicate_count`,
 1 AS `quality_issues_count`,
 1 AS `header_row_manipulation_count`,
 1 AS `missing_days_detected`,
 1 AS `gap_related_balance_changes`,
 1 AS `summary_request_date`,
 1 AS `summary_statement_period`,
 1 AS `summary_mobile_number`,
 1 AS `summary_customer_name`,
 1 AS `summary_email_address`,
 1 AS `processed_at`,
 1 AS `meta_title`,
 1 AS `meta_author`,
 1 AS `meta_producer`,
 1 AS `meta_created_at`,
 1 AS `meta_modified_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Dumping events for database 'fraud_detection'
--

--
-- Dumping routines for database 'fraud_detection'
--

--
-- Current Database: `fraud_detection`
--

USE `fraud_detection`;

--
-- Final view structure for view `unified_statements`
--

/*!50001 DROP VIEW IF EXISTS `unified_statements`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `unified_statements` AS select `m`.`id` AS `metadata_id`,`m`.`run_id` AS `run_id`,`m`.`acc_number` AS `acc_number`,`m`.`acc_prvdr_code` AS `acc_prvdr_code`,`m`.`format` AS `format`,`m`.`mime` AS `mime`,`m`.`submitted_date` AS `submitted_date`,`m`.`start_date` AS `start_date`,`m`.`end_date` AS `end_date`,`m`.`rm_name` AS `rm_name`,`m`.`num_rows` AS `num_rows`,`m`.`parsing_status` AS `parsing_status`,`m`.`parsing_error` AS `parsing_error`,`m`.`created_at` AS `imported_at`,(convert((case when (`m`.`parsing_status` = ('FAILED' collate utf8mb4_unicode_ci)) then 'IMPORT_FAILED' when (`s`.`id` is null) then 'IMPORTED' when ((`s`.`verification_status` = ('FAIL' collate utf8mb4_unicode_ci)) and (`s`.`balance_match` = ('Failed' collate utf8mb4_unicode_ci))) then 'FLAGGED' when (`s`.`verification_status` = ('FAIL' collate utf8mb4_unicode_ci)) then 'VERIFICATION_FAILED' when (`s`.`verification_status` = ('WARNING' collate utf8mb4_unicode_ci)) then 'VERIFIED_WITH_WARNINGS' when ((`s`.`verification_status` = ('PASS' collate utf8mb4_unicode_ci)) and (`s`.`balance_match` = ('Failed' collate utf8mb4_unicode_ci))) then 'VERIFIED_WITH_WARNINGS' when (`s`.`verification_status` = ('PASS' collate utf8mb4_unicode_ci)) then 'VERIFIED' else 'IMPORTED' end) using utf8mb4) collate utf8mb4_unicode_ci) AS `status`,(convert((case when (`s`.`id` is not null) then 'PROCESSED' else 'IMPORTED' end) using utf8mb4) collate utf8mb4_unicode_ci) AS `processing_status`,`s`.`verification_status` AS `verification_status`,`s`.`verification_reason` AS `verification_reason`,`s`.`balance_match` AS `balance_match`,(case when (`s`.`balance_match` = 'Success') then 'NO_ISSUES' else `s`.`custom_verification` end) AS `custom_verification`,(case when (`s`.`balance_match` = 'Success') then 'Balance verification successful' else `s`.`flag_reason` end) AS `custom_verification_reason`,`m`.`summary_opening_balance` AS `summary_opening_balance`,`m`.`summary_closing_balance` AS `summary_closing_balance`,`m`.`first_balance` AS `stmt_opening_balance`,`m`.`last_balance` AS `stmt_closing_balance`,`s`.`calculated_closing_balance` AS `calculated_closing_balance`,`s`.`balance_diff_changes` AS `balance_diff_changes`,`s`.`balance_diff_change_ratio` AS `balance_diff_change_ratio`,`s`.`credits` AS `credits`,`s`.`debits` AS `debits`,`s`.`fees` AS `fees`,`s`.`charges` AS `charges`,`s`.`duplicate_count` AS `duplicate_count`,`m`.`quality_issues_count` AS `quality_issues_count`,`m`.`header_row_manipulation_count` AS `header_row_manipulation_count`,`s`.`missing_days_detected` AS `missing_days_detected`,`s`.`gap_related_balance_changes` AS `gap_related_balance_changes`,`m`.`summary_request_date` AS `summary_request_date`,`m`.`summary_statement_period` AS `summary_statement_period`,`m`.`summary_mobile_number` AS `summary_mobile_number`,`m`.`summary_customer_name` AS `summary_customer_name`,`m`.`summary_email_address` AS `summary_email_address`,`s`.`created_at` AS `processed_at`,`m`.`meta_title` AS `meta_title`,`m`.`meta_author` AS `meta_author`,`m`.`meta_producer` AS `meta_producer`,`m`.`meta_created_at` AS `meta_created_at`,`m`.`meta_modified_at` AS `meta_modified_at` from (`metadata` `m` left join `summary` `s` on((`m`.`run_id` = `s`.`run_id`))) order by `m`.`created_at` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-18 12:19:33
