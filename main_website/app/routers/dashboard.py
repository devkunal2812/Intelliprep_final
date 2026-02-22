"""
Dashboard router.

Detects whether the user is in calibration or adaptive phase.
Shows:
  - Tests completed / calibration progress
  - Overall accuracy
  - Average response time
  - Topic-wise accuracy breakdown
  - Phase indicator (calibration vs adaptive)
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user
from app.services.skill_profile import get_skill_profile
from app.config import CALIBRATION_TESTS_REQUIRED
from app.db import get_connection, put_connection

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    user_id = user.id
    skill = get_skill_profile(user_id)
    tests_completed = skill.get("tests_completed", 0)

    # Count calibration tests specifically
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) FROM main_tests
            WHERE auth_user_id = %s
              AND test_type = 'calibration'
              AND status = 'COMPLETED';
            """,
            (user_id,),
        )
        calib_done = cur.fetchone()[0]

        # Check for in-progress test
        cur.execute(
            """
            SELECT id, test_type FROM main_tests
            WHERE auth_user_id = %s AND status = 'IN_PROGRESS'
            ORDER BY start_time DESC LIMIT 1;
            """,
            (user_id,),
        )
        in_progress = cur.fetchone()
        
        # Enforce lock: If they have an active test, redirect them to it immediately
        if in_progress:
            return RedirectResponse(f"/test/{in_progress[0]}", status_code=302)

    finally:
        cur.close()
        put_connection(conn)

    in_calibration = calib_done < CALIBRATION_TESTS_REQUIRED
    calibration_progress = min(calib_done, CALIBRATION_TESTS_REQUIRED)

    # Format topic accuracy for display
    topic_accuracy = skill.get("topic_accuracy", {})
    topic_data = [
        {"topic": t.replace("_", " ").title(), "accuracy": round(v * 100, 1)}
        for t, v in sorted(topic_accuracy.items(), key=lambda x: x[1])
    ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user_email": user.email,
            "in_calibration": in_calibration,
            "calibration_done": calibration_progress,
            "calibration_required": CALIBRATION_TESTS_REQUIRED,
            "overall_accuracy": round(skill.get("overall_accuracy", 0) * 100, 1),
            "avg_time_sec": round(skill.get("avg_time_sec", 0), 1),
            "tests_completed": tests_completed,
            "topic_data": topic_data,
            "in_progress_test": in_progress,  # (id, type) or None
        },
    )
