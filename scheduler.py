from datetime import datetime, timedelta
import random

def calculate_next_review(rating, current_interval_hours, easiness_factor, repetitions):
    """
    Aggressive spaced repetition algorithm optimized for 4+ daily sessions.

    Args:
        rating: 0 (Failed) to 5 (Easy)
        current_interval_hours: Current interval in hours
        easiness_factor: Easiness factor (1.3 to 2.5+)
        repetitions: Number of successful repetitions

    Returns:
        tuple: (next_interval_hours, new_easiness_factor)
    """

    # Base intervals for aggressive study (in hours)
    base_intervals = {
        0: 1,    # Failed: 1 hour
        1: 2,    # Very Hard: 2 hours
        2: 4,    # Hard: 4 hours
        3: 8,    # Medium: 8 hours
        4: 24,   # Good: 24 hours (1 day)
        5: 72    # Easy: 72 hours (3 days)
    }

    # Update easiness factor based on rating
    new_easiness_factor = easiness_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    new_easiness_factor = max(1.3, new_easiness_factor)  # Minimum EF of 1.3

    # For first few repetitions, use base intervals
    if repetitions < 2 or rating < 3:
        next_interval = base_intervals.get(rating, 1)
    else:
        # For subsequent reviews, multiply by easiness factor
        if rating >= 3:
            next_interval = current_interval_hours * new_easiness_factor
        else:
            next_interval = base_intervals.get(rating, 1)  # Reset if struggling

    # Cap maximum interval at 1 week (168 hours) for aggressive study
    next_interval = min(next_interval, 168)

    # Add small random factor to prevent scheduling conflicts
    random_factor = 1 + (random.random() - 0.5) * 0.1  # ±5% variation
    next_interval *= random_factor

    return next_interval, new_easiness_factor

def get_due_problems(problems_with_stats, limit=None, randomize=True):
    """
    Get problems that are due for review.

    Args:
        problems_with_stats: List of (Problem, ProblemStats) tuples
        limit: Maximum number of problems to return
        randomize: Whether to randomize the order

    Returns:
        List of problems due for review
    """
    now = datetime.utcnow()
    due_problems = []

    for problem, stats in problems_with_stats:
        if not problem.is_active:
            continue

        if stats is None or stats.next_review <= now:
            due_problems.append(problem)

    # Sort by priority (overdue problems first, then by difficulty)
    def priority_key(problem):
        stats = problem.stats
        if stats is None:
            return (0, 0)  # New problems get highest priority

        # Calculate how overdue the problem is (in hours)
        overdue_hours = (now - stats.next_review).total_seconds() / 3600

        # Difficulty weight (prioritize harder problems slightly)
        difficulty_weight = {'Easy': 1, 'Medium': 2, 'Hard': 3}.get(problem.difficulty, 2)

        # Problems that were failed recently get higher priority
        failure_weight = 10 if stats.last_rating is not None and stats.last_rating <= 2 else 1

        return (-overdue_hours * failure_weight * difficulty_weight, random.random())

    if randomize:
        # Sort by priority but add randomness
        due_problems.sort(key=priority_key)
    else:
        # Purely random order
        random.shuffle(due_problems)

    if limit:
        due_problems = due_problems[:limit]

    return due_problems

def get_session_problems(all_problems_with_stats, session_size=10):
    """
    Get problems for a practice session.

    Args:
        all_problems_with_stats: List of (Problem, ProblemStats) tuples
        session_size: Target number of problems for the session

    Returns:
        List of problems for the session
    """
    # First, get all due problems
    due_problems = get_due_problems(all_problems_with_stats)

    if len(due_problems) >= session_size:
        return due_problems[:session_size]

    # If we don't have enough due problems, add some recent problems for reinforcement
    not_due_problems = []
    now = datetime.utcnow()

    for problem, stats in all_problems_with_stats:
        if not problem.is_active:
            continue

        if stats and stats.next_review > now:
            # Only include problems reviewed in the last 24 hours
            if stats.last_reviewed and (now - stats.last_reviewed).total_seconds() < 86400:
                not_due_problems.append(problem)

    # Prioritize problems with lower ratings for reinforcement
    not_due_problems.sort(key=lambda p: (p.stats.average_rating or 3, random.random()))

    # Fill the session
    remaining_slots = session_size - len(due_problems)
    session_problems = due_problems + not_due_problems[:remaining_slots]

    # Shuffle for variety
    random.shuffle(session_problems)

    return session_problems

def get_study_stats(problems_with_stats):
    """
    Calculate study statistics.

    Returns:
        Dictionary with study statistics
    """
    now = datetime.utcnow()
    stats = {
        'total_problems': 0,
        'due_now': 0,
        'due_today': 0,
        'due_this_week': 0,
        'by_difficulty': {'Easy': 0, 'Medium': 0, 'Hard': 0, 'Unknown': 0},
        'by_rating': {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        'average_rating': 0,
        'total_reviews': 0,
        'problems_mastered': 0  # Rating >= 4 and interval > 24 hours
    }

    total_rating_sum = 0
    rated_problems = 0

    for problem, problem_stats in problems_with_stats:
        if not problem.is_active:
            continue

        stats['total_problems'] += 1

        # Count by difficulty
        difficulty = problem.difficulty or 'Unknown'
        if difficulty in stats['by_difficulty']:
            stats['by_difficulty'][difficulty] += 1
        else:
            stats['by_difficulty']['Unknown'] += 1

        if problem_stats:
            # Due calculations
            if problem_stats.next_review <= now:
                stats['due_now'] += 1
            elif problem_stats.next_review <= now + timedelta(hours=24):
                stats['due_today'] += 1
            elif problem_stats.next_review <= now + timedelta(days=7):
                stats['due_this_week'] += 1

            # Rating statistics
            if problem_stats.last_rating is not None:
                stats['by_rating'][problem_stats.last_rating] += 1
                total_rating_sum += problem_stats.average_rating or problem_stats.last_rating
                rated_problems += 1

            stats['total_reviews'] += problem_stats.total_reviews

            # Mastered problems (high rating and long interval)
            if (problem_stats.average_rating and problem_stats.average_rating >= 4 and
                problem_stats.interval_hours > 24):
                stats['problems_mastered'] += 1
        else:
            # New problem, due now
            stats['due_now'] += 1

    if rated_problems > 0:
        stats['average_rating'] = total_rating_sum / rated_problems

    return stats