# LeetCode SRS Problem Balance Algorithm

## Overview

The LeetCode Spaced Repetition System uses a sophisticated problem selection algorithm that balances new learning with spaced repetition review. This document provides comprehensive documentation of the algorithm for future reference and tuning.

## Core Philosophy

**Primary Goal**: Maintain effective spaced repetition while ensuring consistent exposure to new problems, preventing the system from becoming purely review-focused as the problem set grows.

**Key Challenge**: Traditional spaced repetition can lead to "new problem starvation" where overdue reviews completely dominate sessions, preventing learning of new content.

## Algorithm Architecture

### 1. Problem Categorization System

The algorithm categorizes all active problems into distinct buckets based on their review state:

#### A. **New Problems** (`stats = None`)
- **Definition**: Problems never reviewed before
- **Base Score**: 100 points
- **Purpose**: Ensure continuous learning of new concepts

#### B. **Failed Recent** (`last_rating ≤ 2 AND overdue`)
- **Definition**: Problems recently rated 0-2 (Failed/Very Hard/Hard) that are now due
- **Base Score**: 200-700 (overdue calculation) + 300 (failure boost) = **500-1000+ points**
- **Purpose**: Prioritize struggling concepts for reinforcement

#### C. **Overdue Problems** (`next_review ≤ now`)
- **Definition**: Problems past their scheduled review date (excluding failed recent)
- **Score Calculation**: `200 + min(overdue_hours * 10, 500)`
- **Score Range**: 200-700 points
- **Purpose**: Maintain spaced repetition schedule

#### D. **Reinforcement Problems** (`last_reviewed < 24h AND average_rating < 3.5`)
- **Definition**: Recently reviewed problems with poor performance, not yet due
- **Score Calculation**: `50 - (average_rating * 10)`
- **Score Range**: 15-50 points (lower average = higher score)
- **Purpose**: Additional practice for weak areas

### 2. Dynamic Scoring System

#### Base Score Assignment
```python
if stats is None:
    score = 100  # New problem
elif stats.next_review <= now:
    overdue_hours = (now - stats.next_review).total_seconds() / 3600
    score = 200 + min(overdue_hours * 10, 500)  # Cap at 700

    if stats.last_rating <= 2:
        score += 300  # Failed problem boost
else:
    # Reinforcement scoring for recent poor performance
    if recent_and_poor_performance:
        score = 50 - (stats.average_rating * 10)
```

#### Randomization Layer
- **Purpose**: Prevent deterministic ordering, add variety
- **Implementation**: Add random offset of ±20 points to final scores
- **Benefit**: Similar priority problems get mixed order

### 3. Session Composition Strategy

#### Time-Based Dynamic Loading (Primary Mode)
- **Method**: Select one problem at a time based on highest score
- **Benefit**: Natural mixing based on actual priorities
- **Implementation**: `get_next_problem()` function

#### Legacy Batch Mode (Fallback)
- **New Problem Allocation**: 25% of session slots (minimum 1 if any exist)
- **Review Allocation**: Remaining 75% of slots
- **Priority Order**:
  1. Failed recent problems (up to 50% of review slots)
  2. Overdue problems (sorted by overdue time)
  3. New problems (randomly selected)
  4. Reinforcement problems (fill remaining slots)

## Score Ranges & Priorities

### Priority Hierarchy (Highest to Lowest)
1. **Failed Recent**: 500-1000+ points
2. **Very Overdue**: 400-700 points
3. **Moderately Overdue**: 200-400 points
4. **New Problems**: 100 points
5. **Reinforcement**: 15-50 points

### Example Scenarios
- **New problem**: 100 points
- **Problem 1 hour overdue**: 210 points
- **Problem 1 day overdue**: 440 points
- **Problem 1 week overdue**: 700 points (capped)
- **Failed problem 1 hour overdue**: 510 points
- **Failed problem 1 day overdue**: 740 points
- **Recent problem (avg rating 2.0)**: 30 points
- **Recent problem (avg rating 3.5)**: 15 points

## Balance Guarantees

### New Problem Protection
- **Minimum Allocation**: At least 1 new problem per session if any exist
- **Target Allocation**: 25% of session time in batch mode
- **Score Protection**: New problems (100) beat reinforcement (15-50)

### Failed Problem Prioritization
- **Boost Multiplier**: 3x additional priority (+300 points)
- **Reasoning**: Struggling concepts need immediate attention

### Anti-Starvation Measures
- **Score Caps**: Overdue problems capped at 700 base points
- **New Problem Floor**: Always get moderate priority (100 points)
- **Randomization**: Prevents rigid deterministic ordering

## Configuration Parameters

### Tunable Constants
```python
# Problem scoring
NEW_PROBLEM_SCORE = 100
OVERDUE_BASE_SCORE = 200
OVERDUE_HOURLY_MULTIPLIER = 10
OVERDUE_SCORE_CAP = 500  # Max 700 total
FAILED_PROBLEM_BOOST = 300

# Session composition
NEW_PROBLEM_PERCENTAGE = 0.25  # 25% allocation
RANDOMIZATION_RANGE = 20  # ±20 points

# Time windows
REINFORCEMENT_WINDOW_HOURS = 24
POOR_PERFORMANCE_THRESHOLD = 3.5
```

### Adjustment Guidelines
- **Increase NEW_PROBLEM_SCORE**: More new problems vs reviews
- **Increase FAILED_PROBLEM_BOOST**: More focus on struggling areas
- **Adjust NEW_PROBLEM_PERCENTAGE**: Change new/review ratio in batch mode
- **Modify OVERDUE_MULTIPLIER**: Change urgency scaling

## Algorithm Benefits

### 1. **Balanced Learning**
- Guarantees new content exposure even with many overdue reviews
- Prevents system from becoming purely maintenance-focused

### 2. **Intelligent Prioritization**
- Failed problems get urgent attention without blocking new learning
- Overdue urgency scales naturally with delay time

### 3. **Adaptive Behavior**
- System responds to user performance patterns
- Poor performance increases reinforcement automatically

### 4. **Variety & Engagement**
- Randomization prevents monotonous patterns
- Mixed content types maintain user interest

## Performance Metrics

### Success Indicators
- **New Problem Coverage**: % of available new problems attempted over time
- **Review Adherence**: % of due problems completed within schedule
- **Failure Recovery**: Time to improve ratings on failed problems
- **Balance Ratio**: Actual new/review ratio vs target

### Warning Signs
- New problems completely absent from sessions
- Same problems appearing repeatedly
- Long delays in addressing failed problems
- User feedback about monotony or difficulty spikes

## Future Enhancement Opportunities

### 1. **Adaptive Difficulty**
- Reduce new problems when user is struggling
- Increase new problems when performing well

### 2. **Topic-Based Balancing**
- Ensure variety across problem categories/topics
- Prevent clustering in single subject areas

### 3. **User Preferences**
- Configurable balance ratios per user
- Session type selection (review-heavy vs learning-heavy)

### 4. **Performance-Based Tuning**
- Automatic parameter adjustment based on success rates
- Machine learning optimization of scoring weights

## Implementation Files

### Core Algorithm
- **`scheduler.py`**: Main algorithm implementation
  - `get_session_problems()`: Entry point
  - `get_next_problem()`: Dynamic single-problem selection
  - Scoring and categorization logic

### Integration Points
- **`app.py`**: Session management and API endpoints
- **`models.py`**: Problem statistics tracking
- **Frontend**: Session UI and problem loading

## Testing & Validation

### Unit Tests Needed
- Score calculation accuracy
- Category assignment logic
- Edge case handling (no problems, all overdue, etc.)

### Integration Tests
- End-to-end session flow
- Balance ratio verification
- Time limit handling

### User Acceptance Criteria
- New problems appear regularly in sessions
- Failed problems get appropriate attention
- System feels balanced, not overwhelming

---

*Last Updated: September 29, 2025*
*Algorithm Version: 2.0 (Time-Based Sessions with Dynamic Balance)*