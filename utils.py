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
    """Get the data directory path - defaults to user directory, override with env var for development"""
    import os

    # Default to user's data directory (production/installed usage)
    default_data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'spacedcode')

    # Allow override via environment variable (for development or custom locations)
    data_dir = os.environ.get('SPACEDCODE_DATA_DIR', default_data_dir)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir