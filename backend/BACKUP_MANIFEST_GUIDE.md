# Backup Manifest System

## Overview

Every XtraBackup (full and incremental) now automatically generates a **detailed manifest** describing exactly what's included in the backup. This allows you to quickly understand what each backup contains without needing to restore it.

---

## What's Included in Each Manifest

Each backup generates a `BACKUP_MANIFEST.txt` file containing:

### 1. Backup Information
- Backup type (full or incremental)
- Timestamp
- Backup directory and size
- MySQL connection details

### 2. Git Information
- Current commit hash
- Branch name
- Number of modified files

### 3. Database Statistics
- Total number of statements
- Row counts for all tables:
  - metadata
  - summary
  - uatl_raw_statements
  - uatl_processed_statements
  - umtn_raw_statements
  - umtn_processed_statements

### 4. Schema Objects
- Number of tables
- Number of views
- Key schema columns status (EXISTS/MISSING):
  - `metadata.header_rows_count`
  - `summary.missing_days_detected`
  - `uatl_raw_statements.amount_raw`
  - `uatl_raw_statements.fee_raw`
  - `unified_statements` view

### 5. Data Quality Metrics
- Statements with quality issues
- Statements with header manipulation
- Statements with missing days
- Balance match statistics (success/failed)

### 6. Data Timeline
- Earliest statement date
- Latest statement date
- Most recent import timestamp

### 7. Backup Description
- Your custom description of what changed
- Prompted during backup creation

---

## Creating Backups with Descriptions

### Full Backup

```bash
./scripts/backup/xtrabackup_full.sh
```

**Interactive prompt:**
```
Please describe what's included in this backup (or press Enter to skip):
Examples:
  - After importing remaining Airtel/MTN statements
  - Added unified_statements view
  - Applied schema updates: header_rows_count, amount_raw, fee_raw
  - Post-restore baseline with all tables

Description: █
```

**Example descriptions:**
- "Post-restore baseline from Oct 14 backups"
- "After importing 5,000 new UATL statements"
- "Added unified_statements view for API"
- "Applied all schema updates: header_rows_count, fee_raw, amount_raw"
- "Before major migration to new format"

### Incremental Backup

```bash
./scripts/backup/xtrabackup_incremental.sh
```

**Interactive prompt:**
```
Please describe what changes are in this incremental backup (or press Enter to skip):
Examples:
  - Daily backup after processing new statements
  - After populating header_rows_count
  - Applied schema update for fee_raw column
  - Before major data migration

Description: █
```

**Example descriptions:**
- "Daily backup - no major changes"
- "Populated header_rows_count for 2,500 Airtel statements"
- "After processing 1,000 new MTN statements"
- "Applied gap detection updates to summary table"

---

## Viewing Backup Inventory

### List All Backups

```bash
./scripts/backup/list_backups.sh
```

**Output example:**
```
================================================================================
XTRABACKUP INVENTORY
================================================================================

FULL BACKUPS:
-------------

[1] full_20251016_001500
  📅 Date: 2025-10-16 00:15:00 IST
  💾 Size: 8.2G
  📊 Statements: 32,234,567
  🔗 Git: 958b959a
  📝 Description:
     Post-restore baseline from Oct 14 backups with all tables restored

[2] full_20251015_183000
  📅 Date: 2025-10-15 18:30:00 IST
  💾 Size: 7.8G
  📊 Statements: 31,150,000
  🔗 Git: fccebb3c
  📝 Description:
     After importing remaining Airtel/MTN statements

================================================================================

INCREMENTAL BACKUPS:
--------------------

[1] inc_20251016_120000
  📅 Date: 2025-10-16 12:00:00 IST
  💾 Size: 145M
  📊 Statements: 32,234,567
  🔗 Git: 958b959a
  📝 Description:
     Daily backup after processing new statements

================================================================================

BACKUP CHAIN:
-------------
Current base for next incremental: inc_20251016_120000

SUMMARY:
--------
Full backups total size:         16G
Incremental backups total size:  580M

================================================================================
```

---

## Viewing Individual Manifests

### View Specific Backup Manifest

```bash
cat /path/to/backups/xtrabackup/full/full_20251016_001500/BACKUP_MANIFEST.txt
```

**Or:**
```bash
less backups/xtrabackup/full/full_20251016_001500/BACKUP_MANIFEST.txt
```

### Example Manifest Output

```
================================================================================
XTRABACKUP BACKUP MANIFEST
================================================================================

Backup Information:
-------------------
Backup Type:        full
Backup Date:        2025-10-16 00:15:32 IST
Backup Directory:   /home/ebran/.../backups/xtrabackup/full/full_20251016_001500
Backup Size:        8.2G

MySQL Connection:
-----------------
Host:               127.0.0.1
Port:               3306
Database:           fraud_detection

Git Information:
----------------
Git Commit:         958b959a
Git Branch:         main
Git Status:         0 file(s) modified

Database Statistics:
--------------------
Total Statements:   32,234,567
Total Metadata:     20,794 records
Total Summary:      21,192 records
UATL Raw:           32,696,864 rows
UATL Processed:     35,242,642 rows
UMTN Raw:           27,992,324 rows
UMTN Processed:     27,997,381 rows

Schema Objects:
---------------
Tables:             8
Views:              1

Recent Schema Changes:
----------------------
✓ metadata.header_rows_count: EXISTS
✓ summary.missing_days_detected: EXISTS
✓ uatl_raw_statements.amount_raw: EXISTS
✓ uatl_raw_statements.fee_raw: EXISTS
✓ unified_statements view: EXISTS

Data Quality Metrics:
---------------------
Statements with Quality Issues:     1,234
Statements with Header Manipulation: 567
Statements with Missing Days:        89
Balance Match Success:               19,450
Balance Match Failed:                1,742

Data Timeline:
--------------
Earliest Statement:  2020-01-05
Latest Statement:    2025-10-14
Most Recent Import:  2025-10-15 17:53

================================================================================
BACKUP DESCRIPTION:
================================================================================

Post-restore baseline from Oct 14 backups with all 8 tables restored.
Includes unified_statements view and all schema updates applied.

================================================================================
End of Manifest
================================================================================
```

---

## Use Cases

### 1. Finding When a Change Was Made

**Scenario:** "When did we add the unified_statements view?"

```bash
./scripts/backup/list_backups.sh | grep -A 5 "unified"
```

Or check manifests:
```bash
grep -l "unified_statements view: EXISTS" backups/xtrabackup/full/*/BACKUP_MANIFEST.txt
```

### 2. Comparing Database States

**Scenario:** "How many statements did we have before/after import?"

```bash
# Check first backup
grep "Total Statements:" backups/xtrabackup/full/full_20251015_183000/BACKUP_MANIFEST.txt

# Check second backup
grep "Total Statements:" backups/xtrabackup/full/full_20251016_001500/BACKUP_MANIFEST.txt
```

### 3. Finding Right Backup for Restore

**Scenario:** "I need to restore to before we applied the schema update"

```bash
# List all backups with their descriptions
./scripts/backup/list_backups.sh

# Check specific manifest for schema status
less backups/xtrabackup/full/full_20251015_183000/BACKUP_MANIFEST.txt
```

### 4. Audit Trail

**Scenario:** "What changed between Oct 15 and Oct 16?"

Compare manifests side by side or use diff:
```bash
diff \
  backups/xtrabackup/full/full_20251015_183000/BACKUP_MANIFEST.txt \
  backups/xtrabackup/full/full_20251016_001500/BACKUP_MANIFEST.txt
```

---

## Best Practices

### Description Writing

**Good Descriptions:**
✅ "Post-restore baseline with all tables from Oct 14 backups"
✅ "After importing 5,234 new UATL statements (batch_2024_Q4)"
✅ "Applied schema update: added header_rows_count column"
✅ "Before deploying unified_statements view to production"
✅ "Daily backup - processed 234 statements, no schema changes"

**Poor Descriptions:**
❌ "backup"
❌ "test"
❌ "" (empty)
❌ "stuff"

### When to Skip Description

It's okay to skip descriptions for:
- Automated daily incremental backups with no significant changes
- Quick test backups that won't be kept
- Backups taken immediately after another documented backup

### Regular Reviews

Review your backup inventory monthly:
```bash
./scripts/backup/list_backups.sh > backup_inventory_$(date +%Y%m).txt
```

---

## Troubleshooting

### Manifest Not Generated

**Issue:** Backup completed but no BACKUP_MANIFEST.txt

**Check:**
```bash
# Verify manifest generator is executable
ls -la scripts/backup/generate_backup_manifest.sh

# Make it executable if needed
chmod +x scripts/backup/generate_backup_manifest.sh
```

### Manifest Shows "Calculating..." for Size

**Cause:** Backup directory size calculation in progress

**Solution:** Wait a few seconds and regenerate:
```bash
./scripts/backup/generate_backup_manifest.sh \
  /path/to/backup/dir \
  full
```

### Missing Description Section

**Cause:** No description was provided during backup

**Solution:** You can manually add a description:
```bash
echo "Your description here" > /path/to/backup/BACKUP_NOTES.txt

# Regenerate manifest
./scripts/backup/generate_backup_manifest.sh /path/to/backup full
```

---

## Files in Each Backup Directory

After a successful backup, you'll find:

```
full_20251016_001500/
├── BACKUP_MANIFEST.txt          # Detailed manifest (auto-generated)
├── BACKUP_NOTES.txt              # Your description (if provided)
├── xtrabackup_checkpoints        # XtraBackup metadata
├── xtrabackup_info               # Backup info
├── xtrabackup_logfile            # Transaction log
├── fraud_detection/              # Database files (compressed)
│   ├── metadata.ibd.qp
│   ├── summary.ibd.qp
│   ├── uatl_raw_statements.ibd.qp
│   └── ...
└── ...
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./scripts/backup/xtrabackup_full.sh` | Create full backup with manifest |
| `./scripts/backup/xtrabackup_incremental.sh` | Create incremental backup with manifest |
| `./scripts/backup/list_backups.sh` | View all backups with descriptions |
| `cat backup_dir/BACKUP_MANIFEST.txt` | View detailed manifest |
| `grep "Description:" backup_dir/BACKUP_MANIFEST.txt` | Extract just the description |
| `./scripts/backup/generate_backup_manifest.sh dir type` | Regenerate manifest |

---

## Examples of Good Backup Descriptions

### After Major Changes
```
"Added unified_statements view for new API endpoints.
Updated 20,794 metadata records with header_rows_count.
Baseline before production deployment."
```

### After Import
```
"Imported remaining 8,542 Airtel statements from Q4 2024.
Total statements now: 32,234,567.
All balance verifications passed."
```

### Before Risky Operation
```
"Backup before applying schema migration for fee_raw columns.
All data verified. Git commit: 958b959a"
```

### Daily Routine
```
"Daily incremental backup.
Processed 234 new statements.
No schema changes."
```

---

Last Updated: 2025-10-16
