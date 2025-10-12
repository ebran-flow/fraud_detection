# Database Migrations

SQL migration scripts for database schema updates and fixes.

## Available Migrations

### fix_collation.sql

**Issue:** Illegal mix of collations error in unified_statements view
```
Illegal mix of collations (utf8mb4_0900_ai_ci,COERCIBLE) and (utf8mb4_unicode_ci,COERCIBLE) for operation '='
```

**Cause:** The unified_statements view was comparing string literals with default collation (`utf8mb4_0900_ai_ci`) against table columns using `utf8mb4_unicode_ci` collation.

**Fix:** Added explicit `COLLATE utf8mb4_unicode_ci` clauses to all string comparisons in CASE statements.

**When to apply:**
- After initial database setup
- If you see collation mismatch errors when querying unified_statements
- When filtering by status, verification_status, or balance_match

**How to apply:**

```bash
# Local database
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection < migrations/fix_collation.sql

# Docker database
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < migrations/fix_collation.sql
```

**Verification:**

```bash
# Test the view
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection -e "
  SELECT run_id, status, verification_status
  FROM unified_statements
  WHERE status = 'VERIFIED'
  LIMIT 5;
"

# Should return results without error
```

## Migration History

| Date       | Migration        | Description                          |
|------------|------------------|--------------------------------------|
| 2025-10-12 | fix_collation.sql | Fix collation mismatch in view      |

## Future Migrations

When adding new migrations:

1. Create a new `.sql` file with descriptive name
2. Add documentation to this README
3. Test thoroughly before applying to production
4. Update migration history table above
