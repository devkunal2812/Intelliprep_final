"""
Calibration Test Generator
==========================
Generates a fixed 25-question test using the same balanced algorithm as the
data-collection test_website.  The only difference is table names (main_questions
instead of questions) and using psycopg2 directly for efficient random ordering.

Algorithm:
  • Domain quotas: aptitude=10, technical=15
  • Difficulty: round-robin across easy/medium/hard within each domain
  • Topic cap: no topic may contribute more than 30% of the total (7 questions)
  • Backfill: if strict rules leave gaps, relax topic & difficulty constraints
  • Excludes question IDs from `exclude_ids` (the user's last completed test)
"""

import random
from collections import defaultdict, deque
from typing import List

from app.db import get_connection, put_connection
from app.config import (
    TOTAL_QUESTIONS,
    DOMAIN_QUOTAS,
    DIFFICULTIES,
    MAX_PER_TOPIC,
)


def generate_calibration_question_ids(exclude_ids: List[int] | None = None) -> List[int]:
    """
    Generate a balanced 25-question calibration test.

    Args:
        exclude_ids: Question IDs that must NOT be included (e.g. from last test).

    Returns:
        List of 25 question IDs shuffled in a presentable order.
    """
    exclude_set = set(exclude_ids or [])

    conn = get_connection()
    cur = conn.cursor()

    selected = []
    used_ids = set()
    topic_counter = defaultdict(int)

    try:
        for domain, domain_quota in DOMAIN_QUOTAS.items():
            remaining = domain_quota

            cur.execute(
                """
                SELECT id, topic, difficulty
                FROM main_questions
                WHERE domain = %s
                ORDER BY random();
                """,
                (domain,),
            )
            rows = cur.fetchall()

            # Group by difficulty for round-robin
            by_difficulty = {d: deque() for d in DIFFICULTIES}
            for qid, topic, diff in rows:
                if diff in by_difficulty and qid not in exclude_set:
                    by_difficulty[diff].append((qid, topic))

            # Round-robin pick across easy/medium/hard
            while remaining > 0 and any(by_difficulty.values()):
                for diff in DIFFICULTIES:
                    if remaining == 0:
                        break
                    if not by_difficulty[diff]:
                        continue

                    qid, topic = by_difficulty[diff].popleft()

                    if qid in used_ids:
                        continue

                    if topic_counter[topic] >= MAX_PER_TOPIC:
                        continue

                    selected.append(qid)
                    used_ids.add(qid)
                    topic_counter[topic] += 1
                    remaining -= 1

            # Backfill — relax topic cap, allow any available question
            if remaining > 0:
                for qid, topic, _ in rows:
                    if remaining == 0:
                        break
                    if qid in used_ids or qid in exclude_set:
                        continue
                    selected.append(qid)
                    used_ids.add(qid)
                    topic_counter[topic] += 1
                    remaining -= 1

            if remaining > 0:
                raise RuntimeError(
                    f"Dataset cannot satisfy domain quota for '{domain}'. "
                    f"Need {domain_quota}, only found {domain_quota - remaining}."
                )

    finally:
        cur.close()
        put_connection(conn)

    if len(selected) != TOTAL_QUESTIONS:
        raise RuntimeError(
            f"Failed to generate {TOTAL_QUESTIONS}-question calibration test "
            f"(got {len(selected)})."
        )

    random.shuffle(selected)
    return selected
