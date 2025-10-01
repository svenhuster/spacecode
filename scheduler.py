from datetime import datetime, timedelta
import random

def calculate_effective_rating(new_rating, problem_id, problem_stats):
    """
    Calculate effective rating using performance history to prevent jumping.

    Args:
        new_rating: Current rating (0-5)
        problem_id: ID of the problem being rated
        problem_stats: ProblemStats object for the problem

    Returns:
        float: Effective rating based on weighted history
    """
    if problem_stats is None or problem_stats.total_reviews == 0:
        return new_rating

    # Import here to avoid circular import
    from models import Review

    # Get last 5 reviews for this problem
    recent_reviews = Review.query.filter_by(problem_id=problem_id)\
                          .order_by(Review.reviewed_at.desc())\
                          .limit(5).all()

    if len(recent_reviews) < 2:
        # Not enough history, constrain rating jumps
        if problem_stats.last_rating is not None:
            max_increase = problem_stats.last_rating + 1.5
            return min(new_rating, max_increase)
        return min(new_rating, 3)  # Cap new problems at medium

    # Calculate weighted average (recent reviews weighted more)
    weights = [0.35, 0.25, 0.20, 0.15, 0.05]  # Most recent = 35%
    weighted_sum = 0
    weight_total = 0

    for i, review in enumerate(recent_reviews):
        if i < len(weights):
            weighted_sum += review.rating * weights[i]
            weight_total += weights[i]

    # Include current rating with highest weight
    weighted_sum += new_rating * 0.35
    weight_total += 0.35

    effective_rating = weighted_sum / weight_total

    # Prevent large jumps (max 1.5 points increase from last rating)
    if problem_stats.last_rating is not None:
        max_increase = problem_stats.last_rating + 1.5
        effective_rating = min(effective_rating, max_increase)

    # Ensure rating stays within bounds
    return max(0, min(5, effective_rating))

def calculate_next_review(rating, current_interval_hours, easiness_factor, repetitions, problem_id=None, problem_stats=None):
    """
    Spaced repetition algorithm optimized for 2 sessions/day with gradual progression.

    Args:
        rating: 0 (Failed) to 5 (Fluent) - problem-solving stages:
                0=Failed, 1=Solution, 2=Errors, 3=Debug, 4=Solved, 5=Fluent
        current_interval_hours: Current interval in hours
        easiness_factor: Easiness factor (1.3 to 2.5+)
        repetitions: Number of successful repetitions
        problem_id: ID of the problem (for history lookup)
        problem_stats: ProblemStats object for history access

    Returns:
        tuple: (next_interval_hours, new_easiness_factor)
    """

    # Base intervals for 2 sessions/day (morning & midday) in hours
    base_intervals = {
        0: 4,    # Failed: 4 hours (next session)
        1: 6,    # Solution: 6 hours (next session)
        2: 12,   # Errors: 12 hours (next day morning)
        3: 24,   # Debug: 24 hours (next day)
        4: 48,   # Solved: 48 hours (2 days)
        5: 96    # Fluent: 96 hours (4 days)
    }

    # Calculate effective rating using history if available
    if problem_id is not None and problem_stats is not None:
        effective_rating = calculate_effective_rating(rating, problem_id, problem_stats)
    else:
        effective_rating = rating

    # Update easiness factor based on effective rating (gentler adjustments)
    new_easiness_factor = easiness_factor + (0.05 - (5 - effective_rating) * 0.03)
    new_easiness_factor = max(1.3, min(2.5, new_easiness_factor))  # Keep between 1.3 and 2.5

    # Determine base interval based on effective rating
    interval_key = min(5, max(0, int(effective_rating + 0.5)))  # Round to nearest
    next_interval = base_intervals[interval_key]

    # For first few repetitions, use base intervals
    if repetitions < 2 or effective_rating < 3:
        # Use base interval directly
        pass
    else:
        # For subsequent reviews, multiply by easiness factor only if consistently good
        if effective_rating >= 3:
            next_interval = next_interval * new_easiness_factor

    # Cap maximum interval at 10 days (240 hours) for 2 sessions/day
    next_interval = min(next_interval, 240)

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

        # Problems that had issues recently get higher priority (Failed/Solution/Errors)
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

def get_session_problems(all_problems_with_stats, session_size=1):
    """
    Get problems for a practice session with balanced mix of new and review problems.

    Balance Strategy:
    - Reserve 25% of session for new/unreviewed problems (minimum 1 if any exist)
    - Prioritize overdue problems (spaced repetition)
    - Include failed recent problems for reinforcement
    - Mix in new problems even when many reviews are due

    Args:
        all_problems_with_stats: List of (Problem, ProblemStats) tuples
        session_size: Target number of problems (default 1 for dynamic loading)

    Returns:
        List of problems for the session
    """
    if session_size == 1:
        # Dynamic loading mode - return next single problem with smart selection
        return get_next_problem(all_problems_with_stats)

    # Legacy batch mode (kept for compatibility)
    now = datetime.utcnow()

    # Categorize problems
    new_problems = []           # Never reviewed
    overdue_problems = []       # Past due date
    failed_recent = []          # Recently had issues (Failed/Solution/Errors)
    reinforcement_problems = [] # Recent low ratings but not due

    for problem, stats in all_problems_with_stats:
        if not problem.is_active:
            continue

        if stats is None:
            # New problem - never reviewed
            new_problems.append(problem)
        elif stats.next_review <= now:
            # Due for review
            if stats.last_rating is not None and stats.last_rating <= 2:
                failed_recent.append(problem)
            else:
                overdue_problems.append(problem)
        elif (stats.last_reviewed and
              (now - stats.last_reviewed).total_seconds() < 86400 and
              stats.average_rating and stats.average_rating < 3.5):
            # Recently reviewed with low average rating
            reinforcement_problems.append(problem)

    # Calculate session composition
    new_slots = max(1, int(session_size * 0.25)) if new_problems else 0
    review_slots = session_size - new_slots

    # Select problems with priority ordering
    selected_problems = []

    # 1. Problems with recent issues (highest priority)
    selected_problems.extend(failed_recent[:review_slots//2])
    remaining_review = review_slots - len(selected_problems)

    # 2. Overdue problems (sorted by how overdue they are)
    overdue_problems.sort(key=lambda p: p.stats.next_review if p.stats else now)
    selected_problems.extend(overdue_problems[:remaining_review])

    # 3. New problems (randomly selected)
    random.shuffle(new_problems)
    selected_problems.extend(new_problems[:new_slots])

    # 4. Fill remaining slots with reinforcement if needed
    remaining_slots = session_size - len(selected_problems)
    if remaining_slots > 0:
        reinforcement_problems.sort(key=lambda p: (p.stats.average_rating or 3, random.random()))
        selected_problems.extend(reinforcement_problems[:remaining_slots])

    # Shuffle final list for variety
    random.shuffle(selected_problems)

    return selected_problems

def get_next_problem(all_problems_with_stats):
    """
    Get the next single problem using smart prioritization.
    This is used for time-based sessions with dynamic loading.
    """
    now = datetime.utcnow()

    # Categorize and score problems
    problem_scores = []

    for problem, stats in all_problems_with_stats:
        if not problem.is_active:
            continue

        score = 0
        category = ""

        if stats is None:
            # New problem - high priority but not overwhelming
            score = 100
            category = "new"
        else:
            # Calculate overdue score
            if stats.next_review <= now:
                overdue_hours = (now - stats.next_review).total_seconds() / 3600
                score = 200 + min(overdue_hours * 10, 500)  # Cap at 700

                # Boost problems with recent issues
                if stats.last_rating is not None and stats.last_rating <= 2:
                    score += 300
                    category = "failed_recent"
                else:
                    category = "overdue"
            else:
                # Not due yet - lower priority reinforcement
                if (stats.last_reviewed and
                    (now - stats.last_reviewed).total_seconds() < 86400):
                    if stats.average_rating and stats.average_rating < 3.5:
                        score = 50 - (stats.average_rating * 10)
                        category = "reinforcement"

        if score > 0:
            problem_scores.append((problem, score, category))

    if not problem_scores:
        return []

    # Add randomization to prevent deterministic ordering
    for i, (problem, score, category) in enumerate(problem_scores):
        randomized_score = score + random.randint(-20, 20)
        problem_scores[i] = (problem, randomized_score, category)

    # Sort by score (highest first) and return top problem
    problem_scores.sort(key=lambda x: x[1], reverse=True)

    return [problem_scores[0][0]]

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