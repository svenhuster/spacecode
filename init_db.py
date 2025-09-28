#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
from models import db, Problem, ProblemStats

def create_database():
    """Create the database and tables"""
    from app import create_app

    app = create_app()

    with app.app_context():
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

        # Check if we already have data
        problem_count = Problem.query.count()
        if problem_count > 0:
            print(f"Database already has {problem_count} problems.")
        else:
            print("Database is empty and ready for your problems!")
            print("You can add problems by:")
            print("  - Using the web interface at http://localhost:1234/problems")
            print("  - Installing the bookmarklet from http://localhost:1234/bookmarklet")
            print("  - Using the API for bulk import")

if __name__ == '__main__':
    create_database()