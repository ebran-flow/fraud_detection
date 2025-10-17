---
type: Page
title: Customer details query
description: null
icon: null
createdAt: '2025-10-17T03:33:21.814Z'
creationDate: 2025-10-17 09:03
modificationDate: 2025-10-17 09:46
tags: []
coverImage: null
---

```sql
select 
  s.id,
  s.flow_req_id `run_id`,
  s.acc_number,
  s.alt_acc_num,
  s.acc_prvdr_code,
  s.status,
  s.object_key,
  s.lambda_status,
  p.id `rm_id`,
  concat_ws(' ', p.first_name, p.middle_name, p.last_name) `rm_name`,
  date(s.created_at) `created_date`,
  s.created_at,
  s.entity,
  s.entity_id
from 
  partner_acc_stmt_requests s
  left join persons p on p.id = s.created_by 
where s.acc_prvdr_code in ('UMTN','UATL') and (s.created_at <= '2025-10-10 19:07:24' and s.id <= 30668); 
```

The above query is useful for finding all the statements submitted by the customers. This query is used to generate mapper.csv. Till now we've dealt with purely the statements. Now we need the customer details from all these statements. All the statements are linked to an entity using `entity` and `entity_id`

the available entities are 

- customer_statement

- lead

- reassessment_result

link details

- customer_statement => s.entity = 'customer_statement' and s.entity_id = customer_statements.id

- lead => s.entity = 'lead' and s.entity_id = leads.id

- reassessment_result => s.entity = 'reassessment_result' and s.entity_id = reassessment_results

customer_statement has a subentity which should be handled different, we need details of the subentity in contrast to how we did for lead and reassessment result. it has an entity and entity_id field. the available entities are 

- lead

- reassessment_result

link details

- lead => customer_statements.entity = 'lead' and customer_statements.entity_id = leads.id

- reassessment_result => customer_statement.entity = 'reassessment_result' and customer_statements.entity_id = reassessment_results

So the actual entities at the end are either lead or reassessment result

To retrieve the cust_id use the following link

- lead => leads.cust_id

- reassessment_result => reassessment_results.cust_id

I've attached the schema for all the referenced tables.

```sql
-- Partner Account statement requests schema
CREATE TABLE `partner_acc_stmt_requests` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `country_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_prvdr_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `flow_req_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `orig_flow_req_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity_id` int unsigned DEFAULT NULL,
  `acc_number` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `alt_acc_num` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_date` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `end_date` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_message` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `object_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lambda_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `presigned_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `req_time` datetime DEFAULT NULL,
  `resp_time` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `created_by` int unsigned DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` int unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `partner_acc_stmt_requests_flow_req_id_index` (`flow_req_id`)
) ENGINE=InnoDB AUTO_INCREMENT=31352 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

-- Customer Statements Schema
CREATE TABLE `customer_statements` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `country_code` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_prvdr_code` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acc_number` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alt_acc_num` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_primary_acc` tinyint(1) NOT NULL DEFAULT '0',
  `entity` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_id` int unsigned DEFAULT NULL,
  `holder_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `distributor_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_ownership` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_json` json NOT NULL DEFAULT (json_object()),
  `acc_purpose` json NOT NULL DEFAULT (json_array()),
  `cust_score_factors` json NOT NULL DEFAULT (json_array()),
  `conditions` json NOT NULL DEFAULT (json_array()),
  `limit` int DEFAULT NULL,
  `prev_limit` int DEFAULT NULL,
  `score` varchar(5) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `result` varchar(15) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `result_json` json NOT NULL DEFAULT (json_object()),
  `run_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_message` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assessment_source_date` date DEFAULT NULL,
  `source` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assessment_date` datetime DEFAULT NULL,
  `batch_reassessment_id` bigint DEFAULT NULL,
  `removal_screen` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_removed` tinyint(1) NOT NULL DEFAULT '0',
  `templt` json NOT NULL DEFAULT (json_object()),
  `original_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `created_by` int unsigned NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` int unsigned DEFAULT NULL,
  `active_entity` varchar(100) COLLATE utf8mb4_unicode_ci GENERATED ALWAYS AS ((case when ((`is_removed` = 0) and (`entity` is null) and (`entity_id` is null)) then concat_ws(_utf8mb4'|',`acc_number`,`acc_prvdr_code`) when (`is_removed` = 0) then concat_ws(_utf8mb4'|',`entity`,`entity_id`,`acc_number`,`acc_prvdr_code`) else NULL end)) STORED,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_active_entity` (`active_entity`),
  KEY `customer_statements_entity_entity_id_index` (`entity`,`entity_id`),
  KEY `customer_statements_run_id_index` (`run_id`),
  KEY `customer_statements_acc_number_index` (`acc_number`)
) ENGINE=InnoDB AUTO_INCREMENT=153625 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

-- Leads schema
CREATE TABLE `leads` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `country_code` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_cust_reg_json` json DEFAULT NULL,
  `cust_reg_json` json DEFAULT NULL,
  `cust_reg_json_bak` json DEFAULT NULL,
  `audit_data` json NOT NULL DEFAULT (json_array()),
  `file_json` json DEFAULT NULL,
  `consent_json` json DEFAULT NULL,
  `self_reg_json` json DEFAULT (json_object()),
  `self_reg_start_time` datetime DEFAULT NULL,
  `self_reg_end_time` datetime DEFAULT NULL,
  `lead_json` json DEFAULT NULL,
  `distributor_code` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `update_data_json` json DEFAULT NULL,
  `cust_eval_json` json DEFAULT NULL,
  `reassign_reason` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remarks` json NOT NULL DEFAULT (json_array()),
  `rekyc_remarks` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `self_reg_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `profile_status` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'open',
  `under_watch` tinyint(1) DEFAULT NULL,
  `under_watch_reason` json DEFAULT NULL,
  `score_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `close_reason` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `kyc_reason` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `review_reason` json DEFAULT NULL,
  `lead_source` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assessment_source` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assessment_count` int unsigned NOT NULL DEFAULT '0',
  `referral_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `flag_id` bigint DEFAULT NULL,
  `visit_ids` json NOT NULL DEFAULT (_utf8mb4'[]'),
  `redirect_lead` bigint unsigned DEFAULT NULL,
  `tf_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rectification_pending` tinyint(1) NOT NULL DEFAULT '0',
  `lead_date` datetime DEFAULT NULL,
  `interested_date` datetime DEFAULT NULL,
  `assessment_date` datetime DEFAULT NULL,
  `eval_date` datetime DEFAULT NULL,
  `consent_signed_date` datetime DEFAULT NULL,
  `rm_kyc_start_date` datetime DEFAULT NULL,
  `rm_kyc_end_date` datetime DEFAULT NULL,
  `rm_kyc_submitted_at` datetime DEFAULT NULL,
  `mobile_num_ver_start_date` datetime DEFAULT NULL,
  `mobile_num_ver_end_date` datetime DEFAULT NULL,
  `actual_audit_start_date` datetime DEFAULT NULL,
  `audit_kyc_start_date` datetime DEFAULT NULL,
  `audit_kyc_end_date` datetime DEFAULT NULL,
  `onboarded_date` datetime DEFAULT NULL,
  `referral_date` datetime DEFAULT NULL,
  `self_reg_date` datetime DEFAULT NULL,
  `lead_closed_date` datetime DEFAULT NULL,
  `pitched_on` datetime DEFAULT NULL,
  `rm_eval_id` int unsigned DEFAULT NULL,
  `audited_by` int unsigned DEFAULT NULL,
  `self_reg_audited_by` int DEFAULT NULL,
  `referred_by` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pitched_by` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_initiated_by` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mobile_num` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `biz_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_proof_num` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `national_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_prvdr_code` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_num` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alt_acc_num` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `territory` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_purpose` json NOT NULL DEFAULT (_utf8mb4'[]'),
  `visit_remarks` json NOT NULL DEFAULT (json_array()),
  `channel` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `product` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `flow_rel_mgr_id` int unsigned DEFAULT NULL,
  `sales_rep_id` int unsigned DEFAULT NULL,
  `next_visit_date` datetime DEFAULT NULL,
  `is_removed` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` int unsigned DEFAULT NULL,
  `updated_by` int unsigned DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `flagging_reason` json NOT NULL DEFAULT (_utf8mb4'[]'),
  `photo_cust_eval_checklist` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_migrated` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_account_num` (`account_num`),
  KEY `leads_alt_acc_num_index` (`alt_acc_num`),
  KEY `leads_mobile_num_index` (`mobile_num`),
  KEY `idx_leads_status_profile_country` (`status`,`profile_status`,`country_code`),
  KEY `cust_id` (`cust_id`),
  KEY `leads_id_proof_num_index` (`id_proof_num`),
  KEY `leads_referral_code_index` (`referral_code`),
  KEY `idx_created_at` (`created_at`),
  KEY `leads_national_id_index` (`national_id`)
) ENGINE=InnoDB AUTO_INCREMENT=158303 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

-- Reassessment results
CREATE TABLE `reassessment_results` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `country_code` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_prvdr_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_number` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alt_acc_num` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prev_limit` int DEFAULT NULL,
  `run_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_message` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_json` json DEFAULT NULL,
  `result_json` json DEFAULT (json_object()),
  `type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` int unsigned DEFAULT NULL,
  `updated_by` int unsigned DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cust_id` (`cust_id`)
) ENGINE=InnoDB AUTO_INCREMENT=28471 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

