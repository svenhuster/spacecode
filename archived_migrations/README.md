# Archived Migration Scripts

This directory contains the old manual migration scripts that were used before the project transitioned to Alembic.

## Files:

- `migrate_db.py` - Original manual migration for session pause/resume
- `migrate_add_description.py` - Manual migration to add description field
- `legacy_migration_backup.py` - Backup migration utilities

## Migration History:

1. **Manual Era**: These scripts were run manually to update database schema
2. **Transition**: Database schemas were reconciled with Alembic
3. **Current**: All migrations now handled by Alembic system

## ⚠️ Important Note:

These scripts are archived for reference only. Do not run them as they may conflict with the current Alembic migration system.

For new migrations, use:
```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Reconciliation:

If you encounter migration issues, use:
```bash
python3 scripts/reconcile_migrations.py
```