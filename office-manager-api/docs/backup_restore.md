# PostgreSQL Backup & Restore

This document outlines the backup and restore procedures for the Office Manager PostgreSQL database.

## Automated Backups (using pg_dump via cron)

### Daily Backups

```bash
# Add to crontab (crontab -e)
# Run at 2:00 AM daily
0 2 * * * pg_dump -U postgres office_manager | gzip > /backups/office_manager_$(date +\%Y\%m\%d).sql.gz
```

### Weekly Full Backups

```bash
# Add to crontab
# Run Sunday at 3:00 AM
0 3 * * 0 pg_dump -U postgres office_manager | gzip > /backups/office_manager_weekly_$(date +\%Y\%m\%d).sql.gz
```

### Retention Policy

```bash
# Keep daily backups for 7 days
# Keep weekly backups for 4 weeks
# Keep monthly backups for 12 months

# Add cleanup to crontab (run daily at 4 AM)
0 4 * * * find /backups -name "office_manager_*.sql.gz" -mtime +7 -delete
0 4 * * 0 find /backups -name "office_manager_weekly_*.sql.gz" -mtime +28 -delete
0 4 1 * * find /backups -name "office_manager_monthly_*.sql.gz" -mtime +365 -delete
```

## Point-in-Time Recovery (using pgBackRest)

For enterprise deployments, pgBackRest provides continuous archiving and point-in-time recovery.

### Configuration (pgbackrest.conf)

```ini
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=2
repo1-retention-diff=4
repo1-retention-archive=30
process-max=4
log-level-console=info
log-level-file=debug

[main]
pg1-path=/var/lib/postgresql/data
archive-command=/usr/bin/pgbackrest --stanza=main archive-push %p
restore-command=/usr/bin/pgbackrest --stanza=main archive-get %p %f
```

### Setup Commands

```bash
# Initialize pgBackRest
pgbackrest --stanza=main --delta init

# Start archive mode
echo "wal_level = replica" >> postgresql.conf
echo "archive_mode = on" >> postgresql.conf
echo "archive_command = 'pgbackrest --stanza=main archive-push %p'" >> postgresql.conf

# Restart PostgreSQL
systemctl restart postgresql

# Create first backup
pgbackrest --stanza=main backup --type=full
```

### Point-in-Time Recovery

```bash
# Stop PostgreSQL
systemctl stop postgresql

# Remove existing data (BE CAREFUL!)
rm -rf /var/lib/postgresql/data/*

# Restore to specific timestamp
pgbackrest --stanza=main restore --type=time "--target=2024-01-29 10:00:00"

# Start PostgreSQL
systemctl start postgresql
```

## Emergency Restore

### From Latest Backup

```bash
# Download/download latest backup
gunzip -k office_manager_20240129.sql.gz

# Restore to new database for verification
psql -U postgres -c "CREATE DATABASE office_manager_restore;"
psql -U postgres office_manager_restore < office_manager_20240129.sql

# Verify data
psql -U postgres office_manager_restore -c "SELECT COUNT(*) FROM users;"

# If verification passes, switch databases
psql -U postgres -c "DROP DATABASE office_manager;"
psql -U postgres -c "ALTER DATABASE office_manager_restore RENAME TO office_manager;"
```

### Partial Restore (specific tables)

```bash
# Extract specific table from backup
gunzip -c office_manager_20240129.sql.gz | \
    psql -U postgres office_manager -c "\copy table_name FROM stdin;"
```

## Staging Migration Process

For safe production migrations:

1. **Run migrations on staging first**
   ```bash
   # Staging environment
   export APP_ENV=staging
   alembic upgrade head
   ```

2. **Verify functionality**
   - Run integration tests
   - Manual QA testing
   - Check performance metrics

3. **Schedule maintenance window**
   - Announce downtime (if required)
   - Prepare rollback plan

4. **Run migrations on production during low-traffic period**
   ```bash
   # Take backup first
   pg_dump -U postgres office_manager | gzip > pre_migration_backup.sql.gz
   
   # Run migrations
   export APP_ENV=production
   alembic upgrade head
   ```

5. **Have rollback migration ready**
   ```bash
   # If issues occur, rollback
   alembic downgrade -1
   ```

## Backup Verification

Regularly test backup restoration:

```bash
# Weekly verification script
#!/bin/bash
BACKUP_FILE=/backups/office_manager_$(date +%Y%m%d).sql.gz
TEST_DB=backup_test_$(date +%s)

# Create test database
createdb $TEST_DB

# Restore to test database
gunzip -c $BACKUP_FILE | psql $TEST_DB

# Verify key tables exist
if psql $TEST_DB -t -c "SELECT COUNT(*) FROM users;" | grep -q "[0-9]"; then
    echo "Backup verification PASSED"
else
    echo "Backup verification FAILED"
    exit 1
fi

# Cleanup
dropdb $TEST_DB
```

## Monitoring

Add backup monitoring to your alerting system:

```bash
# Check backup age
if [ $(find /backups -name "office_manager_*.sql.gz" -mtime +1 | wc -l) -gt 0 ]; then
    echo "WARNING: No recent backup found"
fi

# Check backup size (alert if suspiciously small)
SIZE=$(stat -f%z /backups/office_manager_$(date +%Y%m%d).sql.gz 2>/dev/null || stat -c%s /backups/office_manager_$(date +%Y%m%d).sql.gz 2>/dev/null)
if [ $SIZE -lt 1000 ]; then
    echo "WARNING: Backup file too small"
fi
```
