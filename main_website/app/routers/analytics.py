"""
Analytics router — detailed performance analytics page.
Shows topic-by-topic accuracy, difficulty distribution, time trends, etc.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import get_current_user
from app.services.skill_profile import get_skill_profile
from app.db import get_connection, put_connection
from app.templates_env import templates

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_class=HTMLResponse)
def analytics(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    user_id = user.id
    skill = get_skill_profile(user_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Enforce lock: if there is an in-progress test, redirect to it
        cur.execute(
            """
            SELECT id FROM main_tests
            WHERE auth_user_id = %s AND status = 'IN_PROGRESS'
            ORDER BY start_time DESC LIMIT 1;
            """,
            (user_id,),
        )
        in_progress = cur.fetchone()
        if in_progress:
            return RedirectResponse(f"/test/{in_progress[0]}", status_code=302)

        # Per-difficulty accuracy
        cur.execute(
            """
            SELECT q.difficulty,
                   COUNT(*) FILTER (WHERE a.is_correct = true) AS correct,
                   COUNT(*) AS total
            FROM main_attempts a
            JOIN main_tests    t ON t.id = a.test_id
            JOIN main_questions q ON q.id = a.question_id
            WHERE t.auth_user_id = %s
              AND t.status = 'COMPLETED'
              AND a.submitted_at IS NOT NULL
            GROUP BY q.difficulty;
            """,
            (user_id,),
        )
        diff_rows = cur.fetchall()

        # Per-test accuracy trend (last 10)
        cur.execute(
            """
            SELECT t.id,
                   t.test_type,
                   t.end_time,
                   COUNT(*) FILTER (WHERE a.is_correct = true) AS correct,
                   COUNT(*) AS total
            FROM main_tests t
            JOIN main_attempts a ON a.test_id = t.id
            WHERE t.auth_user_id = %s
              AND t.status = 'COMPLETED'
              AND a.submitted_at IS NOT NULL
            GROUP BY t.id, t.test_type, t.end_time
            ORDER BY t.end_time DESC
            LIMIT 10;
            """,
            (user_id,),
        )
        trend_rows = cur.fetchall()

    finally:
        cur.close()
        put_connection(conn)

    # Difficulty accuracy
    difficulty_data = {}
    for diff, correct, total in diff_rows:
        difficulty_data[diff] = {
            "correct": correct,
            "total": total,
            "accuracy": round((correct / total) * 100, 1) if total else 0,
        }

    # Test trend (oldest first for chart)
    test_trend = [
        {
            "label": f"Test {i+1}",
            "test_type": row[1],
            "date": row[2].strftime("%d %b") if row[2] else "—",
            "accuracy": round((row[3] / row[4]) * 100, 1) if row[4] else 0,
        }
        for i, row in enumerate(reversed(trend_rows))
    ]

    # Topic accuracy from skill profile
    topic_accuracy = skill.get("topic_accuracy", {})
    topic_data = [
        {
            "topic": t.replace("_", " ").title(),
            "accuracy": round(v * 100, 1),
        }
        for t, v in sorted(topic_accuracy.items(), key=lambda x: -x[1])
    ]

    return templates.TemplateResponse(
        request, "analytics.html",
        {
            "user_email": user.email,
            "skill": skill,
            "overall_accuracy": round(skill.get("overall_accuracy", 0) * 100, 1),
            "avg_time_sec": round(skill.get("avg_time_sec", 0), 1),
            "tests_completed": skill.get("tests_completed", 0),
            "topic_data": topic_data,
            "difficulty_data": difficulty_data,
            "test_trend": test_trend,
        },
    )
