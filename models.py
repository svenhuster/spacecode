from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import re

db = SQLAlchemy()

class Problem(db.Model):
    __tablename__ = 'problems'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    slug = db.Column(db.String(200))
    title = db.Column(db.String(300))
    number = db.Column(db.Integer)
    difficulty = db.Column(db.String(20))  # Easy, Medium, Hard
    tags = db.Column(db.Text)  # comma-separated
    description = db.Column(db.Text)  # Full problem description (up to 4MB)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    reviews = db.relationship('Review', backref='problem', lazy=True, cascade='all, delete-orphan')
    stats = db.relationship('ProblemStats', backref='problem', uselist=False, cascade='all, delete-orphan')

    def __init__(self, url, **kwargs):
        self.url = url
        self.slug = self.extract_slug_from_url(url)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def extract_slug_from_url(url):
        """Extract problem slug from LeetCode URL"""
        match = re.search(r'/problems/([^/]+)', url)
        return match.group(1) if match else None

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'slug': self.slug,
            'title': self.title,
            'number': self.number,
            'difficulty': self.difficulty,
            'tags': self.tags.split(',') if self.tags else [],
            'description': self.description,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'stats': self.stats.to_dict() if self.stats else None
        }

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 0-5
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_spent_seconds = db.Column(db.Integer)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'problem_id': self.problem_id,
            'rating': self.rating,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'time_spent_seconds': self.time_spent_seconds,
            'session_id': self.session_id
        }

class Session(db.Model):
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    paused_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # active, paused, completed, abandoned
    problems_reviewed = db.Column(db.Integer, default=0)

    # Relationships
    reviews = db.relationship('Review', backref='session', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'status': self.status,
            'problems_reviewed': self.problems_reviewed,
            'duration_minutes': self.get_duration_minutes()
        }

    def get_duration_minutes(self):
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds() / 60
        return None

class ProblemStats(db.Model):
    __tablename__ = 'problem_stats'

    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), primary_key=True)
    easiness_factor = db.Column(db.Float, default=2.5)
    interval_hours = db.Column(db.Float, default=1.0)
    repetitions = db.Column(db.Integer, default=0)
    next_review = db.Column(db.DateTime, default=datetime.utcnow)
    last_rating = db.Column(db.Integer)
    total_reviews = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float)
    last_reviewed = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'problem_id': self.problem_id,
            'easiness_factor': self.easiness_factor,
            'interval_hours': self.interval_hours,
            'repetitions': self.repetitions,
            'next_review': self.next_review.isoformat() if self.next_review else None,
            'last_rating': self.last_rating,
            'total_reviews': self.total_reviews,
            'average_rating': self.average_rating,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'is_due': self.is_due()
        }

    def is_due(self):
        """Check if problem is due for review"""
        return self.next_review <= datetime.utcnow()

    def update_stats(self, rating):
        """Update stats after a review"""
        from scheduler import calculate_next_review

        self.last_rating = rating
        self.last_reviewed = datetime.utcnow()
        self.total_reviews += 1

        # Update average rating
        if self.average_rating is None:
            self.average_rating = rating
        else:
            self.average_rating = (self.average_rating * (self.total_reviews - 1) + rating) / self.total_reviews

        # Calculate next review time
        self.interval_hours, self.easiness_factor = calculate_next_review(
            rating, self.interval_hours, self.easiness_factor, self.repetitions
        )

        self.next_review = datetime.utcnow() + timedelta(hours=self.interval_hours)

        if rating >= 3:
            self.repetitions += 1
        else:
            self.repetitions = 0  # Reset if struggling