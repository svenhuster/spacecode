"""
Configuration for LeetCode SRS application.
"""

import os
from utils import get_data_directory


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
    DEFAULT_PORT = 1234
    DEFAULT_HOST = '127.0.0.1'

    # Environment-based settings
    @staticmethod
    def get_port():
        return int(os.environ.get('SPACECODE_PORT', Config.DEFAULT_PORT))

    @staticmethod
    def get_host():
        allow_remote = os.environ.get('SPACECODE_ALLOW_REMOTE', 'false').lower() == 'true'
        return '0.0.0.0' if allow_remote else Config.DEFAULT_HOST

    @staticmethod
    def is_debug():
        return os.environ.get('SPACECODE_DEBUG', 'false').lower() == 'true'

    @staticmethod
    def allow_remote_connections():
        return os.environ.get('SPACECODE_ALLOW_REMOTE', 'false').lower() == 'true'