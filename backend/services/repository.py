"""SQLite repository: session-scoped learners, pending questions and anonymized misconceptions.

All SQL is parameterized. Pending questions hold answer keys and Twin predictions server-side.
"""

import sqlite3
import threading
from pathlib import Path

from pydantic import BaseModel

from backend.core.models import Learner, Question

SCHEMA = """
CREATE TABLE IF NOT EXISTS learners (
    session_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_questions (
    question_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS misconceptions (
    learner_key TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pending_session ON pending_questions(session_id);
"""


class TwinPrediction(BaseModel):
    predicted_answer: str
    predicted_correct: bool
    reasoning: str


class PendingQuestion(BaseModel):
    question: Question
    prediction: TwinPrediction
    confidence_before: float


class Repository:
    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def get_learner(self, session_id: str) -> Learner | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM learners WHERE session_id = ?", (session_id,)
            ).fetchone()
        return Learner.model_validate_json(row[0]) if row else None

    def save_learner(self, session_id: str, learner: Learner) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO learners (session_id, data) VALUES (?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET data = excluded.data",
                (session_id, learner.model_dump_json()),
            )

    def put_question(self, session_id: str, pending: PendingQuestion) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO pending_questions (question_id, session_id, data) "
                "VALUES (?, ?, ?)",
                (pending.question.id, session_id, pending.model_dump_json()),
            )

    def pop_question(self, session_id: str, question_id: str) -> PendingQuestion | None:
        """Fetch and delete a pending question; returns None if it is not this session's."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT data FROM pending_questions WHERE question_id = ? AND session_id = ?",
                (question_id, session_id),
            ).fetchone()
            if row:
                self._conn.execute(
                    "DELETE FROM pending_questions WHERE question_id = ?", (question_id,)
                )
        return PendingQuestion.model_validate_json(row[0]) if row else None

    def add_misconception(self, learner_key: str, skill_id: str, text: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO misconceptions (learner_key, skill_id, text) VALUES (?, ?, ?)",
                (learner_key, skill_id, text),
            )

    def misconception_records(self) -> list[tuple[str, str, str]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT learner_key, skill_id, text FROM misconceptions"
            ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
