"""
Configuration for LeetCode SRS application.
"""

import os
from utils import get_data_directory


class ScheduleProfile:
    """Schedule profile configuration for spaced repetition"""

    def __init__(self, name, description, base_intervals, max_interval_hours,
                 easiness_range, sessions_per_day, rating_descriptions=None):
        self.name = name
        self.description = description
        self.base_intervals = base_intervals
        self.max_interval_hours = max_interval_hours
        self.easiness_range = easiness_range
        self.sessions_per_day = sessions_per_day
        self.rating_descriptions = rating_descriptions or {
            0: "Failed - couldn't solve",
            1: "Solution - needed to look up solution",
            2: "Errors - solved with significant errors",
            3: "Debug - solved but needed debugging",
            4: "Solved - clean solution with minor issues",
            5: "Fluent - perfect solution quickly"
        }

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'base_intervals': self.base_intervals,
            'max_interval_hours': self.max_interval_hours,
            'easiness_range': self.easiness_range,
            'sessions_per_day': self.sessions_per_day,
            'rating_descriptions': self.rating_descriptions
        }


class Config:
    """Base configuration class"""

    # Security
    SECRET_KEY = 'leetcode-srs-secret-key-change-in-production'

    # Database
    @staticmethod
    def get_database_uri():
        data_dir = get_data_directory()
        return f'sqlite:///{os.path.join(data_dir, "leetcode.db")}'

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Server settings
    DEFAULT_PORT = 1235
    DEFAULT_HOST = '127.0.0.1'

    # Spaced Repetition Schedule Profiles
    SCHEDULE_PROFILES = {
        "aggressive": ScheduleProfile(
            name="Interview Prep",
            description="Aggressive schedule for interview preparation (2-4 sessions/day)",
            base_intervals={
                0: 4,    # Failed: 4 hours (next session)
                1: 6,    # Solution: 6 hours (next session)
                2: 12,   # Errors: 12 hours (next day morning)
                3: 24,   # Debug: 24 hours (next day)
                4: 48,   # Solved: 48 hours (2 days)
                5: 96    # Fluent: 96 hours (4 days)
            },
            max_interval_hours=240,  # 10 days max
            easiness_range=(1.3, 2.5),
            sessions_per_day="2-4"
        ),

        "regular": ScheduleProfile(
            name="Standard Study",
            description="Regular schedule for long-term retention (1 session/day)",
            base_intervals={
                0: 24,   # Failed: 1 day
                1: 48,   # Solution: 2 days
                2: 72,   # Errors: 3 days
                3: 120,  # Debug: 5 days
                4: 240,  # Solved: 10 days
                5: 480   # Fluent: 20 days
            },
            max_interval_hours=720,  # 30 days max
            easiness_range=(1.3, 3.0),
            sessions_per_day="1"
        ),

        "relaxed": ScheduleProfile(
            name="Maintenance Mode",
            description="Relaxed schedule for knowledge maintenance (3-4 sessions/week)",
            base_intervals={
                0: 48,   # Failed: 2 days
                1: 96,   # Solution: 4 days
                2: 168,  # Errors: 1 week
                3: 336,  # Debug: 2 weeks
                4: 720,  # Solved: 1 month
                5: 1440  # Fluent: 2 months
            },
            max_interval_hours=2160,  # 90 days max
            easiness_range=(1.3, 3.5),
            sessions_per_day="0.5"
        ),

        "intensive": ScheduleProfile(
            name="Bootcamp Mode",
            description="Ultra-intensive schedule for rapid learning (4+ sessions/day)",
            base_intervals={
                0: 2,    # Failed: 2 hours
                1: 3,    # Solution: 3 hours
                2: 6,    # Errors: 6 hours
                3: 12,   # Debug: 12 hours
                4: 24,   # Solved: 24 hours
                5: 48    # Fluent: 48 hours
            },
            max_interval_hours=168,  # 1 week max
            easiness_range=(1.2, 2.3),
            sessions_per_day="4+"
        )
    }

    # Current schedule profile (can be overridden by environment or database)
    @classmethod
    def get_current_schedule_profile(cls):
        # First check environment variable
        env_profile = os.environ.get('SPACEDCODE_SCHEDULE')
        if env_profile and env_profile in cls.SCHEDULE_PROFILES:
            return cls.SCHEDULE_PROFILES[env_profile]

        # Then check database settings (requires app context)
        try:
            from models import UserSettings
            db_profile = UserSettings.get_schedule_profile()
            if db_profile and db_profile in cls.SCHEDULE_PROFILES:
                return cls.SCHEDULE_PROFILES[db_profile]
        except Exception:
            # App context not available or database not initialized
            pass

        # Fall back to default
        return cls.SCHEDULE_PROFILES['aggressive']

    @classmethod
    def get_current_schedule_name(cls):
        """Get the name of the current schedule profile"""
        current = cls.get_current_schedule_profile()
        for name, profile in cls.SCHEDULE_PROFILES.items():
            if profile == current:
                return name
        return 'aggressive'

    # Environment-based settings
    @staticmethod
    def get_port():
        return int(os.environ.get('SPACEDCODE_PORT', Config.DEFAULT_PORT))

    @staticmethod
    def get_host():
        allow_remote = os.environ.get('SPACEDCODE_ALLOW_REMOTE', 'false').lower() == 'true'
        return '0.0.0.0' if allow_remote else Config.DEFAULT_HOST

    @staticmethod
    def is_debug():
        return os.environ.get('SPACEDCODE_DEBUG', 'false').lower() == 'true'

    @staticmethod
    def allow_remote_connections():
        return os.environ.get('SPACEDCODE_ALLOW_REMOTE', 'false').lower() == 'true'