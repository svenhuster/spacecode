#!/usr/bin/env python3
"""
Migration script to adjust intervals for 2 sessions/day schedule.

This script scales existing intervals appropriately for the new schedule
and recalculates next_review times.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, ProblemStats

def migrate_intervals():
    """Migrate existing intervals for 2-session schedule"""
    print("Starting migration to 2-sessions/day schedule...")

    stats_to_update = ProblemStats.query.all()
    updated_count = 0

    for stats in stats_to_update:
        old_interval = stats.interval_hours

        # Scale existing intervals for 2-session schedule
        if stats.interval_hours < 8:
            # Very short intervals (failed/very hard) → scale up for session gaps
            new_interval = stats.interval_hours * 2
        elif stats.interval_hours < 24:
            # Medium intervals → moderate scaling
            new_interval = stats.interval_hours * 1.5
        elif stats.interval_hours < 72:
            # Long intervals → gentle scaling
            new_interval = stats.interval_hours * 1.3
        else:
            # Very long intervals → cap and scale down slightly
            new_interval = min(stats.interval_hours, 240)

        # Ensure minimum interval of 4 hours for next session availability
        new_interval = max(new_interval, 4)

        # Cap at 10 days (240 hours)
        new_interval = min(new_interval, 240)

        # Update the stats
        stats.interval_hours = new_interval

        # Recalculate next_review time if we have last_reviewed
        if stats.last_reviewed:
            stats.next_review = stats.last_reviewed + timedelta(hours=new_interval)

        updated_count += 1
        print(f"Problem {stats.problem_id}: {old_interval:.1f}h → {new_interval:.1f}h")

    # Commit all changes
    try:
        db.session.commit()
        print(f"\n✅ Successfully migrated {updated_count} problem intervals!")
        print("New schedule optimized for 2 sessions/day (morning & midday)")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Migration failed: {e}")
        return False

    return True

def show_migration_preview():
    """Show what the migration would do without applying changes"""
    print("Migration Preview (no changes applied):")
    print("=" * 50)

    stats_list = ProblemStats.query.all()

    for stats in stats_list:
        old_interval = stats.interval_hours

        if stats.interval_hours < 8:
            new_interval = stats.interval_hours * 2
        elif stats.interval_hours < 24:
            new_interval = stats.interval_hours * 1.5
        elif stats.interval_hours < 72:
            new_interval = stats.interval_hours * 1.3
        else:
            new_interval = min(stats.interval_hours, 240)

        new_interval = max(new_interval, 4)
        new_interval = min(new_interval, 240)

        print(f"Problem {stats.problem_id}: {old_interval:.1f}h → {new_interval:.1f}h")

    print(f"\nTotal problems to migrate: {len(stats_list)}")

if __name__ == "__main__":
    from app import app

    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == "--preview":
            show_migration_preview()
        else:
            confirm = input("This will modify existing problem intervals. Continue? (y/N): ")
            if confirm.lower() in ['y', 'yes']:
                success = migrate_intervals()
                if success:
                    print("\n🎉 Migration complete! Your scheduling is now optimized for 2 sessions/day.")
                    print("Recommended session times: Morning (9-10:30 AM) and Midday (1-2:30 PM)")
                else:
                    sys.exit(1)
            else:
                print("Migration cancelled.")