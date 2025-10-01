#!/usr/bin/env python3

import os
import shutil
import glob
from flask import Flask
from datetime import datetime
from alembic.config import Config as AlembicConfig
from alembic import command

from models import db
from config import Config
from utils import get_data_directory


def create_database_backup(data_dir):
    """Create a backup of the SQLite database on app startup"""
    db_path = os.path.join(data_dir, 'leetcode.db')
    if not os.path.exists(db_path):
        return

    backup_dir = os.path.join(data_dir, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    # Create backup with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'leetcode_backup_{timestamp}.db')

    try:
        shutil.copy2(db_path, backup_path)
        print(f"Database backup created: {backup_path}")

        # Keep only last 10 backups
        backup_files = sorted(glob.glob(os.path.join(backup_dir, 'leetcode_backup_*.db')))
        if len(backup_files) > 10:
            for old_backup in backup_files[:-10]:
                os.remove(old_backup)
                print(f"Removed old backup: {old_backup}")

    except Exception as e:
        print(f"Warning: Could not create database backup: {e}")


def run_alembic_migrations(database_url):
    """Run Alembic migrations with proper error handling"""
    try:
        # Set environment variable to indicate we're running from app
        os.environ['ALEMBIC_FROM_APP'] = 'true'

        # Find alembic.ini in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_cfg_path = os.path.join(script_dir, 'alembic.ini')

        if not os.path.exists(alembic_cfg_path):
            print("⚠ Alembic configuration not found - skipping migrations")
            return

        # Create Alembic config
        alembic_cfg = AlembicConfig(alembic_cfg_path)

        # Set the database URL directly to avoid env.py recursion
        alembic_cfg.set_main_option('sqlalchemy.url', database_url)

        # Get current revision
        try:
            command.current(alembic_cfg)
            print("✅ Database schema is up to date")
        except Exception as e:
            if "no such table: alembic_version" in str(e).lower():
                print("🔄 Initializing database with Alembic...")
                # Stamp the database with the latest revision without running migrations
                command.stamp(alembic_cfg, 'head')
                print("✅ Database initialized with current schema")
            else:
                print("🔄 Running Alembic migrations...")
                command.upgrade(alembic_cfg, 'head')
                print("✅ Alembic migrations completed")

    except Exception as e:
        print(f"⚠ Warning: Could not run Alembic migrations: {e}")
        print("  The app will continue with the current database schema.")
    finally:
        # Clean up environment variable
        os.environ.pop('ALEMBIC_FROM_APP', None)


def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS

    # Create database backup BEFORE Flask touches the database
    data_dir = get_data_directory()
    create_database_backup(data_dir)

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        # Create tables
        db.create_all()

        # Run Alembic migrations with database URL
        run_alembic_migrations(app.config['SQLALCHEMY_DATABASE_URI'])

    # Register route modules
    from routes.session import register_session_routes
    from routes.problems import register_problem_routes
    from routes.api import register_api_routes

    register_session_routes(app)
    register_problem_routes(app)
    register_api_routes(app)

    return app


app = create_app()


if __name__ == '__main__':
    # Get configuration using Config class
    port = Config.get_port()
    host = Config.get_host()
    debug = Config.is_debug()
    allow_remote = Config.allow_remote_connections()
    data_dir = get_data_directory()

    print("Starting LeetCode Spaced Repetition System...")
    if allow_remote:
        print(f"Server will be available at: http://localhost:{port} (and all network interfaces)")
    else:
        print(f"Server will be available at: http://localhost:{port} (localhost only)")
    print(f"Data directory: {data_dir}")
    print(f"Visit http://localhost:{port}/bookmarklet to install the bookmarklet")
    if not allow_remote:
        print("Note: Set SPACECODE_ALLOW_REMOTE=true to allow remote connections")
    print("Press Ctrl+C to stop the server")

    app.run(debug=debug, host=host, port=port)