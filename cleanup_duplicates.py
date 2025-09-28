#!/usr/bin/env python3

import os
import re
from collections import defaultdict
from urllib.parse import urlparse
from datetime import datetime

def cleanup_duplicates():
    """Find and remove duplicate problems based on problem number"""
    from app import create_app
    from models import db, Problem, ProblemStats, Review

    app = create_app()

    with app.app_context():
        print("🔍 Scanning for duplicate problems...")

        # Get all active problems
        problems = Problem.query.filter(Problem.is_active == True).all()
        print(f"Found {len(problems)} active problems")

        # Group problems by number
        by_number = defaultdict(list)
        by_normalized_url = defaultdict(list)
        problems_without_number = []

        for problem in problems:
            if problem.number:
                by_number[problem.number].append(problem)
            else:
                problems_without_number.append(problem)

            # Normalize URL and group
            normalized_url = normalize_url(problem.url)
            by_normalized_url[normalized_url].append(problem)

        # Find duplicates by number
        number_duplicates = {num: probs for num, probs in by_number.items() if len(probs) > 1}
        url_duplicates = {url: probs for url, probs in by_normalized_url.items() if len(probs) > 1}

        print(f"\n📊 Duplicate Analysis:")
        print(f"  - Problems with duplicate numbers: {len(number_duplicates)}")
        print(f"  - Problems with duplicate URLs: {len(url_duplicates)}")
        print(f"  - Problems without numbers: {len(problems_without_number)}")

        if not number_duplicates and not url_duplicates:
            print("✅ No duplicates found!")
            return

        # Handle number duplicates
        duplicates_removed = 0
        for number, problem_list in number_duplicates.items():
            print(f"\n🔢 Problem #{number} has {len(problem_list)} duplicates:")

            # Sort by created date (keep oldest)
            problem_list.sort(key=lambda p: p.created_at)

            keeper = problem_list[0]
            duplicates = problem_list[1:]

            print(f"  ✅ Keeping: {keeper.title} (ID: {keeper.id}, URL: {keeper.url})")

            for dup in duplicates:
                print(f"  ❌ Removing: {dup.title} (ID: {dup.id}, URL: {dup.url})")

                # Check if duplicate has reviews
                review_count = Review.query.filter_by(problem_id=dup.id).count()
                if review_count > 0:
                    print(f"    ⚠️  This problem has {review_count} reviews. Merging stats...")
                    merge_problem_data(keeper, dup)

                # Soft delete the duplicate
                dup.is_active = False
                duplicates_removed += 1

        # Handle URL duplicates (only if they weren't already handled by number)
        for url, problem_list in url_duplicates.items():
            # Skip if all problems in this group were already handled by number duplicates
            if all(p.number and any(p in by_number[p.number] for p in problem_list) for p in problem_list if p.number):
                continue

            print(f"\n🔗 URL {url} has {len(problem_list)} duplicates:")

            # Sort by created date (keep oldest)
            problem_list.sort(key=lambda p: p.created_at)

            keeper = problem_list[0]
            duplicates = problem_list[1:]

            print(f"  ✅ Keeping: {keeper.title} (ID: {keeper.id})")

            for dup in duplicates:
                print(f"  ❌ Removing: {dup.title} (ID: {dup.id})")

                # Check if duplicate has reviews
                review_count = Review.query.filter_by(problem_id=dup.id).count()
                if review_count > 0:
                    print(f"    ⚠️  This problem has {review_count} reviews. Merging stats...")
                    merge_problem_data(keeper, dup)

                # Soft delete the duplicate
                dup.is_active = False
                duplicates_removed += 1

        # Try to extract numbers for problems without them
        updated_numbers = 0
        for problem in problems_without_number:
            if problem.is_active:  # Skip if marked for deletion
                number = extract_number_from_url(problem.url)
                if number and number != problem.number:
                    print(f"🔢 Updating problem '{problem.title}' number from {problem.number} to {number}")
                    problem.number = number
                    updated_numbers += 1

        # Commit changes
        if duplicates_removed > 0 or updated_numbers > 0:
            try:
                db.session.commit()
                print(f"\n✅ Cleanup completed!")
                print(f"  - {duplicates_removed} duplicate problems removed")
                print(f"  - {updated_numbers} problem numbers updated")
                print(f"  - All data preserved through merging")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error during cleanup: {e}")
        else:
            print("\n✅ No changes needed")

def normalize_url(url):
    """Normalize URL by removing query parameters and fragments"""
    if not url:
        return url

    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    if normalized.endswith('/'):
        normalized = normalized[:-1]

    return normalized

def extract_number_from_url(url):
    """Extract problem number from LeetCode URL"""
    if not url:
        return None

    # Try to extract from URL path like /problems/123-two-sum/
    match = re.search(r'/problems/(\d+)-', url)
    if match:
        return int(match.group(1))

    return None

def merge_problem_data(keeper, duplicate):
    """Merge reviews and stats from duplicate to keeper"""
    from models import db, Review, ProblemStats

    # Update all reviews to point to the keeper
    Review.query.filter_by(problem_id=duplicate.id).update({'problem_id': keeper.id})

    # Merge stats if both exist
    keeper_stats = ProblemStats.query.filter_by(problem_id=keeper.id).first()
    dup_stats = ProblemStats.query.filter_by(problem_id=duplicate.id).first()

    if dup_stats:
        if keeper_stats:
            # Merge stats - keep the more progressed one
            if dup_stats.total_reviews > keeper_stats.total_reviews:
                print(f"    📊 Duplicate has more reviews ({dup_stats.total_reviews} vs {keeper_stats.total_reviews}), using duplicate's stats")
                # Update keeper's stats with duplicate's better stats
                keeper_stats.easiness_factor = dup_stats.easiness_factor
                keeper_stats.interval_hours = dup_stats.interval_hours
                keeper_stats.repetitions = dup_stats.repetitions
                keeper_stats.next_review = dup_stats.next_review
                keeper_stats.last_rating = dup_stats.last_rating
                keeper_stats.total_reviews = dup_stats.total_reviews
                keeper_stats.average_rating = dup_stats.average_rating
                keeper_stats.last_reviewed = dup_stats.last_reviewed
        else:
            # Transfer duplicate's stats to keeper
            dup_stats.problem_id = keeper.id

        # Delete duplicate's stats if we didn't transfer them
        if keeper_stats and dup_stats.problem_id == duplicate.id:
            db.session.delete(dup_stats)

if __name__ == '__main__':
    cleanup_duplicates()