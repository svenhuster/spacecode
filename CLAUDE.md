# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a **LeetCode Spaced Repetition System** - a Flask web application that helps users practice LeetCode problems using spaced repetition algorithms. The app tracks problem difficulty, user performance ratings (0-5), and schedules reviews based on an aggressive spaced repetition algorithm optimized for 4+ daily practice sessions.

## Development Environment

This project uses **Nix** for development environment management:

```bash
# Enter development environment
nix develop

# Start the application (recommended)
./run.sh

# Or manually run
python3 init_db.py  # Initialize database
python3 app.py      # Start server on http://localhost:1234
```

## Core Architecture

### Database Models (`models.py`)
- **Problem**: LeetCode problems with URL, title, number, difficulty, tags, full description (up to 4MB), and personal notes
- **Review**: Individual review sessions with ratings and timestamps
- **Session**: Practice sessions that group multiple problem reviews
- **ProblemStats**: Spaced repetition metadata (easiness factor, intervals, next review times)

### Spaced Repetition Engine (`scheduler.py`)
- Implements aggressive algorithm with base intervals: 1h (failed) to 72h (easy)
- Maximum interval capped at 1 week for aggressive study
- Problem scheduling based on overdue time, difficulty, and failure history
- Session building combines due problems + recent low-rated problems for reinforcement

### Flask Application (`app.py`)
- **Dashboard** (`/`): Study stats and recent sessions
- **Practice Session** (`/session`): Interactive problem review with keyboard shortcuts (0-5)
- **Problem Management** (`/problems`): Add/search problems with bookmarklet support
- **API Endpoints**: Bookmarklet integration, bulk import, due problems

### Frontend (`templates/`, `static/`)
- **Jinja2 Templates**: Responsive design with dark theme
- **CSS**: Modern dark UI with proper typography and animations (`static/style.css`)
- **JavaScript**: Enhanced UX with keyboard shortcuts, form validation, API utilities (`static/app.js`)

## Key Features

1. **Advanced Bookmarklet Integration**:
   - Extracts problem data from LeetCode's `__NEXT_DATA__` JSON for reliable metadata
   - Searches through all queries to find the correct question data
   - Captures full problem descriptions, difficulty, tags, and examples
   - Enhanced problem number extraction from multiple JSON fields
   - **Refresh-Safe**: Can be clicked multiple times to update metadata without losing progress

2. **Smart Update System**:
   - Single `/api/add-problem` endpoint handles both creation and updates
   - Preserves all review data, stats, and spaced repetition progress
   - Only updates metadata fields (title, difficulty, tags, description)
   - Returns clear messages indicating whether problem was created or updated

3. **Duplicate Prevention**:
   - URL normalization removes query parameters and trailing slashes
   - Problem number extraction from URLs for reliable duplicate detection
   - Comprehensive duplicate checking by both URL and problem number
   - Cleanup script available to merge existing duplicates

4. **Session Management**: Supports pausing/resuming practice sessions

5. **Keyboard Shortcuts**:
   - Rating problems with keys 0-5 during practice
   - Global navigation: Alt+D (Dashboard), Alt+P (Practice), Alt+M (Problems), Alt+S (Stats)

6. **Analytics**: Comprehensive stats tracking performance and mastery levels

7. **Dark Theme**: Modern dark UI optimized for coding sessions

## Database Initialization & Maintenance

- `init_db.py` creates tables (starts with empty database - no sample data)
- `migrate_add_description.py` adds description field to existing databases
- `cleanup_duplicates.py` finds and removes duplicate problems while preserving review data
- SQLite database stored in `data/leetcode.db`

### Migration Commands
```bash
# Add description field to existing database
python3 migrate_add_description.py

# Clean up duplicate problems
python3 cleanup_duplicates.py
```

## Frontend Architecture

### Templates Structure
- `base.html`: Common layout with navigation and flash messages
- `index.html`: Dashboard with study stats and session management
- `session.html`: Practice session interface with rating controls
- `problems.html`: Problem management with search and filters
- `stats.html`: Analytics and performance tracking
- `bookmarklet.html`: Bookmarklet installation guide

### JavaScript Features
- **Auto-enhancement**: Form validation, loading states, tooltips
- **API utilities**: Centralized request handling for AJAX operations
- **Keyboard shortcuts**: Global navigation and rating shortcuts
- **UI enhancements**: Progress indicators, smooth scrolling, notifications

## Development Notes

- Server runs on port 1234 by default
- Development includes browser auto-opening to http://localhost:1234
- Database starts empty - add problems via web interface, bookmarklet, or API
- Database uses soft deletes (is_active flag) for problem management
- Responsive design with mobile-first approach
- All frontend assets are self-contained (no external CDNs except fonts)
- never touch the prod db without permission