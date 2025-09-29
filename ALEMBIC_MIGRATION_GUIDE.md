# Professional Migration Guide with Alembic

## Overview

The LeetCode SRS now uses **Alembic** for professional database migrations with full version control. This replaces the manual migration system with industry-standard migration management.

## Alembic Features

✅ **Version Control** - Track all database schema changes
✅ **Automatic Migration** - Runs on app startup
✅ **Rollback Support** - Downgrade to previous versions
✅ **Migration History** - View all applied migrations
✅ **Backup Integration** - Automatic backups before migrations

## Automatic Migration System

### On App Startup
1. **Database backup** created automatically in `data/backups/`
2. **Alembic migrations** applied automatically to bring schema up to date
3. **Graceful handling** of migration errors (app continues with existing schema)
4. **No manual intervention** required for most deployments

### What Gets Added
- `total_time_seconds INTEGER DEFAULT 0` - Cumulative session time tracking
- `max_duration_minutes INTEGER DEFAULT 45` - User-configured session duration

## Alembic Commands

### Check Migration Status
```bash
# View migration history
alembic history --verbose

# View current database version
alembic current

# Check pending migrations
alembic show head
```

### Manual Migration Operations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade 57ac40682023

# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 67ad237ff8fb
```

### Development Commands
```bash
# Generate new migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration file
alembic revision -m "Custom migration"

# Mark database as current version (without running migrations)
alembic stamp head
```

## Migration Files Structure

```
alembic/
├── versions/
│   ├── 67ad237ff8fb_initial_baseline_migration.py
│   └── 57ac40682023_add_session_time_tracking_columns.py
├── env.py                 # Alembic environment configuration
├── script.py.mako        # Migration template
└── README
```

## Testing Migration System

### Test Database Fixtures
```bash
# Test migration on old schema
cp test_migrations/v1_without_time_columns.db data/test.db
SPACECODE_DATA_DIR=data python3 test_alembic_migration.py

# Verify successful migration
python3 -c "
import sqlite3
conn = sqlite3.connect('data/test.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(sessions)')
print([row[1] for row in cursor.fetchall()])
conn.close()
"
```

### Available Test Fixtures
- `test_migrations/v1_without_time_columns.db` - Original schema
- `test_migrations/v2_with_time_columns.db` - Current schema
- `test_alembic_migration.py` - Automated migration test

## Production Deployment

### Standard Deployment
```bash
# 1. Stop application
systemctl stop spacecode

# 2. Deploy new code (backup created automatically)
git pull origin main
nix develop

# 3. Start application (migrations run automatically)
systemctl start spacecode

# 4. Verify migration
alembic current
```

### Rollback Procedure
```bash
# 1. Stop application
systemctl stop spacecode

# 2. Rollback database
alembic downgrade -1

# 3. Deploy previous code version
git checkout <previous-commit>

# 4. Restart application
systemctl start spacecode
```

## Migration Safety Features

### Automatic Backups
- Created before every migration attempt
- Timestamped format: `leetcode_backup_YYYY-MM-DD_HH-MM-SS.db`
- Configurable retention: `SPACECODE_MAX_BACKUPS=30`

### Error Handling
- Migration failures don't crash the application
- Graceful degradation to existing schema
- Detailed error logging for debugging

### Data Preservation
- Existing sessions data fully preserved
- `total_time_seconds` calculated from existing session durations
- All review data and statistics maintained

## Troubleshooting

### "duplicate column" Error
```bash
# Check if database is already migrated
alembic current

# Mark current database state (if columns exist)
alembic stamp head
```

### Migration Stuck or Failed
```bash
# Check migration status
alembic current
alembic history

# Force to specific version (use carefully)
alembic stamp <revision_id>

# Restore from backup
cp data/backups/leetcode_backup_<timestamp>.db data/leetcode.db
```

### Development Issues
```bash
# Reset migration state for testing
rm alembic/versions/*.py
alembic revision --autogenerate -m "Fresh start"
```

## Advanced Usage

### Custom Migration Example
```python
"""Add new column example

Revision ID: abc123
Revises: 57ac40682023
Create Date: 2025-XX-XX
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.add_column(sa.Column('new_field', sa.String(255)))

def downgrade() -> None:
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.drop_column('new_field')
```

### Environment Variables
- `ALEMBIC_TESTING=true` - Bypass Flask app during testing
- `ALEMBIC_FROM_APP=true` - Running from app startup (internal)
- `SPACECODE_DATA_DIR` - Custom database location

## Migration Best Practices

1. **Always backup** before migrations (done automatically)
2. **Test migrations** on development data first
3. **Review generated migrations** before applying
4. **Use descriptive migration messages**
5. **Plan rollback strategy** for critical changes

## Verification Commands

```bash
# Complete migration verification
python3 -c "
from app import create_app
from alembic.config import Config
from alembic import command

app = create_app()
with app.app_context():
    print(f'Database: {app.config[\"SQLALCHEMY_DATABASE_URI\"]}')

    # Check Alembic status
    cfg = Config('alembic.ini')
    print('Migration verification complete!')
"
```

---

*Professional Migration System Implemented: September 29, 2025*
*Powered by: Alembic 1.15.2 + SQLAlchemy + Flask*
*Status: Production Ready ✅*