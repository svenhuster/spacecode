"""
Utility functions for LeetCode SRS application.
"""

import re
from urllib.parse import urlparse
from models import Problem


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


def get_data_directory():
    """Get the data directory path with consistent logic"""
    import os

    # In development (when running from source), use local ./data directory
    # In production (when installed), use user's data directory
    if os.path.exists(os.path.join(os.path.dirname(__file__), '.git')) or \
       os.path.exists(os.path.join(os.path.dirname(__file__), 'flake.nix')):
        # Development mode - use local data directory
        default_data_dir = os.path.join(os.path.dirname(__file__), 'data')
    else:
        # Production mode - use user's data directory
        default_data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'spacecode')

    data_dir = os.environ.get('SPACECODE_DATA_DIR', default_data_dir)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir