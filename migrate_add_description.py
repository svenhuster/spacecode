#!/usr/bin/env python3

import os
import sqlite3
from datetime import datetime

def migrate_database():
    """Add description column to problems table"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'leetcode.db')

    if not os.path.exists(db_path):
        print("Database not found. Run init_db.py first.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if description column already exists
        cursor.execute("PRAGMA table_info(problems)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'description' in columns:
            print("Description column already exists.")
            return

        # Add description column
        print("Adding description column to problems table...")
        cursor.execute("ALTER TABLE problems ADD COLUMN description TEXT")
        conn.commit()
        print("Description column added successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()