"""
Session management routes for LeetCode SRS.
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

from models import db, Problem, Review, Session, ProblemStats
from scheduler import get_session_problems, get_study_stats, calculate_next_review


def register_session_routes(app):
    """Register session-related routes with the Flask app"""

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
            flash('No problems available for practice!', 'warning')
            return redirect(url_for('problems'))

        current_problem = session_problems[0]
        return render_template('session.html',
                             problem=current_problem,
                             current_session=current_session)

    @app.route('/session/review', methods=['POST'])
    def review_problem():
        """Submit a problem review"""
        try:
            problem_id = int(request.form.get('problem_id'))
            rating = int(request.form.get('rating'))
            time_spent = int(request.form.get('time_spent', 0))

            if rating < 0 or rating > 5:
                return jsonify({'error': 'Rating must be between 0 and 5'}), 400

            # Get current session
            current_session = None
            if 'current_session_id' in session:
                current_session = Session.query.filter(
                    Session.id == session['current_session_id'],
                    Session.status == 'active'
                ).first()

            if not current_session:
                return jsonify({'error': 'No active session found'}), 400

            # Find the problem
            problem = Problem.query.get(problem_id)
            if not problem:
                return jsonify({'error': 'Problem not found'}), 404

            # Create review record
            review = Review(
                problem_id=problem_id,
                rating=rating,
                time_spent_seconds=time_spent,
                session_id=current_session.id
            )
            db.session.add(review)

            # Update session stats
            current_session.problems_reviewed += 1
            current_session.total_time_seconds += time_spent

            # Update problem stats
            stats = ProblemStats.query.filter_by(problem_id=problem_id).first()
            if not stats:
                stats = ProblemStats(problem_id=problem_id)
                db.session.add(stats)

            stats.update_stats(rating)

            db.session.commit()

            # Return next problem URL for dynamic loading
            return jsonify({
                'success': True,
                'next_url': url_for('get_next_session_problem'),
                'message': f'Problem rated {rating}/5'
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
                current_session.status = 'completed'
                current_session.completed_at = datetime.utcnow()
                db.session.commit()
            session.pop('current_session_id', None)
        return redirect(url_for('dashboard'))

    @app.route('/session/pause', methods=['POST'])
    def pause_session():
        """Pause the current session"""
        if 'current_session_id' in session:
            current_session = Session.query.get(session['current_session_id'])
            if current_session:
                current_session.status = 'paused'
                current_session.paused_at = datetime.utcnow()
                db.session.commit()
        return redirect(url_for('dashboard'))

    @app.route('/session/resume', methods=['POST'])
    def resume_session():
        """Resume the current session"""
        if 'current_session_id' in session:
            current_session = Session.query.get(session['current_session_id'])
            if current_session and current_session.status == 'paused':
                current_session.status = 'active'
                current_session.paused_at = None
                db.session.commit()
                return redirect(url_for('practice_session'))
        return redirect(url_for('dashboard'))

    @app.route('/session/abandon', methods=['POST'])
    def abandon_session():
        """Abandon the current session"""
        if 'current_session_id' in session:
            current_session = Session.query.get(session['current_session_id'])
            if current_session:
                current_session.status = 'abandoned'
                current_session.completed_at = datetime.utcnow()
                db.session.commit()
            session.pop('current_session_id', None)
        return redirect(url_for('dashboard'))

    @app.route('/session/next-problem')
    def get_next_session_problem():
        """Get the next problem for the current session (dynamic loading)"""
        try:
            # Check if there's an active session
            current_session = None
            if 'current_session_id' in session:
                current_session = Session.query.filter(
                    Session.id == session['current_session_id'],
                    Session.status == 'active'
                ).first()

            if not current_session:
                return jsonify({'error': 'No active session found'}), 400

            # Check if time expired
            if current_session.is_time_expired():
                current_session.status = 'completed'
                current_session.completed_at = datetime.utcnow()
                db.session.commit()
                session.pop('current_session_id', None)
                return jsonify({
                    'session_expired': True,
                    'message': 'Your session time has expired! Great work!'
                })

            # Get next problem
            problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
            session_problems = get_session_problems(problems_with_stats, session_size=1)

            if not session_problems:
                return jsonify({'error': 'No more problems available'}), 404

            problem = session_problems[0]
            return jsonify({
                'problem': problem.to_dict(),
                'session': current_session.to_dict()
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500