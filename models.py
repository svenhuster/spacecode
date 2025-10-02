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
    total_time_seconds = db.Column(db.Integer, default=0)  # Time spent excluding pauses
    max_duration_minutes = db.Column(db.Integer, default=45)  # User-configured duration

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
            'total_time_seconds': self.total_time_seconds,
            'max_duration_minutes': self.max_duration_minutes,
            'duration_minutes': self.get_duration_minutes(),
            'remaining_seconds': self.get_remaining_seconds(),
            'is_time_expired': self.is_time_expired()
        }

    def get_duration_minutes(self):
        """Get actual time spent in session (excluding pauses)"""
        if self.total_time_seconds:
            return self.total_time_seconds / 60
        return None

    def get_remaining_seconds(self):
        """Get remaining time in seconds for this session"""
        # Handle case where columns don't exist yet (during migration)
        max_duration_minutes = getattr(self, 'max_duration_minutes', None)
        total_time_seconds = getattr(self, 'total_time_seconds', None)

        if not max_duration_minutes:
            return None

        max_seconds = max_duration_minutes * 60
        remaining = max_seconds - (total_time_seconds or 0)
        return max(0, remaining)

    def is_time_expired(self):
        """Check if session has exceeded its time limit"""
        # Handle case where columns don't exist yet (during migration)
        max_duration_minutes = getattr(self, 'max_duration_minutes', None)
        total_time_seconds = getattr(self, 'total_time_seconds', None)

        if not max_duration_minutes:
            return False

        max_seconds = max_duration_minutes * 60
        return (total_time_seconds or 0) >= max_seconds

    def update_time_spent(self):
        """Update total_time_seconds based on current session state"""
        if not self.started_at:
            return

        now = datetime.utcnow()

        if self.status == 'active':
            # Calculate time since session started, excluding any paused time
            session_duration = (now - self.started_at).total_seconds()

            # If we have a paused_at time in the past, subtract that paused duration
            # Note: This is a simplified approach. For more complex pause/resume tracking,
            # we would need additional pause tracking tables
            if self.paused_at:
                # We're currently active but have been paused before
                # This gets complex without detailed pause logs, so we'll handle it simply
                pass

            # For now, we'll track time when reviews are submitted
            # self.total_time_seconds will be updated in review submissions

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
        """Update stats after a review using new weighted system"""
        from scheduler import calculate_next_review, calculate_effective_rating

        self.last_rating = rating
        self.last_reviewed = datetime.utcnow()
        self.total_reviews = (self.total_reviews or 0) + 1

        # Update average rating using exponential moving average for smoother transitions
        if self.average_rating is None:
            self.average_rating = rating
        else:
            # Use exponential moving average (30% weight for new rating)
            alpha = 0.3
            self.average_rating = alpha * rating + (1 - alpha) * self.average_rating

        # Calculate next review time using new weighted system
        self.interval_hours, self.easiness_factor = calculate_next_review(
            rating, self.interval_hours, self.easiness_factor, self.repetitions,
            self.problem_id, self  # Pass full stats object for history access
        )

        self.next_review = datetime.utcnow() + timedelta(hours=self.interval_hours)

        # Update repetitions based on effective performance
        effective_rating = calculate_effective_rating(rating, self.problem_id, self)
        if effective_rating >= 3:
            self.repetitions += 1
        else:
            # Gradual decrease instead of full reset for less harsh progression
            self.repetitions = max(0, self.repetitions - 1)


class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_setting(key, default=None):
        """Get a setting value by key"""
        setting = UserSettings.query.filter_by(setting_key=key).first()
        return setting.setting_value if setting else default

    @staticmethod
    def set_setting(key, value):
        """Set a setting value by key"""
        setting = UserSettings.query.filter_by(setting_key=key).first()
        if setting:
            setting.setting_value = str(value)
            setting.updated_at = datetime.utcnow()
        else:
            setting = UserSettings(setting_key=key, setting_value=str(value))
            db.session.add(setting)
        db.session.commit()
        return setting

    @staticmethod
    def get_schedule_profile():
        """Get the current schedule profile preference"""
        return UserSettings.get_setting('schedule_profile', 'aggressive')

    @staticmethod
    def set_schedule_profile(profile_name):
        """Set the current schedule profile preference"""
        return UserSettings.set_setting('schedule_profile', profile_name)

    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }