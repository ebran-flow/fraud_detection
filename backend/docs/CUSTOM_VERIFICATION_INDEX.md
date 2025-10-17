# Custom Verification System - Document Index

This index provides quick navigation to all documentation related to the custom verification system.

---

## Executive Documents (For Management)

### 1. Executive Summary
**File:** `EXECUTIVE_SUMMARY_CUSTOM_VERIFICATION.md`
**Purpose:** High-level overview for management decision-making
**Contents:**
- Key findings and statistics
- Top 3 fraud patterns identified
- High-risk RM analysis
- Business impact (1.43B UGX at risk)
- Immediate action items
- ROI and risk mitigation

**When to Use:** Management reviews, stakeholder presentations, quarterly reports

---

## Technical Documentation (For Development Team)

### 2. Comprehensive Summary Report
**File:** `CUSTOM_VERIFICATION_SUMMARY.md`
**Purpose:** Complete technical documentation of the system
**Contents:**
- Detailed methodology (9 metadata combinations)
- Classification logic for Format 1 and Format 2
- Statistical analysis by format, producer, manipulation
- Sample FATAL cases with analysis
- Implementation details
- SQL query examples
- Recommendations for Phase 2 & 3

**When to Use:** System understanding, training, troubleshooting, enhancement planning

---

### 3. Quick Start Guide
**File:** `CUSTOM_VERIFICATION_QUICK_START.md`
**Purpose:** Practical guide for daily operations
**Contents:**
- Common SQL queries (ready to copy-paste)
- Fraud pattern identification guide
- Quick decision guide for RMs and reviewers
- Troubleshooting steps
- Integration with customer_details table
- Key metrics dashboard

**When to Use:** Daily operations, query reference, training new team members

---

### 4. View Update Instructions
**File:** `UPDATE_UNIFIED_VIEW_INSTRUCTIONS.md`
**Purpose:** Technical guide for applying view migrations
**Contents:**
- Step-by-step migration instructions
- xtrabackup credentials usage
- Verification queries
- Troubleshooting permission issues

**When to Use:** Database maintenance, view updates, permission issues

---

## Requirements & Design (For Reference)

### 5. Requirements Document
**File:** `prompts/Suspicious statements flagging logic.md`
**Purpose:** Original requirements and classification logic
**Contents:**
- 4-level flagging system definition
- Format 1 combinations (6 combinations)
- Format 2 combinations (3 combinations)
- Metric definitions and usage
- Balance match override rule
- Historical decision context

**When to Use:** Understanding requirements, validating implementation, enhancement proposals

---

## Data Exports (For Analysis)

### 6. Flagged Statements Export
**File:** `data/flagged_statements_fatal_critical.csv`
**Size:** 288 records
**Purpose:** Complete dataset of FATAL and CRITICAL cases
**Columns:**
- run_id, acc_number, format
- custom_verification, custom_verification_reason
- balance_match, balance_diff_change_ratio
- All quality metrics and metadata
- Customer details (name, mobile)
- RM information
- Financial totals

**When to Use:** Customer contact workflow, detailed investigation, reporting

---

### 7. Verified Statements Export
**File:** `data/verified_statements_no_issues.csv`
**Size:** 2,164 records
**Purpose:** Reference dataset of verified safe statements
**Columns:**
- run_id, acc_number, format
- custom_verification, custom_verification_reason
- balance_match, balance_diff_change_ratio
- meta_producer, meta_author
- submitted_date, rm_name

**When to Use:** Comparison analysis, training data, pattern validation

---

## Database Migrations (For Database Admin)

### 8. Add Custom Verification Column
**File:** `../migrations/add_custom_verification_column.sql`
**Purpose:** Add custom_verification columns to summary table
**Changes:**
- summary.custom_verification (VARCHAR 50)
- summary.flag_level (VARCHAR 50) - deprecated
- summary.flag_reason (TEXT)

**When to Use:** Initial setup, new database instances

---

### 9. Update Unified View - Basic
**File:** `../migrations/add_custom_verification_to_unified_view.sql`
**Purpose:** Add custom_verification to unified_statements view
**Features:**
- custom_verification column with balance_match override
- custom_verification_reason column
- Maintains backward compatibility

**When to Use:** View updates, after classification runs

---

### 10. Update Unified View - With Customer Details
**File:** `../migrations/update_unified_view_with_customer_details.sql`
**Purpose:** Comprehensive view with customer_details join (FUTURE)
**Features:**
- All verification columns
- Complete customer details integration
- Borrower information
- RM tracking
- 69 additional columns

**When to Use:** After customer_details table is fully populated and tested

---

## Scripts (For Automation)

### 11. Apply Custom Verification Script
**File:** `../scripts/analysis/apply_custom_verification.py`
**Purpose:** Classify statements based on metadata combinations
**Features:**
- Processes 12,405+ statements in ~2 minutes
- Implements 9 metadata combinations
- Supports --dry-run for preview
- Statistics output
- Progress tracking with tqdm

**Usage:**
```bash
# Apply classification
python scripts/analysis/apply_custom_verification.py

# Preview only (no database changes)
python scripts/analysis/apply_custom_verification.py --dry-run
```

**When to Use:** After new statement imports, when requirements change, periodic updates

---

## Quick Reference Tables

### Document Purpose Matrix

| Document | Management | Developers | Analysts | RMs | Quick Ref |
|----------|-----------|-----------|----------|-----|-----------|
| Executive Summary | ✓✓✓ | ✓ | ✓✓ | ✓ | |
| Comprehensive Summary | ✓ | ✓✓✓ | ✓✓ | | |
| Quick Start Guide | | ✓✓ | ✓✓ | ✓✓✓ | ✓✓✓ |
| View Update Instructions | | ✓✓✓ | | | |
| Requirements Doc | ✓ | ✓✓✓ | ✓✓ | | |
| Flagged Statements CSV | ✓✓ | ✓ | ✓✓✓ | ✓✓ | |
| Verified Statements CSV | | ✓ | ✓✓✓ | ✓ | |

**Legend:** ✓✓✓ Primary audience, ✓✓ Secondary audience, ✓ Reference only

---

### File Size Reference

| File | Size | Record Count | Format |
|------|------|--------------|--------|
| EXECUTIVE_SUMMARY_CUSTOM_VERIFICATION.md | ~15 KB | - | Markdown |
| CUSTOM_VERIFICATION_SUMMARY.md | ~25 KB | - | Markdown |
| CUSTOM_VERIFICATION_QUICK_START.md | ~20 KB | - | Markdown |
| flagged_statements_fatal_critical.csv | ~150 KB | 288 | CSV |
| verified_statements_no_issues.csv | ~250 KB | 2,164 | CSV |
| apply_custom_verification.py | ~9 KB | - | Python |

---

## Navigation by Task

### "I need to understand the system"
Start with: **CUSTOM_VERIFICATION_SUMMARY.md**
Then read: **Requirements Document**
Reference: **Quick Start Guide**

### "I need to present findings to management"
Use: **EXECUTIVE_SUMMARY_CUSTOM_VERIFICATION.md**
Support with: **Flagged Statements CSV**

### "I need to run daily queries"
Use: **CUSTOM_VERIFICATION_QUICK_START.md**
Section: "Common Queries"

### "I need to investigate a FATAL case"
1. Query: `SELECT * FROM unified_statements WHERE run_id = 'XXX'`
2. Check: **Flagged Statements CSV** for complete details
3. Reference: **Quick Start Guide** → "Understanding Fraud Patterns"

### "I need to update the classification"
1. Read: **VIEW_UPDATE_INSTRUCTIONS.md**
2. Run: `python scripts/analysis/apply_custom_verification.py`
3. Verify: Check unified_statements view

### "I need to train new team members"
Start with: **Quick Start Guide**
Then: **Comprehensive Summary** (methodology section)
Practice: Sample queries from Quick Start Guide

---

## Document History

| Date | Document | Change |
|------|----------|--------|
| 2025-10-17 | All documents | Initial creation |
| 2025-10-17 | apply_custom_verification.py | Added combination_6 |
| 2025-10-17 | Requirements doc | Added balance_match override rule |
| 2025-10-17 | Unified view | Applied custom_verification integration |

---

## Support Contacts

**System Issues:** Backend Development Team
**Classification Questions:** Fraud Detection Team
**Database Migrations:** Database Admin Team
**Process Questions:** Risk Management Team

---

## Related Systems

This custom verification system integrates with:
- **metadata table** - PDF metadata extraction
- **summary table** - Balance verification results
- **customer_details table** - Borrower and customer information
- **unified_statements view** - Consolidated reporting view

For customer_details integration, see: `update_unified_view_with_customer_details.sql` (pending deployment)

---

**Last Updated:** October 17, 2025
**System Version:** 1.0
**Status:** Production Ready
