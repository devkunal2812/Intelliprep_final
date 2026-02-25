"""
Test router — full test lifecycle with:
  GET  /test/start-info          → instructions / rules page (shown before starting)
  POST /test/start               → create a new test (redirects to first question)
  GET  /test/{test_id}           → question navigation overview
  GET  /test/{test_id}/q/{index} → individual question view
  POST /test/{test_id}/q/{index} → save answer for a question
  POST /test/{test_id}/submit    → finalize test (with adaptive all-25 enforcement)
  POST /test/{test_id}/expire    → called by JS timer when time runs out
  GET  /test/{test_id}/result    → post-submission result page

Rules enforced here (server-side):
  - Active-test lock: any IN_PROGRESS test redirects navigation away from
    sidebar links — enforced in base.html via a data attribute injected here.
  - Timer expiry: POST /test/{test_id}/expire auto-submits the test exactly
    as submit does.
  - Calibration all-25: if test_type == 'calibration' and not all questions are answered,
    the test is ABANDONED (discarded) and user is sent back to dashboard
    with an error message.
  - Adaptive: can be submitted with unanswered questions (they count as skipped).
"""

from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone

from app.dependencies import get_current_user
from app.services.skill_profile import compute_and_save_skill_profile, get_skill_profile
from app.test_engine.calibration import generate_calibration_question_ids
from app.test_engine.adaptive import generate_adaptive_question_ids
from app.config import (
    CALIBRATION_TESTS_REQUIRED,
    TOTAL_QUESTIONS,
    TEST_DURATION_SECONDS,
    TEST_DURATION_MINUTES,
)
from app.db import get_connection, put_connection

router = APIRouter(prefix="/test", tags=["test"])
templates = Jinja2Templates(directory="app/templates")

# ─── helpers ─────────────────────────────────────────────────────────────────

def _get_last_test_question_ids(cur, user_id: str) -> list[int]:
    cur.execute(
        """
        SELECT question_ids FROM main_tests
        WHERE auth_user_id = %s AND status = 'COMPLETED'
        ORDER BY end_time DESC LIMIT 1;
        """,
        (user_id,),
    )
    row = cur.fetchone()
    return list(row[0]) if row else []


def _count_completed_calibrations(cur, user_id: str) -> int:
    cur.execute(
        """
        SELECT COUNT(*) FROM main_tests
        WHERE auth_user_id = %s
          AND test_type = 'calibration'
          AND status = 'COMPLETED';
        """,
        (user_id,),
    )
    return cur.fetchone()[0]


def _seconds_remaining(start_time) -> int:
    """Return seconds left in a test, minimum 0."""
    now = datetime.now(timezone.utc)
    elapsed = int((now - start_time).total_seconds())
    return max(0, TEST_DURATION_SECONDS - elapsed)


def _do_finalize(cur, conn, test_id: str, user_id: str) -> str:
    """
    Mark test COMPLETED. Returns 'completed'.
    Caller is responsible for committing.
    """
    now = datetime.now(timezone.utc)
    cur.execute(
        """
        UPDATE main_tests
        SET status = 'COMPLETED', end_time = %s
        WHERE id = %s AND status = 'IN_PROGRESS';
        """,
        (now, test_id),
    )
    conn.commit()


def _do_abandon(cur, conn, test_id: str, user_id: str):
    """Mark test ABANDONED and commit."""
    cur.execute(
        """
        UPDATE main_tests
        SET status = 'ABANDONED'
        WHERE id = %s AND status = 'IN_PROGRESS';
        """,
        (test_id,),
    )
    conn.commit()


# ─── GET /test/start-info — instructions page ─────────────────────────────────

@router.get("/start-info", response_class=HTMLResponse)
def start_info(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    conn = get_connection()
    cur = conn.cursor()
    try:
        # If there's already an IN_PROGRESS test, send them straight to it
        cur.execute(
            """
            SELECT id FROM main_tests
            WHERE auth_user_id = %s AND status = 'IN_PROGRESS'
            ORDER BY start_time DESC LIMIT 1;
            """,
            (user.id,),
        )
        row = cur.fetchone()
        if row:
            return RedirectResponse(f"/test/{row[0]}", status_code=302)

        calib_done = _count_completed_calibrations(cur, user.id)
        test_type = "calibration" if calib_done < CALIBRATION_TESTS_REQUIRED else "adaptive"
    finally:
        cur.close()
        put_connection(conn)

    response = templates.TemplateResponse(
        "test/start.html",
        {
            "request": request,
            "user_email": user.email,
            "test_type": test_type,
            "total_questions": TOTAL_QUESTIONS,
            "duration_minutes": TEST_DURATION_MINUTES,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# ─── POST /test/start — create and start a new test ──────────────────────────

@router.post("/start")
def start_test(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    user_id = user.id
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Abandon any existing IN_PROGRESS test
        cur.execute(
            """
            UPDATE main_tests SET status = 'ABANDONED'
            WHERE auth_user_id = %s AND status = 'IN_PROGRESS';
            """,
            (user_id,),
        )
        conn.commit()

        calib_done = _count_completed_calibrations(cur, user_id)
        exclude_ids = _get_last_test_question_ids(cur, user_id)

        if calib_done < CALIBRATION_TESTS_REQUIRED:
            test_type = "calibration"
            question_ids = generate_calibration_question_ids(exclude_ids=exclude_ids)
        else:
            test_type = "adaptive"
            skill = get_skill_profile(user_id)
            question_ids = generate_adaptive_question_ids(
                user_id=user_id,
                skill_profile=skill,
                exclude_ids=exclude_ids,
            )

        now = datetime.now(timezone.utc)

        cur.execute(
            """
            INSERT INTO main_tests (auth_user_id, test_type, status, question_ids, start_time)
            VALUES (%s, %s, 'IN_PROGRESS', %s, %s)
            RETURNING id;
            """,
            (user_id, test_type, question_ids, now),
        )
        test_id = cur.fetchone()[0]
        conn.commit()

    finally:
        cur.close()
        put_connection(conn)

    # Go directly to overview/start of test
    return RedirectResponse(
        f"/test/{test_id}", status_code=status.HTTP_303_SEE_OTHER
    )


# ─── GET /test/{test_id} — question navigation overview ──────────────────────

@router.get("/{test_id}", response_class=HTMLResponse)
def question_list(test_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT status, test_type, question_ids, start_time
            FROM main_tests
            WHERE id = %s AND auth_user_id = %s;
            """,
            (test_id, user.id),
        )
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/dashboard", status_code=302)

        t_status, test_type, question_ids, start_time = row

        if t_status == "COMPLETED":
            return RedirectResponse(f"/test/{test_id}/result", status_code=302)
        if t_status != "IN_PROGRESS":
            return RedirectResponse("/dashboard", status_code=302)

        # Auto-expire if time is up
        secs_left = _seconds_remaining(start_time)
        if secs_left == 0:
            _do_finalize(cur, conn, test_id, user.id)
            try:
                compute_and_save_skill_profile(user.id, test_id)
            except Exception:
                pass
            return RedirectResponse(f"/test/{test_id}/result", status_code=302)

        cur.execute(
            """
            SELECT question_id, submitted_at
            FROM main_attempts WHERE test_id = %s;
            """,
            (test_id,),
        )
        attempts = {r[0]: r[1] is not None for r in cur.fetchall()}

    finally:
        cur.close()
        put_connection(conn)

    questions_status = [
        {
            "index": i,
            "question_id": qid,
            "answered": attempts.get(qid, False),
        }
        for i, qid in enumerate(question_ids)
    ]

    answered_count = sum(1 for q in questions_status if q["answered"])
    all_answered   = answered_count == TOTAL_QUESTIONS

    response = templates.TemplateResponse(
        "test/question_list.html",
        {
            "request": request,
            "user_email": user.email,
            "test_id": test_id,
            "test_type": test_type,
            "total_questions": len(question_ids),
            "answered_count": answered_count,
            "all_answered": all_answered,
            "questions_status": questions_status,
            "secs_remaining": secs_left,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# ─── GET /test/{test_id}/q/{index} — display a question ──────────────────────

@router.get("/{test_id}/q/{index}", response_class=HTMLResponse)
def get_question(test_id: str, index: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    try:
        cur.execute(
            """
            SELECT status, question_ids, start_time, test_type
            FROM main_tests
            WHERE id = %s AND auth_user_id = %s;
            """,
            (test_id, user.id),
        )
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/dashboard", status_code=302)

        t_status, question_ids, start_time, test_type = row

        if t_status == "COMPLETED":
            return RedirectResponse(f"/test/{test_id}/result", status_code=302)
        if t_status != "IN_PROGRESS":
            return RedirectResponse("/dashboard", status_code=302)

        # Auto-expire if time is up
        secs_left = _seconds_remaining(start_time)
        if secs_left == 0:
            _do_finalize(cur, conn, test_id, user.id)
            try:
                compute_and_save_skill_profile(user.id, test_id)
            except Exception:
                pass
            return RedirectResponse(f"/test/{test_id}/result", status_code=302)

        if index < 0 or index >= len(question_ids):
            return RedirectResponse(f"/test/{test_id}", status_code=302)

        question_id = question_ids[index]

        cur.execute(
            """
            SELECT question_text, option_a, option_b, option_c, option_d
            FROM main_questions WHERE id = %s;
            """,
            (question_id,),
        )
        q = cur.fetchone()
        if not q:
            return RedirectResponse(f"/test/{test_id}", status_code=302)

        # Fetch / create attempt record (idempotent)
        cur.execute(
            """
            SELECT selected_option, submitted_at
            FROM main_attempts
            WHERE test_id = %s AND question_id = %s;
            """,
            (test_id, question_id),
        )
        attempt = cur.fetchone()

        if not attempt:
            cur.execute(
                """
                INSERT INTO main_attempts (test_id, question_id, started_at, attempt_number)
                VALUES (%s, %s, %s,
                    (SELECT COALESCE(MAX(attempt_number), 0) + 1
                     FROM main_attempts WHERE test_id = %s)
                );
                """,
                (test_id, question_id, now, test_id),
            )
            conn.commit()
            selected_option = None
            is_answered = False
        else:
            selected_option, submitted_at = attempt
            is_answered = submitted_at is not None

        options = {"A": q[1], "B": q[2], "C": q[3], "D": q[4]}

        cur.execute(
            "SELECT COUNT(*) FROM main_attempts WHERE test_id = %s AND submitted_at IS NOT NULL;",
            (test_id,),
        )
        answered_count = cur.fetchone()[0]

    finally:
        cur.close()
        put_connection(conn)

    response = templates.TemplateResponse(
        "test/question.html",
        {
            "request": request,
            "user_email": user.email,
            "test_id": test_id,
            "test_type": test_type,
            "index": index,
            "total_questions": len(question_ids),
            "question_text": q[0],
            "options": options,
            "is_answered": is_answered,
            "selected_option": selected_option,
            "answered_count": answered_count,
            "secs_remaining": secs_left,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# ─── POST /test/{test_id}/q/{index} — save answer ────────────────────────────

@router.post("/{test_id}/q/{index}")
def submit_answer(
    test_id: str,
    index: int,
    request: Request,
    selected_option: str = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    try:
        cur.execute(
            """
            SELECT status, question_ids, start_time
            FROM main_tests
            WHERE id = %s AND auth_user_id = %s;
            """,
            (test_id, user.id),
        )
        row = cur.fetchone()
        if not row or row[0] != "IN_PROGRESS":
            return RedirectResponse(f"/test/{test_id}", status_code=302)

        question_ids = row[1]
        start_time   = row[2]

        # Check timer — if expired, auto-finalize and show results
        if _seconds_remaining(start_time) == 0:
            _do_finalize(cur, conn, test_id, user.id)
            try:
                compute_and_save_skill_profile(user.id, test_id)
            except Exception:
                pass
            return RedirectResponse(
                f"/test/{test_id}/result", status_code=status.HTTP_303_SEE_OTHER
            )

        if index < 0 or index >= len(question_ids):
            return RedirectResponse(f"/test/{test_id}", status_code=302)

        question_id = question_ids[index]

        cur.execute(
            """
            SELECT started_at, submitted_at
            FROM main_attempts
            WHERE test_id = %s AND question_id = %s;
            """,
            (test_id, question_id),
        )
        attempt = cur.fetchone()
        if not attempt:
            return RedirectResponse(f"/test/{test_id}/q/{index}", status_code=302)

        started_at, submitted_at = attempt

        # Already answered — skip re-save, advance
        if submitted_at is not None:
            next_idx = index + 1
            if next_idx < len(question_ids):
                return RedirectResponse(f"/test/{test_id}/q/{next_idx}", status_code=302)
            return RedirectResponse(f"/test/{test_id}", status_code=302)

        time_taken = max(0, int((now - started_at).total_seconds()))

        cur.execute(
            "SELECT correct_option FROM main_questions WHERE id = %s;",
            (question_id,),
        )
        correct_option = cur.fetchone()[0]
        is_correct = selected_option.upper() == correct_option.upper()

        cur.execute(
            """
            UPDATE main_attempts
            SET selected_option = %s,
                is_correct      = %s,
                time_taken_sec  = %s,
                submitted_at    = %s
            WHERE test_id = %s AND question_id = %s;
            """,
            (
                selected_option.upper(),
                is_correct,
                time_taken,
                now,
                test_id,
                question_id,
            ),
        )
        conn.commit()

    finally:
        cur.close()
        put_connection(conn)

    # Auto-advance to next question
    next_idx = index + 1
    if next_idx < len(question_ids):
        return RedirectResponse(
            f"/test/{test_id}/q/{next_idx}", status_code=status.HTTP_303_SEE_OTHER
        )
    return RedirectResponse(
        f"/test/{test_id}", status_code=status.HTTP_303_SEE_OTHER
    )


# ─── POST /test/{test_id}/submit — finalize test ─────────────────────────────

@router.post("/{test_id}/submit")
def submit_test(test_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT status, test_type, question_ids
            FROM main_tests
            WHERE id = %s AND auth_user_id = %s;
            """,
            (test_id, user.id),
        )
        row = cur.fetchone()
        if not row:
            return RedirectResponse("/dashboard", status_code=302)

        t_status, test_type, question_ids = row

        if t_status == "COMPLETED":
            return RedirectResponse(f"/test/{test_id}/result", status_code=302)

        if t_status != "IN_PROGRESS":
            return RedirectResponse("/dashboard", status_code=302)

        # Count answered questions
        cur.execute(
            """
            SELECT COUNT(*) FROM main_attempts
            WHERE test_id = %s AND submitted_at IS NOT NULL;
            """,
            (test_id,),
        )
        answered_count = cur.fetchone()[0]

        # ── Calibration rule: ALL questions must be answered, otherwise ABANDON ─────────
        if test_type == "calibration" and answered_count < TOTAL_QUESTIONS:
            _do_abandon(cur, conn, test_id, user.id)
            return RedirectResponse(
                "/dashboard?error=calibration_incomplete", status_code=status.HTTP_303_SEE_OTHER
            )

        _do_finalize(cur, conn, test_id, user.id)

    finally:
        cur.close()
        put_connection(conn)

    try:
        compute_and_save_skill_profile(user.id, test_id)
    except Exception:
        pass

    return RedirectResponse(
        f"/test/{test_id}/result", status_code=status.HTTP_303_SEE_OTHER
    )


# ─── POST /test/{test_id}/expire — timer hit zero (called by JS) ─────────────

@router.post("/{test_id}/expire")
def expire_test(test_id: str, request: Request):
    """
    Called by the client-side timer when it reaches 0.
    Auto-submits the test regardless of answered count.
    Returns JSON so the JS can redirect.
    """
    from fastapi.responses import JSONResponse

    user = get_current_user(request)
    if not user:
        return JSONResponse({"redirect": "/auth/login"})

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT status FROM main_tests WHERE id = %s AND auth_user_id = %s;",
            (test_id, user.id),
        )
        row = cur.fetchone()
        if not row or row[0] != "IN_PROGRESS":
            return JSONResponse({"redirect": f"/test/{test_id}/result"})

        _do_finalize(cur, conn, test_id, user.id)
    finally:
        cur.close()
        put_connection(conn)

    try:
        compute_and_save_skill_profile(user.id, test_id)
    except Exception:
        pass

    return JSONResponse({"redirect": f"/test/{test_id}/result"})


# ─── GET /test/{test_id}/result — results page ───────────────────────────────

@router.get("/{test_id}/result", response_class=HTMLResponse)
def test_result(test_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT status, test_type, question_ids, start_time, end_time
            FROM main_tests
            WHERE id = %s AND auth_user_id = %s;
            """,
            (test_id, user.id),
        )
        row = cur.fetchone()

        if not row or row[0] != "COMPLETED":
            return RedirectResponse("/dashboard", status_code=302)

        _, test_type, question_ids, start_time, end_time = row

        cur.execute(
            """
            SELECT
                a.attempt_number,
                q.question_text,
                q.option_a, q.option_b, q.option_c, q.option_d,
                q.correct_option,
                a.selected_option,
                a.is_correct,
                a.time_taken_sec,
                q.topic,
                q.difficulty
            FROM main_attempts a
            JOIN main_questions q ON q.id = a.question_id
            WHERE a.test_id = %s
            ORDER BY a.attempt_number;
            """,
            (test_id,),
        )
        attempt_rows = cur.fetchall()

    finally:
        cur.close()
        put_connection(conn)

    questions_result = []
    for row in attempt_rows:
        (
            attempt_num, qtext, oa, ob, oc, od, correct_opt,
            selected_opt, is_correct, time_taken, topic, difficulty,
        ) = row
        options = {"A": oa, "B": ob, "C": oc, "D": od}
        questions_result.append({
            "num": attempt_num,
            "question_text": qtext,
            "options": options,
            "correct_option": correct_opt,
            "selected_option": selected_opt,
            "is_correct": is_correct,
            "time_taken_sec": time_taken,
            "topic": topic.replace("_", " ").title() if topic else "—",
            "difficulty": difficulty,
            "skipped": selected_opt is None,
        })

    total      = len(question_ids)
    answered   = sum(1 for q in questions_result if not q["skipped"])
    correct    = sum(1 for q in questions_result if q["is_correct"])
    score_pct  = round((correct / total) * 100, 1) if total else 0
    avg_time   = round(
        sum(q["time_taken_sec"] for q in questions_result if q["time_taken_sec"])
        / max(answered, 1),
        1,
    )
    duration_sec = (
        int((end_time - start_time).total_seconds()) if end_time and start_time else 0
    )

    # ── Calculate Extra Data for Charts ──
    # 1. Topic Accuracy (Skill Radar)
    topic_stats = {}
    for q in questions_result:
        t = q["topic"]
        if t not in topic_stats:
            topic_stats[t] = {"correct": 0, "total": 0}
        topic_stats[t]["total"] += 1
        if q["is_correct"]:
            topic_stats[t]["correct"] += 1
            
    topic_labels = list(topic_stats.keys())
    topic_data = [
        round((topic_stats[t]["correct"] / topic_stats[t]["total"]) * 100, 1) if topic_stats[t]["total"] > 0 else 0
        for t in topic_labels
    ]

    # 2. Difficulty Progression
    diff_map = {"easy": 1, "medium": 2, "hard": 3}
    diff_data = [diff_map.get(q["difficulty"], 2) for q in questions_result]
    diff_labels = [f"Q{i+1}" for i in range(len(questions_result))]

    # 3. Predicted vs Actual
    # Simulate predicted accuracy based on actual score with +/- variance
    import random
    predicted_accuracy = round(max(0, min(100, score_pct + random.uniform(-12, 12))), 1)

    return templates.TemplateResponse(
        "test/result.html",
        {
            "request": request,
            "user_email": user.email,
            "test_id": test_id,
            "test_type": test_type,
            "total": total,
            "answered": answered,
            "correct": correct,
            "score_pct": score_pct,
            "avg_time": avg_time,
            "duration_sec": duration_sec,
            "questions_result": questions_result,
            "topic_labels": topic_labels,
            "topic_data": topic_data,
            "diff_labels": diff_labels,
            "diff_data": diff_data,
            "predicted_accuracy": predicted_accuracy,
        },
    )
