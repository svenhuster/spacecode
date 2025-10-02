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
            # Log the request details for debugging
            app.logger.info(f"Session review request - Content-Type: {request.content_type}")
            app.logger.info(f"Session review request - Raw data: {request.get_data()}")

            data = request.get_json()
            app.logger.info(f"Session review request - Parsed JSON data: {data}")

            if not data:
                app.logger.error("Session review failed - Invalid JSON data")
                return jsonify({'error': 'Invalid JSON data', 'debug': 'No JSON data received'}), 400

            problem_id = data.get('problem_id')
            rating = data.get('rating')
            time_spent = data.get('time_spent', 0)

            app.logger.info(f"Session review request - problem_id: {problem_id}, rating: {rating}, time_spent: {time_spent}")

            if problem_id is None:
                app.logger.error("Session review failed - Missing problem_id")
                return jsonify({'error': 'Missing problem_id', 'debug': f'Data received: {data}'}), 400
            if rating is None:
                app.logger.error("Session review failed - Missing rating")
                return jsonify({'error': 'Missing rating', 'debug': f'Data received: {data}'}), 400

            try:
                problem_id = int(problem_id)
                rating = int(rating)
                time_spent = int(time_spent)
                app.logger.info(f"Session review request - Converted values - problem_id: {problem_id}, rating: {rating}, time_spent: {time_spent}")
            except ValueError as ve:
                app.logger.error(f"Session review failed - Value conversion error: {ve}")
                return jsonify({'error': 'Invalid data types', 'debug': f'Conversion error: {str(ve)}'}), 400

            if rating < 0 or rating > 5:
                app.logger.error(f"Session review failed - Invalid rating: {rating}")
                return jsonify({'error': 'Rating must be between 0 and 5', 'debug': f'Rating received: {rating}'}), 400

            # Get current session
            current_session = None
            session_id_from_session = session.get('current_session_id')
            app.logger.info(f"Session review request - Session ID from Flask session: {session_id_from_session}")

            if 'current_session_id' in session:
                current_session = Session.query.filter(
                    Session.id == session['current_session_id'],
                    Session.status == 'active'
                ).first()
                app.logger.info(f"Session review request - Found session: {current_session}")
                if current_session:
                    app.logger.info(f"Session review request - Session details: ID={current_session.id}, status={current_session.status}")

            if not current_session:
                app.logger.error("Session review failed - No active session found")
                return jsonify({'error': 'No active session found', 'debug': f'Session ID: {session_id_from_session}'}), 400

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

            # Check if session time has expired after this rating
            session_expired = current_session.is_time_expired()

            db.session.commit()

            # Return response with expiry status
            response_data = {
                'success': True,
                'message': f'Problem rated {rating}/5'
            }

            if session_expired:
                response_data['session_expired'] = True
                response_data['message'] = f'Problem rated {rating}/5 - session completed due to time limit'
            else:
                response_data['next_url'] = url_for('get_next_session_problem')

            return jsonify(response_data)

        except Exception as e:
            app.logger.error(f"Session review exception: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': str(e), 'debug': 'Unexpected server error - check logs'}), 500

    @app.route('/session/skip', methods=['POST'])
    def skip_problem():
        """Skip a problem in the current session"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400

            problem_id = data.get('problem_id')
            time_spent = data.get('time_spent', 0)

            if problem_id is None:
                return jsonify({'error': 'Missing problem_id'}), 400

            problem_id = int(problem_id)
            time_spent = int(time_spent)

            # Get current session
            current_session = None
            if 'current_session_id' in session:
                current_session = Session.query.filter(
                    Session.id == session['current_session_id'],
                    Session.status == 'active'
                ).first()

            if not current_session:
                return jsonify({'error': 'No active session found'}), 400

            # Check if session time has expired - don't allow skipping expired sessions
            if current_session.is_time_expired():
                return jsonify({
                    'error': 'Cannot skip - session time has expired. Please rate this problem to complete your session.',
                    'session_expired': True
                }), 400

            # Find the problem
            problem = Problem.query.get(problem_id)
            if not problem:
                return jsonify({'error': 'Problem not found'}), 404

            # Create review record with rating -1 to indicate skipped
            review = Review(
                problem_id=problem_id,
                rating=-1,  # Special rating to indicate skipped
                time_spent_seconds=time_spent,
                session_id=current_session.id
            )
            db.session.add(review)

            # Update session stats
            current_session.problems_reviewed += 1
            current_session.total_time_seconds += time_spent

            # Get next problem (excluding already reviewed/skipped ones in this session)
            reviewed_problem_ids = db.session.query(Review.problem_id).filter(
                Review.session_id == current_session.id
            )

            problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(
                Problem.is_active == True,
                ~Problem.id.in_(reviewed_problem_ids)
            ).all()
            session_problems = get_session_problems(problems_with_stats, session_size=1)

            db.session.commit()

            if not session_problems:
                return jsonify({
                    'success': True,
                    'no_problems': True,
                    'message': 'No more problems available'
                })

            next_problem = session_problems[0]
            return jsonify({
                'success': True,
                'problem': next_problem.to_dict(),
                'session': current_session.to_dict(),
                'message': 'Problem skipped'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/session/complete', methods=['POST'])
    def complete_session():
        """Complete the current session"""
        try:
            if 'current_session_id' in session:
                current_session = Session.query.get(session['current_session_id'])
                if current_session:
                    current_session.status = 'completed'
                    current_session.completed_at = datetime.utcnow()
                    db.session.commit()
                    session.pop('current_session_id', None)
                    return jsonify({
                        'success': True,
                        'message': 'Session completed successfully'
                    })
                else:
                    return jsonify({'error': 'Session not found'}), 404
            else:
                return jsonify({'error': 'No active session'}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/session/pause', methods=['POST'])
    def pause_session():
        """Pause the current session"""
        try:
            if 'current_session_id' in session:
                current_session = Session.query.get(session['current_session_id'])
                if current_session:
                    current_session.status = 'paused'
                    current_session.paused_at = datetime.utcnow()
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'message': 'Session paused successfully'
                    })
                else:
                    return jsonify({'error': 'Session not found'}), 404
            else:
                return jsonify({'error': 'No active session'}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

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
        try:
            if 'current_session_id' in session:
                current_session = Session.query.get(session['current_session_id'])
                if current_session:
                    current_session.status = 'abandoned'
                    current_session.completed_at = datetime.utcnow()
                    db.session.commit()
                    session.pop('current_session_id', None)
                    return jsonify({
                        'success': True,
                        'message': 'Session ended successfully'
                    })
                else:
                    return jsonify({'error': 'Session not found'}), 404
            else:
                return jsonify({'error': 'No active session'}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

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