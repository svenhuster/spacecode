"""
API routes for LeetCode SRS.
"""

from flask import request, jsonify
from datetime import datetime
import json

from models import db, Problem, Review, Session, ProblemStats
from scheduler import get_session_problems, get_study_stats
from utils import normalize_leetcode_url, extract_problem_number_from_url, check_duplicate_problem
from idle_monitor import get_idle_monitor


def register_api_routes(app):
    """Register API routes with the Flask app"""

    @app.route('/api/due-problems')
    def api_due_problems():
        """API endpoint to get due problems"""
        try:
            problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
            due_problems = []

            for problem, stats in problems_with_stats:
                if stats and stats.is_due():
                    due_problems.append({
                        'id': problem.id,
                        'title': problem.title,
                        'url': problem.url,
                        'difficulty': problem.difficulty,
                        'next_review': stats.next_review.isoformat() if stats.next_review else None
                    })

            return jsonify(due_problems)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/add-problem', methods=['POST'])
    def api_add_problem():
        """API endpoint to add/update a problem via bookmarklet"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400

            url = data.get('url', '').strip()
            title = data.get('title', '').strip()
            difficulty = data.get('difficulty', '').strip()
            tags = data.get('tags', [])
            description = data.get('description', '').strip()
            number = data.get('number')

            if not url:
                return jsonify({'error': 'URL is required'}), 400

            # Normalize URL
            normalized_url = normalize_leetcode_url(url)

            # Extract problem number if not provided
            if not number:
                number = extract_problem_number_from_url(normalized_url)

            # Check for existing problem
            existing_problem = check_duplicate_problem(normalized_url, number)

            if existing_problem:
                # Update existing problem with new metadata
                updated_fields = []

                if title and existing_problem.title != title:
                    existing_problem.title = title
                    updated_fields.append('title')

                if difficulty and existing_problem.difficulty != difficulty:
                    existing_problem.difficulty = difficulty
                    updated_fields.append('difficulty')

                if tags:
                    new_tags = ','.join(tags) if isinstance(tags, list) else tags
                    if existing_problem.tags != new_tags:
                        existing_problem.tags = new_tags
                        updated_fields.append('tags')

                if description and existing_problem.description != description:
                    existing_problem.description = description
                    updated_fields.append('description')

                if number and existing_problem.number != number:
                    existing_problem.number = number
                    updated_fields.append('number')

                if updated_fields:
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'updated': True,
                        'problem_id': existing_problem.id,
                        'title': existing_problem.title,
                        'updated_fields': updated_fields,
                        'message': f'Problem updated: {", ".join(updated_fields)}'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'updated': False,
                        'problem_id': existing_problem.id,
                        'title': existing_problem.title,
                        'message': 'Problem already exists with same metadata'
                    })
            else:
                # Create new problem
                new_problem = Problem(
                    url=normalized_url,
                    title=title,
                    difficulty=difficulty,
                    tags=','.join(tags) if isinstance(tags, list) else tags,
                    description=description,
                    number=number
                )

                db.session.add(new_problem)
                db.session.commit()

                return jsonify({
                    'success': True,
                    'created': True,
                    'problem_id': new_problem.id,
                    'title': new_problem.title,
                    'message': 'Problem added successfully'
                })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export-data')
    def api_export_data():
        """Export all data as JSON"""
        try:
            # Get all problems with their stats
            problems_with_stats = db.session.query(Problem, ProblemStats).outerjoin(ProblemStats).filter(Problem.is_active == True).all()
            problems_data = []

            for problem, stats in problems_with_stats:
                problem_data = problem.to_dict()
                if stats:
                    problem_data['stats'] = stats.to_dict()
                problems_data.append(problem_data)

            # Get all reviews
            reviews = Review.query.all()
            reviews_data = [review.to_dict() for review in reviews]

            # Get all sessions
            sessions = Session.query.filter(Session.completed_at.isnot(None)).order_by(Session.completed_at.desc()).all()
            sessions_data = [session.to_dict() for session in sessions]

            export_data = {
                'export_date': datetime.utcnow().isoformat(),
                'version': '1.0',
                'problems': problems_data,
                'reviews': reviews_data,
                'sessions': sessions_data
            }

            return jsonify(export_data)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/bulk-import', methods=['POST'])
    def api_bulk_import():
        """Bulk import problems from JSON"""
        try:
            data = request.get_json()
            if not data or 'problems' not in data:
                return jsonify({'error': 'Invalid import data format'}), 400

            problems_data = data['problems']
            added_count = 0
            updated_count = 0
            errors = []

            for problem_data in problems_data:
                try:
                    url = problem_data.get('url', '').strip()
                    title = problem_data.get('title', '').strip()
                    difficulty = problem_data.get('difficulty', '').strip()
                    tags = problem_data.get('tags', [])
                    description = problem_data.get('description', '').strip()
                    number = problem_data.get('number')

                    if not url:
                        errors.append(f"Problem missing URL: {title}")
                        continue

                    # Normalize URL
                    normalized_url = normalize_leetcode_url(url)

                    # Extract problem number if not provided
                    if not number:
                        number = extract_problem_number_from_url(normalized_url)

                    # Check for existing problem
                    existing_problem = check_duplicate_problem(normalized_url, number)

                    if existing_problem:
                        # Update existing problem
                        existing_problem.title = title or existing_problem.title
                        existing_problem.difficulty = difficulty or existing_problem.difficulty
                        existing_problem.tags = ','.join(tags) if isinstance(tags, list) else (tags or existing_problem.tags)
                        existing_problem.description = description or existing_problem.description
                        existing_problem.number = number or existing_problem.number
                        updated_count += 1
                    else:
                        # Create new problem
                        new_problem = Problem(
                            url=normalized_url,
                            title=title,
                            difficulty=difficulty,
                            tags=','.join(tags) if isinstance(tags, list) else tags,
                            description=description,
                            number=number
                        )
                        db.session.add(new_problem)
                        added_count += 1

                except Exception as e:
                    errors.append(f"Error processing problem {problem_data.get('title', 'Unknown')}: {str(e)}")

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

    @app.route('/api/idle-status')
    def api_idle_status():
        """Get idle monitor status"""
        try:
            idle_monitor = get_idle_monitor()
            if not idle_monitor:
                return jsonify({
                    'enabled': False,
                    'reason': 'Idle monitor not initialized'
                })

            status = idle_monitor.get_status()
            return jsonify(status)

        except Exception as e:
            return jsonify({'error': str(e)}), 500