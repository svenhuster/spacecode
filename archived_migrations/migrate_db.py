#!/usr/bin/env python3

import os
from models import db

def migrate_database():
    """Add new columns to existing database"""
    from app import create_app

    app = create_app()

    with app.app_context():
        print("🔄 Migrating database to add session pause/resume features...")

        from sqlalchemy import text

        try:
            # Try to add the new columns
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE sessions ADD COLUMN paused_at DATETIME'))
                conn.commit()
            print("   ✅ Added paused_at column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   ⚠️  paused_at column already exists")
            else:
                print(f"   ❌ Error adding paused_at: {e}")

        try:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE sessions ADD COLUMN status VARCHAR(20) DEFAULT "active"'))
                conn.commit()
            print("   ✅ Added status column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   ⚠️  status column already exists")
            else:
                print(f"   ❌ Error adding status: {e}")

        # Update existing sessions to have status = 'completed' if they have completed_at
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE sessions
                    SET status = 'completed'
                    WHERE completed_at IS NOT NULL AND (status IS NULL OR status = 'active')
                """))
                conn.commit()
            print(f"   ✅ Updated {result.rowcount} existing sessions to 'completed' status")
        except Exception as e:
            print(f"   ❌ Error updating existing sessions: {e}")

        print("\n✅ Database migration completed!")
        print("   - Sessions now support pause/resume functionality")
        print("   - Existing sessions have been properly migrated")

if __name__ == '__main__':
    print("🧠 LeetCode SRS - Database Migration")
    print("====================================")
    print("")
    migrate_database()