# Migration Guide for Time-Based Sessions

## Overview

The LeetCode SRS has been updated to support time-based sessions with user-configurable durations. This requires database schema changes that are handled automatically.

## Automatic Migration

The app now includes automatic migration on startup. When you start the application:

1. **Backup is created** automatically before any operations
2. **Migration runs** if needed to add time tracking columns
3. **Existing data** is preserved and calculated for existing sessions

### What Gets Added

Two new columns to the `sessions` table:
- `total_time_seconds INTEGER DEFAULT 0` - Tracks cumulative session time
- `max_duration_minutes INTEGER DEFAULT 45` - User-configured session duration

## Manual Migration (If Needed)

If automatic migration fails, you can run the migration manually:

```bash
# Run the standalone migration script
python3 migrate_add_session_time_columns.py
```

## Migration Status

Check if your database has been migrated:

```bash
python3 -c "
from app import create_app
import sqlite3

app = create_app()
with app.app_context():
    from models import db

    conn = sqlite3.connect(db.engine.url.database)
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(sessions)')
    columns = [row[1] for row in cursor.fetchall()]

    has_migration = 'total_time_seconds' in columns and 'max_duration_minutes' in columns
    print(f'Migration status: {'✅ COMPLETE' if has_migration else '❌ NEEDED'}')
    print(f'Columns: {columns}')
    conn.close()
"
```

## Troubleshooting

### Error: "no such column: sessions.total_time_seconds"

This indicates your database hasn't been migrated. Solutions:

1. **Restart the app** - migration runs automatically on startup
2. **Run manual migration** - Use the script above
3. **Check permissions** - Ensure the app can write to the database file

### Error: Migration fails during startup

1. Check database file permissions
2. Ensure database isn't locked by another process
3. Look for error messages in console output

### Backup Recovery

If something goes wrong, backups are created automatically in `data/backups/`:

```bash
# List available backups
ls -la data/backups/

# Restore from backup (stop app first)
cp data/backups/leetcode_backup_YYYY-MM-DD_HH-MM-SS.db data/leetcode.db
```

## Deployment Notes

### Production Deployment

1. **Stop the application**
2. **Backup current database** (automatic backup will also be created)
3. **Deploy new code**
4. **Start application** - migration runs automatically
5. **Verify migration** using status check above

### Zero-Downtime Deployment

The migration is designed to be backward-compatible:
- New columns have default values
- Old sessions continue to work
- Time tracking starts working immediately for new sessions

## Data Migration Details

### Existing Sessions

For sessions that were completed before the migration:
- `total_time_seconds` is calculated from `started_at` to `completed_at`
- `max_duration_minutes` defaults to 45 minutes
- All review data and statistics are preserved

### New Sessions

After migration:
- Users select session duration during configuration
- Time tracking is accurate with pause/resume support
- Progress bars show time-based completion

## Verification

After migration, verify everything works:

1. **Start a new session** - Should show configuration page
2. **Check countdown timer** - Should display remaining time
3. **Test pause/resume** - Time tracking should be accurate
4. **Complete a session** - Should auto-complete when time expires

## Rollback (Emergency Only)

If you need to rollback to the previous version:

1. **Stop the new application**
2. **Restore database backup** from before migration
3. **Deploy previous version** of the code
4. **Start application**

Note: Any sessions created with the new time-based system will be lost.

---

*Migration implemented: September 29, 2025*
*Compatible with: All previous database schemas*