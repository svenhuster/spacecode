#!/usr/bin/env python3

import os
import sqlite3
from datetime import datetime

def migrate_add_session_time_columns():
    """
    Add time tracking columns to sessions table:
    - total_time_seconds: tracks cumulative time (excluding pauses)
    - max_duration_minutes: user-configured session duration
    """

    # Determine database path using same logic as app.py
    if os.path.exists(os.path.join(os.path.dirname(__file__), '.git')) or \
       os.path.exists(os.path.join(os.path.dirname(__file__), 'flake.nix')):
        # Development mode - use local data directory
        default_data_dir = os.path.join(os.path.dirname(__file__), 'data')
    else:
        # Production mode - use user's data directory
        default_data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'spacecode')

    data_dir = os.environ.get('SPACECODE_DATA_DIR', default_data_dir)
    db_path = os.path.join(data_dir, 'leetcode.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Nothing to migrate.")
        return

    print(f"Migrating database at {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_needed = []

        if 'total_time_seconds' not in columns:
            migrations_needed.append('total_time_seconds')

        if 'max_duration_minutes' not in columns:
            migrations_needed.append('max_duration_minutes')

        if not migrations_needed:
            print("All session time columns already exist. No migration needed.")
            return

        print(f"Adding columns: {', '.join(migrations_needed)}")

        # Add columns
        if 'total_time_seconds' in migrations_needed:
            cursor.execute("""
                ALTER TABLE sessions
                ADD COLUMN total_time_seconds INTEGER DEFAULT 0
            """)
            print("Added total_time_seconds column")

        if 'max_duration_minutes' in migrations_needed:
            cursor.execute("""
                ALTER TABLE sessions
                ADD COLUMN max_duration_minutes INTEGER DEFAULT 45
            """)
            print("Added max_duration_minutes column")

        # For existing sessions, calculate total_time_seconds from duration
        if 'total_time_seconds' in migrations_needed:
            cursor.execute("""
                UPDATE sessions
                SET total_time_seconds = CAST(
                    (julianday(completed_at) - julianday(started_at)) * 24 * 60 * 60 AS INTEGER
                )
                WHERE completed_at IS NOT NULL AND started_at IS NOT NULL
            """)

            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"Updated total_time_seconds for {updated_rows} existing sessions")

        conn.commit()
        print("Migration completed successfully!")

    except sqlite3.Error as e:
        print(f"❌ Database error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

    return True

if __name__ == '__main__':
    success = migrate_add_session_time_columns()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        exit(1)