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
    """Base configuration class - all values read from environment"""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is required")

    # Database
    @staticmethod
    def get_database_uri():
        data_dir = get_data_directory()
        return f'sqlite:///{os.path.join(data_dir, "leetcode.db")}'

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

    # Current schedule profile (required from environment)
    @classmethod
    def get_current_schedule_profile(cls):
        # Get from environment variable (required)
        env_profile = os.environ.get('SPACEDCODE_SCHEDULE')
        if not env_profile:
            raise RuntimeError("SPACEDCODE_SCHEDULE environment variable is required")

        if env_profile not in cls.SCHEDULE_PROFILES:
            available = ', '.join(cls.SCHEDULE_PROFILES.keys())
            raise RuntimeError(f"Invalid schedule profile '{env_profile}'. Available: {available}")

        return cls.SCHEDULE_PROFILES[env_profile]

    @classmethod
    def get_current_schedule_name(cls):
        """Get the name of the current schedule profile"""
        current = cls.get_current_schedule_profile()
        for name, profile in cls.SCHEDULE_PROFILES.items():
            if profile == current:
                return name
        return 'aggressive'

    # Environment-based settings (required)
    @staticmethod
    def get_port():
        port = os.environ.get('SPACEDCODE_PORT')
        if not port:
            raise RuntimeError("SPACEDCODE_PORT environment variable is required")
        return int(port)

    @staticmethod
    def get_host():
        host = os.environ.get('SPACEDCODE_HOST')
        if not host:
            raise RuntimeError("SPACEDCODE_HOST environment variable is required")
        allow_remote = os.environ.get('SPACEDCODE_ALLOW_REMOTE', 'false').lower() == 'true'
        return '0.0.0.0' if allow_remote else host

    @staticmethod
    def is_debug():
        debug = os.environ.get('SPACEDCODE_DEBUG')
        if debug is None:
            raise RuntimeError("SPACEDCODE_DEBUG environment variable is required")
        return debug.lower() == 'true'

    @staticmethod
    def allow_remote_connections():
        allow_remote = os.environ.get('SPACEDCODE_ALLOW_REMOTE')
        if allow_remote is None:
            raise RuntimeError("SPACEDCODE_ALLOW_REMOTE environment variable is required")
        return allow_remote.lower() == 'true'