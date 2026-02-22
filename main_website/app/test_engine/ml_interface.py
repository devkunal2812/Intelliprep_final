"""
ML Model Integration — IntelliPrep Adaptive Engine
====================================================
Loads the XGBoost model trained by test/train_model.py and scores a batch
of candidate questions for a given user.

Contract (unchanged from the stub):
    Input : user_id (str)
            question_ids (list[int])
            skill_profile (dict)  ← from main_user_skill row
    Output: dict[int, float]      ← question_id -> P(correct) in [0.0, 1.0]

The adaptive generator in adaptive.py calls this function and filters
questions whose probability falls in [ADAPTIVE_TARGET_LOW, ADAPTIVE_TARGET_HIGH].

Feature vector per question (must match training order in train_model.py):
    [0] overall_performance       ← skill_profile["overall_accuracy"]
    [1] topic_performance         ← skill_profile["topic_accuracy"].get(topic, overall)
    [2] behavioral_summary_score  ← 1 - min(avg_time_sec / 120, 1)
    [3] domain_id                 ← encoded: aptitude=0, technical=1
    [4] topic_id                  ← from topic_vocab.json
    [5] difficulty_level          ← easy=0, medium=1, hard=2
    [6] session_progress          ← passed in via skill_profile["session_progress"]
                                    (defaults to 0.0 if not present)
    [7] timing_signal             ← min(avg_time_sec / 120, 1)
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np
import xgboost as xgb

from app.db import get_connection, put_connection

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE       = Path(__file__).resolve().parent   # app/test_engine/
MODEL_PATH  = _HERE / "adaptive_model.ubj"
VOCAB_PATH  = _HERE / "topic_vocab.json"

# ── Encoding maps (must match train_model.py exactly) ────────────────────────
_DOMAIN_MAP = {"aptitude": 0, "technical": 1}
_DIFF_MAP   = {"easy": 0, "medium": 1, "hard": 2}
_MAX_TIME   = 120.0
_TOTAL_Q    = 25

FEATURE_COLS = [
    "overall_performance",
    "topic_performance",
    "behavioral_summary_score",
    "domain_id",
    "topic_id",
    "difficulty_level",
    "session_progress",
    "timing_signal",
]


# ── Lazy-load model and vocab once ────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_model() -> xgb.Booster:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Adaptive model not found at {MODEL_PATH}. "
            "Run 'python test/train_model.py' to train and save it."
        )
    booster = xgb.Booster()
    booster.load_model(str(MODEL_PATH))
    logger.info("Adaptive model loaded from %s", MODEL_PATH)
    return booster


@lru_cache(maxsize=1)
def _load_vocab() -> dict:
    if not VOCAB_PATH.exists():
        return {}
    with open(VOCAB_PATH) as f:
        return json.load(f)


def _encode_topic(topic_str: str, vocab: dict) -> float:
    """Return the integer topic ID, falling back to 0 for unknown topics."""
    t = topic_str.strip().lower()
    if t in vocab:
        return float(vocab[t])
    # Fuzzy match — useful when DB topic names differ slightly
    for key, val in vocab.items():
        if key in t or t in key:
            return float(val)
    return 0.0


def _fetch_question_meta(question_ids: List[int]) -> dict:
    """
    Fetch domain, topic, difficulty for each question from the DB.
    Returns {question_id: {domain, topic, difficulty}}
    """
    if not question_ids:
        return {}
    conn = get_connection()
    cur  = conn.cursor()
    try:
        placeholders = ",".join(["%s"] * len(question_ids))
        cur.execute(
            f"SELECT id, domain, topic, difficulty FROM main_questions WHERE id IN ({placeholders})",
            question_ids,
        )
        return {
            row[0]: {"domain": row[1], "topic": row[2], "difficulty": row[3]}
            for row in cur.fetchall()
        }
    finally:
        cur.close()
        put_connection(conn)


# ── Public interface ──────────────────────────────────────────────────────────
def predict_success_probabilities(
    user_id: str,
    question_ids: List[int],
    skill_profile: dict,
    *,
    session_progress: float = 0.0,
) -> dict[int, float]:
    """
    Predict P(correct) for one or more candidate questions for a given user.

    Args:
        user_id          : Supabase auth UUID (currently unused; reserved for
                           future per-user model sharding).
        question_ids     : List of candidate question IDs to score.
                           Can be a single-element list or hundreds — all handled
                           in one vectorised XGBoost batch call.
        skill_profile    : The user's current main_user_skill record, containing:
                             - overall_accuracy   (float, 0..1)
                             - avg_time_sec       (float, seconds)
                             - topic_accuracy     (dict str->float, 0..1)
                             - tests_completed    (int)
        session_progress : Fraction of the current session already answered
                           (0.0 at start, 1.0 at end). Defaults to 0.0.

    Returns:
        dict[int, float] mapping each question_id -> P(correct) in [0.0, 1.0].
        Questions not found in the DB are silently omitted.
    """
    if not question_ids:
        return {}

    # ── Load model + vocab ────────────────────────────────────────────────────
    try:
        model = _load_model()
        vocab = _load_vocab()
    except FileNotFoundError:
        # Model not yet trained — fall back to neutral probability so the
        # adaptive generator can still select questions
        logger.warning("Adaptive model not found — returning neutral 0.60 for all questions")
        return {qid: 0.60 for qid in question_ids}

    # ── Fetch question metadata from DB ───────────────────────────────────────
    meta = _fetch_question_meta(list(question_ids))

    # ── Build feature matrix ─────────────────────────────────────────────────
    overall_acc   = float(skill_profile.get("overall_accuracy", 0.5))
    avg_time      = float(skill_profile.get("avg_time_sec", 30.0))
    topic_acc     = skill_profile.get("topic_accuracy") or {}

    timing_signal       = min(avg_time / _MAX_TIME, 1.0)
    behavioral_score    = 1.0 - timing_signal

    ordered_ids = []   # to preserve order for mapping output
    rows        = []

    for qid in question_ids:
        if qid not in meta:
            continue
        q = meta[qid]

        topic_str    = q["topic"].strip().lower()
        domain_id    = float(_DOMAIN_MAP.get(q["domain"].strip().lower(), 0))
        topic_id     = _encode_topic(topic_str, vocab)
        difficulty   = float(_DIFF_MAP.get(q["difficulty"].strip().lower(), 1))
        topic_perf   = float(topic_acc.get(topic_str, overall_acc))

        rows.append([
            overall_acc,        # overall_performance
            topic_perf,         # topic_performance
            behavioral_score,   # behavioral_summary_score
            domain_id,          # domain_id
            topic_id,           # topic_id
            difficulty,         # difficulty_level
            session_progress,   # session_progress
            timing_signal,      # timing_signal
        ])
        ordered_ids.append(qid)

    if not rows:
        return {}

    X       = np.array(rows, dtype=np.float32)
    dmatrix = xgb.DMatrix(X, feature_names=FEATURE_COLS)
    probs   = model.predict(dmatrix)   # already P(correct) — model uses binary:logistic

    return {qid: float(p) for qid, p in zip(ordered_ids, probs)}
