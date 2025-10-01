"""
Problem management routes for LeetCode SRS.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

from models import db, Problem, Review, Session, ProblemStats
from utils import normalize_leetcode_url, extract_problem_number_from_url, check_duplicate_problem


def register_problem_routes(app):
    """Register problem-related routes with the Flask app"""

    @app.route('/problems')
    def problems():
        """Problems management page"""
        search_query = request.args.get('search', '')
        difficulty_filter = request.args.get('difficulty', '')
        sort_by = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc')

        # Base query for active problems with stats
        query = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True)

        # Apply search filter
        if search_query:
            query = query.filter(
                (Problem.title.ilike(f'%{search_query}%')) |
                (Problem.tags.ilike(f'%{search_query}%')) |
                (Problem.number == search_query if search_query.isdigit() else False)
            )

        # Apply difficulty filter
        if difficulty_filter:
            query = query.filter(Problem.difficulty == difficulty_filter)

        # Apply sorting
        if sort_by == 'title':
            order_column = Problem.title
        elif sort_by == 'difficulty':
            order_column = Problem.difficulty
        elif sort_by == 'number':
            order_column = Problem.number
        elif sort_by == 'next_review':
            order_column = ProblemStats.next_review
        else:  # created_at
            order_column = Problem.created_at

        if sort_order == 'asc':
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())

        problems_with_stats = query.all()

        return render_template('problems.html',
                             problems_with_stats=problems_with_stats,
                             search_query=search_query,
                             difficulty_filter=difficulty_filter,
                             sort_by=sort_by,
                             sort_order=sort_order)

    @app.route('/problems/add', methods=['POST'])
    def add_problem():
        """Add a new problem"""
        try:
            url = request.form.get('url', '').strip()
            title = request.form.get('title', '').strip()
            notes = request.form.get('notes', '').strip()

            if not url:
                flash('URL is required', 'error')
                return redirect(url_for('problems'))

            # Normalize URL
            normalized_url = normalize_leetcode_url(url)

            # Extract problem number
            problem_number = extract_problem_number_from_url(normalized_url)

            # Check for duplicates
            existing_problem = check_duplicate_problem(normalized_url, problem_number)
            if existing_problem:
                flash(f'Problem already exists: {existing_problem.title}', 'warning')
                return redirect(url_for('problems'))

            # Create new problem
            new_problem = Problem(
                url=normalized_url,
                title=title,
                number=problem_number,
                notes=notes
            )

            db.session.add(new_problem)
            db.session.commit()

            flash('Problem added successfully!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding problem: {str(e)}', 'error')

        return redirect(url_for('problems'))

    @app.route('/problems/<int:problem_id>', methods=['DELETE'])
    def delete_problem(problem_id):
        """Soft delete a problem"""
        try:
            problem = Problem.query.get_or_404(problem_id)
            problem.is_active = False
            db.session.commit()
            return jsonify({'success': True, 'message': 'Problem deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/problems/<int:problem_id>/restore', methods=['POST'])
    def restore_problem(problem_id):
        """Restore a soft-deleted problem"""
        try:
            problem = Problem.query.get_or_404(problem_id)
            problem.is_active = True
            db.session.commit()
            flash('Problem restored successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error restoring problem: {str(e)}', 'error')
        return redirect(url_for('deleted_problems'))

    @app.route('/problems/deleted')
    def deleted_problems():
        """Show deleted problems"""
        deleted_problems = Problem.query.filter_by(is_active=False).order_by(Problem.created_at.desc()).all()
        return render_template('deleted_problems.html', problems=deleted_problems)

    @app.route('/stats')
    def stats():
        """Statistics page"""
        from scheduler import get_study_stats
        problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
        stats = get_study_stats(problems_with_stats)

        # Get session statistics
        completed_sessions = Session.query.filter_by(status='completed').order_by(Session.completed_at.desc()).all()

        return render_template('stats.html', stats=stats, completed_sessions=completed_sessions)

    @app.route('/bookmarklet')
    def bookmarklet():
        """Bookmarklet installation page"""
        return render_template('bookmarklet.html')