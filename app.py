#!/usr/bin/env python3

import os
import webbrowser
import threading
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlparse, parse_qs

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

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'leetcode-srs-secret-key-change-in-production'

    # Database configuration
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(data_dir, "leetcode.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    CORS(app)

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
def practice_session():
    """Practice session page"""
    current_session = None

    # Check if we have an existing active or paused session
    if 'current_session_id' in session:
        current_session = Session.query.filter(
            Session.id == session['current_session_id'],
            Session.status.in_(['active', 'paused'])
        ).first()

    # If no current session or session is completed/abandoned, start a new one
    if current_session is None:
        new_session = Session(status='active')
        db.session.add(new_session)
        db.session.commit()
        session['current_session_id'] = new_session.id
        current_session = new_session
    else:
        # Resume existing session by setting status to active
        if current_session.status == 'paused':
            current_session.status = 'active'
            current_session.paused_at = None
            db.session.commit()

    # Get problems for this session
    problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
    session_problems = get_session_problems(problems_with_stats, session_size=10)

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
            session_id=session.get('current_session_id')
        )
        db.session.add(review)

        # Update problem stats
        stats.update_stats(rating)

        # Update session
        if 'current_session_id' in session:
            current_session = Session.query.get(session['current_session_id'])
            if current_session and current_session.status == 'active':
                current_session.problems_reviewed += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'next_review': stats.next_review.isoformat(),
            'interval_hours': stats.interval_hours
        })

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
            return jsonify({
                'success': True,
                'message': f'Problem already exists (#{existing.number}: {existing.title})',
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
            'message': 'Problem added successfully!',
            'problem': problem.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-import', methods=['POST'])
def api_bulk_import():
    """Bulk import problems from JSON"""
    try:
        data = request.get_json()
        problems_data = data.get('problems', [])

        added_count = 0
        errors = []

        for problem_data in problems_data:
            try:
                url = problem_data.get('url', '').strip()
                if not url:
                    continue

                # Check if exists
                if Problem.query.filter_by(url=url).first():
                    continue

                problem = Problem(
                    url=url,
                    title=problem_data.get('title', ''),
                    number=problem_data.get('number'),
                    difficulty=problem_data.get('difficulty', ''),
                    tags=problem_data.get('tags', ''),
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
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def open_browser():
    """Open browser after a short delay to ensure server is running"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:1234')

if __name__ == '__main__':
    print("Starting LeetCode Spaced Repetition System...")
    print("Server will be available at: http://localhost:1234")
    print("Visit http://localhost:1234/bookmarklet to install the bookmarklet")
    print("Press Ctrl+C to stop the server")

    # Open browser automatically in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=True, host='0.0.0.0', port=1234)