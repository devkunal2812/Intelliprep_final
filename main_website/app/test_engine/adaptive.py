"""
Adaptive Test Generator
========================
Selects 25 questions for an adaptive test using ML-predicted success probabilities.

Selection Algorithm:
  1. Fetch all active questions not in exclude_ids (last test's questions).
  2. Call the ML interface to get predicted success probabilities.
  3. For each domain, prefer questions in the target probability window [0.45, 0.75].
  4. Maintain round-robin difficulty diversity within the window.
  5. Maintain per-topic cap (≤ 30% of total = 7 questions).
  6. If the target window yields insufficient questions, expand the window gradually
     (±0.10 each iteration) until enough candidates are found.
  7. Fallback: use any remaining question from the domain if all else fails.

This logic is domain-balanced (aptitude=10, technical=15) and topic-diverse.
"""

import random
from collections import defaultdict, deque
from typing import List

from app.db import get_connection, put_connection
from app.test_engine.ml_interface import predict_success_probabilities
from app.config import (
    TOTAL_QUESTIONS,
    DOMAIN_QUOTAS,
    DIFFICULTIES,
    MAX_PER_TOPIC,
    ADAPTIVE_TARGET_LOW,
    ADAPTIVE_TARGET_HIGH,
)


def generate_adaptive_question_ids(
    user_id: str,
    skill_profile: dict,
    exclude_ids: List[int] | None = None,
) -> List[int]:
    """
    Generate a 25-question adaptive test for the given user.

    Args:
        user_id      : Supabase auth UUID.
        skill_profile: User's current main_user_skill dict (from DB).
        exclude_ids  : IDs of questions from the user's LAST test (must not repeat).

    Returns:
        List of 25 question IDs in shuffled order.
    """
    exclude_set = set(exclude_ids or [])

    conn = get_connection()
    cur = conn.cursor()

    selected = []
    used_ids: set[int] = set()
    topic_counter: defaultdict[str, int] = defaultdict(int)

    try:
        for domain, domain_quota in DOMAIN_QUOTAS.items():
            remaining = domain_quota

            # Fetch all active, non-excluded questions for this domain
            cur.execute(
                """
                SELECT id, topic, difficulty
                FROM main_questions
                WHERE is_active = true
                  AND domain = %s
                ORDER BY random();
                """,
                (domain,),
            )
            rows = cur.fetchall()
            candidate_ids = [r[0] for r in rows if r[0] not in exclude_set and r[0] not in used_ids]

            # ── ML CALL ───────────────────────────────────────────────────────
            # session_progress=0.0 because we're selecting at the START of the session
            probs = predict_success_probabilities(
                user_id, candidate_ids, skill_profile, session_progress=0.0
            )
            # ─────────────────────────────────────────────────────────────────

            # Enrich rows with probability
            enriched = [
                (qid, topic, diff, probs.get(qid, 0.60))
                for qid, topic, diff in rows
                if qid not in exclude_set and qid not in used_ids
            ]

            # Try to fill the domain quota with expanding window
            low, high = ADAPTIVE_TARGET_LOW, ADAPTIVE_TARGET_HIGH
            max_expansion_steps = 5

            def _pick(low_bound, high_bound):
                """Single pass round-robin within probability window."""
                nonlocal remaining, selected, used_ids, topic_counter
                by_diff = {d: deque() for d in DIFFICULTIES}
                for qid, topic, diff, prob in enriched:
                    if qid in used_ids:
                        continue
                    if low_bound <= prob <= high_bound and diff in by_diff:
                        by_diff[diff].append((qid, topic))

                while remaining > 0 and any(by_diff.values()):
                    for diff in DIFFICULTIES:
                        if remaining == 0:
                            break
                        while by_diff[diff]:
                            qid, topic = by_diff[diff].popleft()
                            if qid in used_ids:
                                continue
                            if topic_counter[topic] >= MAX_PER_TOPIC:
                                continue
                            selected.append(qid)
                            used_ids.add(qid)
                            topic_counter[topic] += 1
                            remaining -= 1
                            break

            # Step 1: target window
            _pick(low, high)

            # Step 2: expand if still short
            for _ in range(max_expansion_steps):
                if remaining == 0:
                    break
                low = max(0.0, low - 0.10)
                high = min(1.0, high + 0.10)
                _pick(low, high)

            # Step 3: hard fallback — any available question for this domain
            if remaining > 0:
                for qid, topic, diff, _ in enriched:
                    if remaining == 0:
                        break
                    if qid in used_ids:
                        continue
                    selected.append(qid)
                    used_ids.add(qid)
                    topic_counter[topic] += 1
                    remaining -= 1

            if remaining > 0:
                raise RuntimeError(
                    f"Adaptive generator could not fill domain quota for '{domain}'. "
                    f"Need {domain_quota}, only found {domain_quota - remaining}."
                )

    finally:
        cur.close()
        put_connection(conn)

    if len(selected) != TOTAL_QUESTIONS:
        raise RuntimeError(
            f"Adaptive generator produced {len(selected)} questions instead of {TOTAL_QUESTIONS}."
        )

    random.shuffle(selected)
    return selected
