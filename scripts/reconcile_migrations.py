#!/usr/bin/env python3
"""
Migration reconciliation script.

This script helps fix databases that were partially migrated manually
and need to be brought into sync with Alembic migrations.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_column_exists(db_path, table_name, column_name):
    """Check if a column exists in a table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return column_name in columns
    except Exception as e:
        print(f"Error checking column {column_name}: {e}")
        return False

def check_alembic_version(db_path):
    """Check current Alembic version in database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        return None

def set_alembic_version(db_path, version):
    """Set Alembic version in database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create alembic_version table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)

        # Delete existing version and insert new one
        cursor.execute("DELETE FROM alembic_version")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (version,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting Alembic version: {e}")
        return False

def analyze_database(db_path):
    """Analyze database state and determine correct Alembic version."""
    print(f"\n🔍 Analyzing database: {db_path}")

    if not os.path.exists(db_path):
        print("❌ Database file does not exist")
        return None

    # Check current Alembic version
    current_version = check_alembic_version(db_path)
    print(f"📋 Current Alembic version: {current_version or 'None'}")

    # Check what columns exist in sessions table
    session_columns = {
        'total_time_seconds': check_column_exists(db_path, 'sessions', 'total_time_seconds'),
        'max_duration_minutes': check_column_exists(db_path, 'sessions', 'max_duration_minutes'),
        'paused_at': check_column_exists(db_path, 'sessions', 'paused_at'),
        'status': check_column_exists(db_path, 'sessions', 'status'),
    }

    print("🏗️  Sessions table columns:")
    for col, exists in session_columns.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {col}")

    # Determine correct version based on what exists
    if session_columns['total_time_seconds'] and session_columns['max_duration_minutes']:
        if current_version == '281cb7424067':
            recommended_version = '281cb7424067'  # Latest
            print("✅ Database appears to be fully up to date")
        else:
            recommended_version = '281cb7424067'  # Should be at latest
            print("🔄 Database has session columns but wrong version")
    elif session_columns['paused_at'] and session_columns['status']:
        recommended_version = '67ad237ff8fb'  # Before time tracking
        print("📊 Database has basic session management")
    else:
        recommended_version = '67ad237ff8fb'  # Baseline
        print("📋 Database appears to be at baseline")

    return {
        'current_version': current_version,
        'recommended_version': recommended_version,
        'columns': session_columns
    }

def reconcile_database(db_path, target_version=None):
    """Reconcile database to correct Alembic version."""
    analysis = analyze_database(db_path)
    if not analysis:
        return False

    version_to_set = target_version or analysis['recommended_version']
    current_version = analysis['current_version']

    if current_version == version_to_set:
        print(f"✅ Database is already at correct version: {version_to_set}")
        return True

    print(f"\n🔄 Setting Alembic version to: {version_to_set}")

    if set_alembic_version(db_path, version_to_set):
        print(f"✅ Successfully set Alembic version to {version_to_set}")
        return True
    else:
        print(f"❌ Failed to set Alembic version")
        return False

def main():
    """Main reconciliation function."""
    print("🔧 SpaceCode Migration Reconciliation Tool")
    print("=" * 50)

    # Find databases to reconcile
    current_dir = Path(__file__).parent.parent
    databases = []

    # Main development database
    main_db = current_dir / "data" / "leetcode.db"
    if main_db.exists():
        databases.append(("Main development", str(main_db)))

    # Stable worktree database
    stable_db = current_dir.parent / "spacecode-stable" / "data" / "leetcode.db"
    if stable_db.exists():
        databases.append(("Stable worktree", str(stable_db)))

    if not databases:
        print("❌ No databases found to reconcile")
        return

    for name, db_path in databases:
        print(f"\n🔧 Reconciling {name} database...")
        success = reconcile_database(db_path)
        if success:
            print(f"✅ {name} database reconciled successfully")
        else:
            print(f"❌ Failed to reconcile {name} database")

    print("\n🎉 Migration reconciliation completed!")
    print("💡 You can now start the app and migrations should work smoothly")

if __name__ == "__main__":
    main()