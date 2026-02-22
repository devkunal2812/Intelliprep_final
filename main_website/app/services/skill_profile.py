"""
Skill Profile Service
=====================
Computes and persists the user's skill profile in main_user_skill after each
completed test.

The profile is derived entirely from behavioral data (accuracy + timing) stored
in main_attempts / main_tests — no self-declared skill levels.

Uses the service-role Supabase client so it can bypass RLS and write to
main_user_skill even though the user's anon token cannot update their own row.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from app.db import get_connection, put_connection
from app.supabase_client import supabase_admin


def compute_and_save_skill_profile(user_id: str, test_id: str) -> dict:
    """
    Called after a test is marked COMPLETED.

    1. Aggregates ALL historical attempts for the user (not just this test).
    2. Computes overall_accuracy, avg_time_sec, topic_accuracy, tests_completed.
    3. Writes the result to main_user_skill via the admin client.

    Returns the updated skill profile dict.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # ── Aggregate across all completed tests for this user ─────────────
        cur.execute(
            """
            SELECT
                a.is_correct,
                a.time_taken_sec,
                q.topic
            FROM main_attempts a
            JOIN main_tests    t ON t.id = a.test_id
            JOIN main_questions q ON q.id = a.question_id
            WHERE t.auth_user_id = %s
              AND t.status = 'COMPLETED'
              AND a.submitted_at IS NOT NULL;
            """,
            (user_id,),
        )
        rows = cur.fetchall()

        # ── Count completed tests ──────────────────────────────────────────
        cur.execute(
            """
            SELECT COUNT(*) FROM main_tests
            WHERE auth_user_id = %s AND status = 'COMPLETED';
            """,
            (user_id,),
        )
        tests_completed = cur.fetchone()[0]

    finally:
        cur.close()
        put_connection(conn)

    if not rows:
        # No data yet — keep defaults
        return {
            "overall_accuracy": 0.0,
            "avg_time_sec": 0.0,
            "topic_accuracy": {},
            "tests_completed": tests_completed,
        }

    total = len(rows)
    correct = sum(1 for is_correct, _, _ in rows if is_correct)
    total_time = sum(t for _, t, _ in rows if t is not None)

    overall_accuracy = round(correct / total, 4) if total else 0.0
    avg_time_sec = round(total_time / total, 2) if total else 0.0

    # Per-topic accuracy
    topic_data: defaultdict[str, list[bool]] = defaultdict(list)
    for is_correct, _, topic in rows:
        topic_data[topic].append(is_correct)

    topic_accuracy = {
        topic: round(sum(results) / len(results), 4)
        for topic, results in topic_data.items()
    }

    profile = {
        "overall_accuracy": overall_accuracy,
        "avg_time_sec": avg_time_sec,
        "topic_accuracy": topic_accuracy,
        "tests_completed": tests_completed,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # ── Persist to Supabase via service-role (bypasses RLS) ───────────────
    supabase_admin.table("main_user_skill").upsert(
        {
            "auth_user_id": user_id,
            "overall_accuracy": overall_accuracy,
            "avg_time_sec": avg_time_sec,
            "topic_accuracy": topic_accuracy,
            "tests_completed": tests_completed,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="auth_user_id",
    ).execute()

    return profile


def get_skill_profile(user_id: str) -> dict:
    """
    Fetch the user's skill profile from main_user_skill.
    Returns a safe default dict if the row is missing.
    """
    try:
        resp = (
            supabase_admin.table("main_user_skill")
            .select("*")
            .eq("auth_user_id", user_id)
            .single()
            .execute()
        )
        return resp.data or _default_profile()
    except Exception:
        return _default_profile()


def _default_profile() -> dict:
    return {
        "overall_accuracy": 0.0,
        "avg_time_sec": 0.0,
        "topic_accuracy": {},
        "tests_completed": 0,
    }
