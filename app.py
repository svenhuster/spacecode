#!/usr/bin/env python3

import os
import threading
import time
import shutil
import glob
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlparse, parse_qs
from alembic.config import Config
from alembic import command

from models import db, Problem, Review, Session, ProblemStats
from scheduler import get_session_problems, get_study_stats, calculate_next_review

def normalize_leetcode_url(url):
    """Normalize LeetCode URL by removing query parameters and fragments"""
    if not url:
        return url

    # Parse the URL
    parsed = urlparse(url)

    # Rebuild without query parameters and fragments
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # Remove trailing slash
    if normalized.endswith('/'):
        normalized = normalized[:-1]

    return normalized

def extract_problem_number_from_url(url):
    """Extract problem number from LeetCode URL"""
    if not url:
        return None

    # Try to extract from URL path like /problems/123-two-sum/
    match = re.search(r'/problems/(\d+)-', url)
    if match:
        return int(match.group(1))

    return None

def check_duplicate_problem(url, number=None):
    """Check if problem already exists by URL or number"""
    normalized_url = normalize_leetcode_url(url)

    # Check by normalized URL first
    existing_by_url = Problem.query.filter_by(url=normalized_url, is_active=True).first()
    if existing_by_url:
        return existing_by_url

    # Check by problem number if available
    if number:
        existing_by_number = Problem.query.filter_by(number=number, is_active=True).first()
        if existing_by_number:
            return existing_by_number

    # Extract number from URL if not provided
    if not number:
        number = extract_problem_number_from_url(url)
        if number:
            existing_by_number = Problem.query.filter_by(number=number, is_active=True).first()
            if existing_by_number:
                return existing_by_number

    return None

def create_database_backup(data_dir):
    """Create a backup of the SQLite database on app startup"""
    db_path = os.path.join(data_dir, 'leetcode.db')

    # Only backup if database exists
    if not os.path.exists(db_path):
        return

    # Create backups directory
    backup_dir = os.path.join(data_dir, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    # Create timestamped backup filename
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_filename = f'leetcode_backup_{timestamp}.db'
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        # Copy database file
        shutil.copy2(db_path, backup_path)
        print(f"✓ Database backup created: {backup_path}")

        # Clean up old backups (keep last 30)
        max_backups = int(os.environ.get('SPACECODE_MAX_BACKUPS', 30))
        backup_files = sorted(glob.glob(os.path.join(backup_dir, 'leetcode_backup_*.db')))

        if len(backup_files) > max_backups:
            files_to_delete = backup_files[:-max_backups]
            for old_backup in files_to_delete:
                os.remove(old_backup)
                print(f"✓ Cleaned up old backup: {os.path.basename(old_backup)}")

    except Exception as e:
        print(f"⚠ Failed to create database backup: {e}")

def run_alembic_migrations(database_url):
    """
    Run Alembic database migrations automatically on app startup.
    This replaces the manual migration system with proper version control.
    """
    # Skip if already running from Alembic CLI to avoid recursion
    if os.environ.get('ALEMBIC_FROM_APP') == 'true':
        return

    try:
        # Try to find alembic.ini in multiple locations
        # 1. Directory containing this file (for development)
        app_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_cfg_path = os.path.join(app_dir, 'alembic.ini')

        # 2. Current working directory (for nix run)
        if not os.path.exists(alembic_cfg_path):
            alembic_cfg_path = os.path.join(os.getcwd(), 'alembic.ini')

        # 3. Check if we found it
        if not os.path.exists(alembic_cfg_path):
            print("⚠ Alembic configuration not found - skipping migrations")
            return

        # Create Alembic config
        alembic_cfg = Config(alembic_cfg_path)

        # Set the database URL directly to avoid env.py recursion
        alembic_cfg.set_main_option('sqlalchemy.url', database_url)

        # Set a flag to indicate we're running from app startup
        os.environ['ALEMBIC_FROM_APP'] = 'true'

        print("🔄 Running database migrations with Alembic...")

        # Get current revision to check if migrations are needed
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine

        engine = create_engine(database_url)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()

            script_dir = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script_dir.get_current_head()

            if current_rev == head_rev:
                print("✅ Database is already up to date")
                return
            elif current_rev is None:
                print("📋 Fresh database - applying all migrations")
            else:
                print(f"🔄 Upgrading from {current_rev} to {head_rev}")

        # Apply all pending migrations
        command.upgrade(alembic_cfg, 'head')

        print("✅ Database migrations completed successfully!")

    except Exception as e:
        print(f"⚠ Failed to run database migrations: {e}")
        # For specific error about duplicate columns, this is expected
        # when transitioning from manual to Alembic migrations
        if "duplicate column name" in str(e):
            print("ℹ️  This appears to be a transition from manual to Alembic migrations")
            print("ℹ️  Consider running the reconciliation script to fix this")
        print("⚠ Continuing with existing database schema")
    finally:
        # Clean up environment variable
        os.environ.pop('ALEMBIC_FROM_APP', None)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'leetcode-srs-secret-key-change-in-production'

    # Database configuration
    # In development (when running from source), use local ./data directory
    # In production (when installed), use user's data directory
    if os.path.exists(os.path.join(os.path.dirname(__file__), '.git')) or \
       os.path.exists(os.path.join(os.path.dirname(__file__), 'flake.nix')):
        # Development mode - use local data directory
        default_data_dir = os.path.join(os.path.dirname(__file__), 'data')
    else:
        # Production mode - use user's data directory
        default_data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'spacecode')

    data_dir = os.environ.get('SPACECODE_DATA_DIR', default_data_dir)
    os.makedirs(data_dir, exist_ok=True)

    # Create database backup BEFORE Flask touches the database
    create_database_backup(data_dir)

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(data_dir, "leetcode.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Create database tables if they don't exist and run migrations
    with app.app_context():
        db.create_all()

        # Run Alembic migrations with database URL
        run_alembic_migrations(app.config['SQLALCHEMY_DATABASE_URI'])

    return app

app = create_app()

# Session management moved to Flask session storage

@app.route('/')
def dashboard():
    """Main dashboard showing study stats and due problems"""
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    stats = get_study_stats(problems_with_stats)

    # Get recent sessions
    recent_sessions = Session.query.filter(Session.status == 'completed').order_by(Session.completed_at.desc()).limit(5).all()

    # Check for incomplete sessions
    incomplete_session = None
    if 'current_session_id' in session:
        incomplete_session = Session.query.filter(
            Session.id == session['current_session_id'],
            Session.status.in_(['active', 'paused'])
        ).first()

    return render_template('index.html', stats=stats, recent_sessions=recent_sessions, incomplete_session=incomplete_session)

@app.route('/session')
def session_config():
    """Session configuration page"""
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    stats = get_study_stats(problems_with_stats)

    # Check for incomplete sessions
    incomplete_session = None
    if 'current_session_id' in session:
        incomplete_session = Session.query.filter(
            Session.id == session['current_session_id'],
            Session.status.in_(['active', 'paused'])
        ).first()

    return render_template('session_config.html', stats=stats, incomplete_session=incomplete_session)

@app.route('/session/start', methods=['POST'])
def start_session():
    """Start a new practice session with specified duration"""
    duration_minutes = int(request.form.get('duration_minutes', 45))

    # Validate duration
    if duration_minutes < 5 or duration_minutes > 300:
        flash('Session duration must be between 5 and 300 minutes', 'error')
        return redirect(url_for('session_config'))

    # Create new session
    new_session = Session(
        status='active',
        max_duration_minutes=duration_minutes,
        total_time_seconds=0
    )
    db.session.add(new_session)
    db.session.flush()  # This assigns the ID without committing
    session_id = new_session.id  # Store ID while object is still attached
    db.session.commit()  # Now commit the transaction

    session['current_session_id'] = session_id  # Use the stored ID

    return redirect(url_for('practice_session'))

@app.route('/session/practice')
def practice_session():
    """Practice session page"""
    current_session = None

    # Check if we have an existing active or paused session
    if 'current_session_id' in session:
        current_session = Session.query.filter(
            Session.id == session['current_session_id'],
            Session.status.in_(['active', 'paused'])
        ).first()

    # If no current session, redirect to config
    if current_session is None:
        flash('No active session found. Please start a new session.', 'info')
        return redirect(url_for('session_config'))

    # Check if time expired
    if current_session.is_time_expired():
        current_session.status = 'completed'
        current_session.completed_at = datetime.utcnow()
        db.session.commit()
        session.pop('current_session_id', None)
        flash('Your session time has expired! Great work!', 'success')
        return redirect(url_for('dashboard'))

    # Resume existing session by setting status to active
    if current_session.status == 'paused':
        current_session.status = 'active'
        current_session.paused_at = None
        db.session.commit()

    # Get next problem for this session
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    session_problems = get_session_problems(problems_with_stats, session_size=1)

    if not session_problems:
        flash('No problems due for review right now! Great job!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('session.html', problems=session_problems, session=current_session)

@app.route('/session/review', methods=['POST'])
def review_problem():
    """Submit a review for a problem"""
    data = request.get_json()
    problem_id = data.get('problem_id')
    rating = data.get('rating')
    time_spent = data.get('time_spent', 0)

    if not problem_id or rating is None:
        return jsonify({'error': 'Missing required fields'}), 400

    if rating < 0 or rating > 5:
        return jsonify({'error': 'Rating must be between 0 and 5'}), 400

    try:
        # Get current session
        current_session = None
        if 'current_session_id' in session:
            current_session = Session.query.get(session['current_session_id'])

        if not current_session or current_session.status != 'active':
            return jsonify({'error': 'No active session found'}), 400

        # Update session time tracking
        current_session.total_time_seconds += time_spent
        current_session.problems_reviewed += 1

        # Check if session time limit exceeded
        session_expired = current_session.is_time_expired()

        # Get or create problem stats
        problem = Problem.query.get(problem_id)
        if not problem:
            return jsonify({'error': 'Problem not found'}), 404

        stats = ProblemStats.query.get(problem_id)
        if not stats:
            stats = ProblemStats(problem_id=problem_id)
            db.session.add(stats)

        # Create review record
        review = Review(
            problem_id=problem_id,
            rating=rating,
            time_spent_seconds=time_spent,
            session_id=current_session.id
        )
        db.session.add(review)

        # Update problem stats
        stats.update_stats(rating)

        db.session.commit()

        response_data = {
            'success': True,
            'next_review': stats.next_review.isoformat(),
            'interval_hours': stats.interval_hours,
            'session_time_remaining': current_session.get_remaining_seconds(),
            'session_expired': session_expired
        }

        # If session expired, complete it
        if session_expired:
            current_session.status = 'completed'
            current_session.completed_at = datetime.utcnow()
            db.session.commit()
            response_data['session_completed'] = True

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/session/complete', methods=['POST'])
def complete_session():
    """Complete the current session"""
    if 'current_session_id' in session:
        current_session = Session.query.get(session['current_session_id'])
        if current_session:
            current_session.completed_at = datetime.utcnow()
            current_session.status = 'completed'
            db.session.commit()
        session.pop('current_session_id', None)

    return jsonify({'success': True})

@app.route('/session/pause', methods=['POST'])
def pause_session():
    """Pause the current session"""
    if 'current_session_id' in session:
        current_session = Session.query.get(session['current_session_id'])
        if current_session and current_session.status == 'active':
            current_session.status = 'paused'
            current_session.paused_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'success': True, 'message': 'Session paused'})

    return jsonify({'error': 'No active session to pause'}), 400

@app.route('/session/resume', methods=['POST'])
def resume_session():
    """Resume a paused session"""
    if 'current_session_id' in session:
        current_session = Session.query.get(session['current_session_id'])
        if current_session and current_session.status == 'paused':
            current_session.status = 'active'
            current_session.paused_at = None
            db.session.commit()
            return jsonify({'success': True, 'message': 'Session resumed'})

    return jsonify({'error': 'No paused session to resume'}), 400

@app.route('/session/abandon', methods=['POST'])
def abandon_session():
    """Abandon the current session without completing it"""
    if 'current_session_id' in session:
        current_session = Session.query.get(session['current_session_id'])
        if current_session:
            current_session.status = 'abandoned'
            current_session.completed_at = datetime.utcnow()
            db.session.commit()
        session.pop('current_session_id', None)
        return jsonify({'success': True, 'message': 'Session abandoned'})

    return jsonify({'error': 'No session to abandon'}), 400

@app.route('/problems')
def problems():
    """Problem management page"""
    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')

    query = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True)

    if search:
        query = query.filter(
            (Problem.title.contains(search)) |
            (Problem.tags.contains(search)) |
            (Problem.url.contains(search))
        )

    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)

    problems_with_stats = query.order_by(Problem.created_at.desc()).all()

    return render_template('problems.html', problems_with_stats=problems_with_stats, search=search, difficulty=difficulty)

@app.route('/problems/add', methods=['POST'])
def add_problem():
    """Add a new problem"""
    data = request.form if request.form else request.get_json()

    url = data.get('url', '').strip()
    if not url:
        if request.form:
            flash('URL is required', 'error')
            return redirect(url_for('problems'))
        return jsonify({'error': 'URL is required'}), 400

    # Normalize the URL
    normalized_url = normalize_leetcode_url(url)

    # Get problem number from data or extract from URL
    number = int(data.get('number', 0)) if data.get('number') else None
    if not number:
        number = extract_problem_number_from_url(url)

    # Check if problem already exists
    existing = check_duplicate_problem(normalized_url, number)
    if existing:
        if request.form:
            flash(f'Problem already exists (#{existing.number}: {existing.title})', 'warning')
            return redirect(url_for('problems'))
        return jsonify({'error': f'Problem already exists (#{existing.number}: {existing.title})'}), 400

    try:
        # Create problem
        problem = Problem(
            url=normalized_url,
            title=data.get('title', ''),
            number=number,
            difficulty=data.get('difficulty', ''),
            tags=data.get('tags', ''),
            description=data.get('description', ''),
            notes=data.get('notes', '')
        )
        db.session.add(problem)
        db.session.flush()

        # Create initial stats
        stats = ProblemStats(problem_id=problem.id)
        db.session.add(stats)

        db.session.commit()

        if request.form:
            flash('Problem added successfully!', 'success')
            return redirect(url_for('problems'))

        return jsonify({
            'success': True,
            'problem': problem.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        if request.form:
            flash(f'Error adding problem: {str(e)}', 'error')
            return redirect(url_for('problems'))
        return jsonify({'error': str(e)}), 500

@app.route('/problems/<int:problem_id>', methods=['DELETE'])
def delete_problem(problem_id):
    """Delete a problem"""
    try:
        problem = Problem.query.get_or_404(problem_id)
        problem.is_active = False  # Soft delete
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/problems/<int:problem_id>/restore', methods=['POST'])
def restore_problem(problem_id):
    """Restore a deleted problem"""
    try:
        problem = Problem.query.get_or_404(problem_id)
        problem.is_active = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/problems/deleted')
def deleted_problems():
    """Show recently deleted problems"""
    # Get problems deleted in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    deleted_problems_query = Problem.query.filter(
        Problem.is_active == False,
        Problem.created_at >= thirty_days_ago
    ).order_by(Problem.created_at.desc()).all()

    return render_template('deleted_problems.html', problems=deleted_problems_query)

@app.route('/stats')
def stats():
    """Statistics and analytics page"""
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    study_stats = get_study_stats(problems_with_stats)

    # Get session history
    sessions = Session.query.filter(Session.completed_at.isnot(None)).order_by(Session.completed_at.desc()).limit(30).all()

    # Get recent reviews
    recent_reviews = db.session.query(Review, Problem).join(Problem).order_by(Review.reviewed_at.desc()).limit(20).all()

    return render_template('stats.html', stats=study_stats, sessions=sessions, recent_reviews=recent_reviews)

@app.route('/bookmarklet')
def bookmarklet():
    """Bookmarklet installation page"""
    return render_template('bookmarklet.html')

@app.route('/api/due-problems')
def api_due_problems():
    """API endpoint to get due problems"""
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    session_problems = get_session_problems(problems_with_stats, session_size=int(request.args.get('limit', 10)))

    return jsonify({
        'problems': [p.to_dict() for p in session_problems],
        'count': len(session_problems)
    })

@app.route('/session/next-problem')
def get_next_session_problem():
    """API endpoint to get the next problem for the current session"""
    # Check if user has active session
    if 'current_session_id' not in session:
        return jsonify({'error': 'No active session'}), 400

    current_session = Session.query.get(session['current_session_id'])
    if not current_session or current_session.status != 'active':
        return jsonify({'error': 'No active session'}), 400

    # Check if session time expired
    if current_session.is_time_expired():
        current_session.status = 'completed'
        current_session.completed_at = datetime.utcnow()
        db.session.commit()
        session.pop('current_session_id', None)
        return jsonify({'session_expired': True}), 200

    # Get next problem using improved scheduler
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    next_problems = get_session_problems(problems_with_stats, session_size=1)

    if not next_problems:
        return jsonify({
            'no_problems': True,
            'message': 'No problems available for review right now!'
        }), 200

    problem = next_problems[0]
    return jsonify({
        'success': True,
        'problem': problem.to_dict(),
        'session': current_session.to_dict()
    })

@app.route('/api/add-problem', methods=['POST'])
def api_add_problem():
    """API endpoint for bookmarklet to add problems"""
    try:
        data = request.get_json()

        url = data.get('url', '').strip()
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Normalize the URL
        normalized_url = normalize_leetcode_url(url)

        # Get problem number from data or extract from URL
        number = data.get('number')
        if not number:
            number = extract_problem_number_from_url(url)

        # Check if problem already exists
        existing = check_duplicate_problem(normalized_url, number)
        if existing:
            # Update existing problem with new metadata (preserving all progress data)
            updated_fields = []

            # Update title if new one provided and different
            if data.get('title') and data.get('title') != existing.title:
                existing.title = data.get('title')
                updated_fields.append('title')

            # Update difficulty if new one provided and current is missing/different
            if data.get('difficulty') and data.get('difficulty') != existing.difficulty:
                existing.difficulty = data.get('difficulty')
                updated_fields.append('difficulty')

            # Update tags if new ones provided and different
            if data.get('tags'):
                new_tags = ','.join(data.get('tags')) if isinstance(data.get('tags'), list) else data.get('tags')
                if new_tags != existing.tags:
                    existing.tags = new_tags
                    updated_fields.append('tags')

            # Update description if new one provided and different/missing
            if data.get('description') and data.get('description') != existing.description:
                existing.description = data.get('description')
                updated_fields.append('description')

            # Always update URL to normalized version
            if normalized_url != existing.url:
                existing.url = normalized_url
                updated_fields.append('url')

            # Update problem number if we extracted one and it's missing
            if number and not existing.number:
                existing.number = number
                updated_fields.append('number')

            # Commit updates if any
            if updated_fields:
                db.session.commit()
                message = f'Problem updated: {", ".join(updated_fields)} (#{existing.number}: {existing.title})'
            else:
                message = f'Problem already up to date (#{existing.number}: {existing.title})'

            return jsonify({
                'success': True,
                'message': message,
                'updated_fields': updated_fields,
                'action': 'updated',
                'problem': existing.to_dict()
            })

        # Create problem
        problem = Problem(
            url=normalized_url,
            title=data.get('title', ''),
            number=number,
            difficulty=data.get('difficulty', ''),
            tags=','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', ''),
            description=data.get('description', ''),
            notes=data.get('notes', '')
        )
        db.session.add(problem)
        db.session.flush()

        # Create initial stats
        stats = ProblemStats(problem_id=problem.id)
        db.session.add(stats)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Problem created successfully! (#{problem.number}: {problem.title})',
            'action': 'created',
            'problem': problem.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data')
def api_export_data():
    """Export all user data as JSON"""
    try:
        # Get all active problems with their stats and reviews
        problems_data = []
        problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()

        for problem, stats in problems_with_stats:
            # Get all reviews for this problem
            reviews = Review.query.filter_by(problem_id=problem.id).order_by(Review.reviewed_at.desc()).all()

            problem_data = {
                'url': problem.url,
                'title': problem.title,
                'number': problem.number,
                'difficulty': problem.difficulty,
                'tags': problem.tags,
                'description': problem.description,
                'notes': problem.notes,
                'created_at': problem.created_at.isoformat() if problem.created_at else None,
                'stats': stats.to_dict() if stats else None,
                'reviews': [review.to_dict() for review in reviews]
            }
            problems_data.append(problem_data)

        # Get session history
        sessions = Session.query.filter(Session.completed_at.isnot(None)).order_by(Session.completed_at.desc()).all()
        sessions_data = [session.to_dict() for session in sessions]

        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'version': '1.0',
            'problems': problems_data,
            'sessions': sessions_data,
            'stats': get_study_stats(problems_with_stats)
        }

        return jsonify(export_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-import', methods=['POST'])
def api_bulk_import():
    """Bulk import problems from JSON"""
    try:
        data = request.get_json()
        problems_data = data.get('problems', [])

        added_count = 0
        updated_count = 0
        errors = []

        for problem_data in problems_data:
            try:
                url = problem_data.get('url', '').strip()
                if not url:
                    continue

                # Check if exists
                existing = Problem.query.filter_by(url=url, is_active=True).first()
                if existing:
                    # Update existing problem if new data provided
                    if problem_data.get('title') and not existing.title:
                        existing.title = problem_data.get('title')
                    if problem_data.get('difficulty') and not existing.difficulty:
                        existing.difficulty = problem_data.get('difficulty')
                    if problem_data.get('tags') and not existing.tags:
                        existing.tags = problem_data.get('tags')
                    if problem_data.get('description') and not existing.description:
                        existing.description = problem_data.get('description')
                    if problem_data.get('number') and not existing.number:
                        existing.number = problem_data.get('number')
                    updated_count += 1
                    continue

                problem = Problem(
                    url=url,
                    title=problem_data.get('title', ''),
                    number=problem_data.get('number'),
                    difficulty=problem_data.get('difficulty', ''),
                    tags=problem_data.get('tags', ''),
                    description=problem_data.get('description', ''),
                    notes=problem_data.get('notes', '')
                )
                db.session.add(problem)
                db.session.flush()

                stats = ProblemStats(problem_id=problem.id)
                db.session.add(stats)

                added_count += 1

            except Exception as e:
                errors.append(f"Error with {problem_data.get('url', 'unknown')}: {str(e)}")

        db.session.commit()

        return jsonify({
            'success': True,
            'added_count': added_count,
            'updated_count': updated_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Get configuration from environment variables
    port = int(os.environ.get('SPACECODE_PORT', 1234))
    debug = os.environ.get('SPACECODE_DEBUG', 'false').lower() == 'true'
    allow_remote = os.environ.get('SPACECODE_ALLOW_REMOTE', 'false').lower() == 'true'
    host = '0.0.0.0' if allow_remote else '127.0.0.1'

    # Get data directory (same logic as in create_app)
    if os.path.exists(os.path.join(os.path.dirname(__file__), '.git')) or \
       os.path.exists(os.path.join(os.path.dirname(__file__), 'flake.nix')):
        # Development mode - use local data directory
        default_data_dir = os.path.join(os.path.dirname(__file__), 'data')
    else:
        # Production mode - use user's data directory
        default_data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'spacecode')

    data_dir = os.environ.get('SPACECODE_DATA_DIR', default_data_dir)

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