from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import uuid

from .models import Paper, PaperSummary


class PaperStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.connection.close()

    def upsert_paper(self, paper: Paper, summary: PaperSummary) -> bool:
        before = self.connection.total_changes
        self.connection.execute(
            """
            INSERT INTO papers (
                arxiv_id, title, abstract, authors_json, published, updated,
                entry_url, pdf_url, categories_json, summary_json, source, source_id,
                doi, venue, year, citation_count, reference_count, external_ids_json,
                fields_of_study_json, tags_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
                title = excluded.title,
                abstract = excluded.abstract,
                authors_json = excluded.authors_json,
                published = excluded.published,
                updated = excluded.updated,
                entry_url = excluded.entry_url,
                pdf_url = excluded.pdf_url,
                categories_json = excluded.categories_json,
                summary_json = excluded.summary_json,
                source = excluded.source,
                source_id = excluded.source_id,
                doi = excluded.doi,
                venue = excluded.venue,
                year = excluded.year,
                citation_count = COALESCE(excluded.citation_count, citation_count),
                reference_count = COALESCE(excluded.reference_count, reference_count),
                external_ids_json = excluded.external_ids_json,
                fields_of_study_json = excluded.fields_of_study_json,
                tags_json = excluded.tags_json
            """,
            (
                paper.arxiv_id,
                paper.title,
                paper.abstract,
                json.dumps(paper.authors, ensure_ascii=False),
                paper.published,
                paper.updated,
                paper.entry_url,
                paper.pdf_url,
                json.dumps(paper.categories, ensure_ascii=False),
                json.dumps(summary.__dict__, ensure_ascii=False),
                paper.source,
                paper.source_id or paper.arxiv_id,
                paper.doi,
                paper.venue,
                paper.year,
                paper.citation_count,
                paper.reference_count,
                json.dumps(paper.external_ids, ensure_ascii=False),
                json.dumps(paper.fields_of_study, ensure_ascii=False),
                json.dumps(_merge_tags(summary.method_tags, summary.topic_tags), ensure_ascii=False),
            ),
        )
        self.connection.commit()
        return self.connection.total_changes > before

    def update_download_path(self, paper_id: str, path: str) -> None:
        self.connection.execute(
            "UPDATE papers SET local_pdf_path = ? WHERE arxiv_id = ?", (path, paper_id)
        )
        self.connection.commit()

    def update_citation_data(
        self,
        paper_id: str,
        citation_count: int,
        reference_count: int,
        influential_citation_count: int,
        citations: list[dict],
        references: list[dict],
    ) -> None:
        self.connection.execute(
            """
            UPDATE papers
            SET citation_count = ?,
                reference_count = ?,
                influential_citation_count = ?,
                citations_json = ?,
                references_json = ?
            WHERE arxiv_id = ?
            """,
            (
                citation_count,
                reference_count,
                influential_citation_count,
                json.dumps(citations, ensure_ascii=False),
                json.dumps(references, ensure_ascii=False),
                paper_id,
            ),
        )
        self.connection.commit()

    def update_related_papers(self, paper_id: str, related: list[dict]) -> None:
        self.connection.execute(
            "UPDATE papers SET related_json = ? WHERE arxiv_id = ?",
            (json.dumps(related, ensure_ascii=False), paper_id),
        )
        self.connection.commit()

    def update_pdf_text(self, paper_id: str, pdf_text: str) -> None:
        self.connection.execute(
            "UPDATE papers SET pdf_text = ? WHERE arxiv_id = ?",
            (pdf_text, paper_id),
        )
        self.connection.commit()

    def update_summary(self, paper_id: str, summary: PaperSummary) -> None:
        self.connection.execute(
            """
            UPDATE papers
            SET summary_json = ?,
                tags_json = ?
            WHERE arxiv_id = ?
            """,
            (
                json.dumps(summary.__dict__, ensure_ascii=False),
                json.dumps(_merge_tags(summary.method_tags, summary.topic_tags), ensure_ascii=False),
                paper_id,
            ),
        )
        self.connection.commit()

    def list_papers(self, limit: int = 20) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            "SELECT * FROM papers ORDER BY published DESC LIMIT ?", (limit,)
        )
        return list(cursor.fetchall())

    def find_paper(self, arxiv_id: str) -> sqlite3.Row | None:
        cursor = self.connection.execute("SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,))
        return cursor.fetchone()

    def search_papers(self, keyword: str, limit: int = 20) -> list[sqlite3.Row]:
        like = f"%{keyword}%"
        cursor = self.connection.execute(
            """
            SELECT * FROM papers
            WHERE title LIKE ? OR abstract LIKE ? OR summary_json LIKE ? OR tags_json LIKE ?
            ORDER BY published DESC
            LIMIT ?
            """,
            (like, like, like, like, limit),
        )
        return list(cursor.fetchall())

    def find_paper_by_title_or_url(self, title: str = "", url: str = "") -> sqlite3.Row | None:
        normalized_title = _normalize_title(title)
        if url:
            cursor = self.connection.execute(
                "SELECT * FROM papers WHERE entry_url = ? OR pdf_url = ? LIMIT 1",
                (url, url),
            )
            row = cursor.fetchone()
            if row is not None:
                return row
        if not normalized_title:
            return None
        for row in self.list_papers(500):
            if _normalize_title(row["title"]) == normalized_title:
                return row
        words = [word for word in normalized_title.split() if len(word) > 3]
        if not words:
            return None
        best_row = None
        best_score = 0
        word_set = set(words)
        for row in self.list_papers(500):
            candidate = _normalize_title(row["title"])
            candidate_words = set(word for word in candidate.split() if len(word) > 3)
            if normalized_title in candidate or candidate in normalized_title:
                return row
            score = len(word_set & candidate_words)
            if score > best_score:
                best_score = score
                best_row = row
        threshold = min(6, max(3, int(len(words) * 0.72)))
        return best_row if best_score >= threshold else None

    def create_agent_session(self, paper_id: str, title: str = "") -> dict:
        now = _now_iso()
        session_id = _new_id("session")
        self.connection.execute(
            """
            INSERT INTO agent_sessions (id, paper_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, paper_id, title or "新的论文对话", now, now),
        )
        self.connection.commit()
        return self.find_agent_session(session_id) or {
            "id": session_id,
            "paper_id": paper_id,
            "title": title or "新的论文对话",
            "created_at": now,
            "updated_at": now,
            "turn_count": 0,
            "turns": [],
        }

    def find_agent_session(self, session_id: str) -> dict | None:
        cursor = self.connection.execute(
            "SELECT * FROM agent_sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._agent_session_to_dict(row, include_turns=True)

    def list_agent_sessions(self, paper_id: str | None = None, limit: int = 60) -> list[dict]:
        if paper_id:
            cursor = self.connection.execute(
                """
                SELECT * FROM agent_sessions
                WHERE paper_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (paper_id, limit),
            )
        else:
            cursor = self.connection.execute(
                """
                SELECT * FROM agent_sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [self._agent_session_to_dict(row, include_turns=True) for row in cursor.fetchall()]

    def touch_agent_session(self, session_id: str, title: str | None = None) -> None:
        now = _now_iso()
        if title:
            self.connection.execute(
                "UPDATE agent_sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
        else:
            self.connection.execute(
                "UPDATE agent_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        self.connection.commit()

    def add_agent_turn(
        self,
        session_id: str,
        paper_id: str,
        question: str,
        answer: str,
        plan: list[dict],
        tool_calls: list[dict],
        reflection: dict,
        memory_used: list[dict],
    ) -> dict:
        now = _now_iso()
        turn_id = _new_id("turn")
        self.connection.execute(
            """
            INSERT INTO agent_turns (
                id, session_id, paper_id, question, answer, plan_json,
                tool_calls_json, reflection_json, memory_used_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn_id,
                session_id,
                paper_id,
                question,
                answer,
                _json_dumps(plan),
                _json_dumps(tool_calls),
                _json_dumps(reflection),
                _json_dumps(memory_used),
                now,
            ),
        )
        self.connection.execute(
            "UPDATE agent_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self.connection.commit()
        return self.find_agent_turn(turn_id) or {
            "id": turn_id,
            "session_id": session_id,
            "paper_id": paper_id,
            "question": question,
            "answer": answer,
            "plan": plan,
            "tool_calls": tool_calls,
            "reflection": reflection,
            "memory_used": memory_used,
            "created_at": now,
        }

    def find_agent_turn(self, turn_id: str) -> dict | None:
        cursor = self.connection.execute("SELECT * FROM agent_turns WHERE id = ?", (turn_id,))
        row = cursor.fetchone()
        return self._agent_turn_to_dict(row) if row is not None else None

    def list_agent_turns(self, session_id: str, limit: int = 50) -> list[dict]:
        cursor = self.connection.execute(
            """
            SELECT * FROM agent_turns
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (session_id, limit),
        )
        return [self._agent_turn_to_dict(row) for row in cursor.fetchall()]

    def create_agent_task_run(
        self,
        session_id: str,
        paper_id: str,
        steps: list[dict],
        status: str = "running",
    ) -> dict:
        now = _now_iso()
        run_id = _new_id("run")
        self.connection.execute(
            """
            INSERT INTO agent_task_runs (
                id, session_id, paper_id, status, steps_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, session_id, paper_id, status, _json_dumps(steps), now, now),
        )
        self.connection.commit()
        return {
            "id": run_id,
            "session_id": session_id,
            "paper_id": paper_id,
            "status": status,
            "steps": steps,
            "created_at": now,
            "updated_at": now,
        }

    def update_agent_task_run(
        self,
        run_id: str,
        status: str,
        steps: list[dict],
        turn_id: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            UPDATE agent_task_runs
            SET status = ?, steps_json = ?, turn_id = COALESCE(?, turn_id), updated_at = ?
            WHERE id = ?
            """,
            (status, _json_dumps(steps), turn_id, _now_iso(), run_id),
        )
        self.connection.commit()

    def add_agent_feedback(
        self,
        turn_id: str,
        session_id: str,
        rating: str,
        category: str = "",
        note: str = "",
    ) -> dict:
        now = _now_iso()
        feedback_id = _new_id("feedback")
        self.connection.execute(
            """
            INSERT INTO agent_feedback (id, turn_id, session_id, rating, category, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (feedback_id, turn_id, session_id, rating, category, note, now),
        )
        if category or note:
            self.upsert_agent_memory(
                kind="feedback",
                key=category or rating,
                value={"rating": rating, "category": category, "note": note},
                weight_delta=1,
                commit=False,
            )
        self.connection.commit()
        return {
            "id": feedback_id,
            "turn_id": turn_id,
            "session_id": session_id,
            "rating": rating,
            "category": category,
            "note": note,
            "created_at": now,
        }

    def upsert_agent_memory(
        self,
        kind: str,
        key: str,
        value: dict,
        weight_delta: int = 1,
        commit: bool = True,
    ) -> dict:
        now = _now_iso()
        memory_id = _new_id("memory")
        self.connection.execute(
            """
            INSERT INTO agent_memory (id, kind, key, value_json, weight, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(kind, key) DO UPDATE SET
                value_json = excluded.value_json,
                weight = agent_memory.weight + excluded.weight,
                updated_at = excluded.updated_at
            """,
            (memory_id, kind, key, _json_dumps(value), weight_delta, now, now),
        )
        if commit:
            self.connection.commit()
        cursor = self.connection.execute(
            "SELECT * FROM agent_memory WHERE kind = ? AND key = ?",
            (kind, key),
        )
        row = cursor.fetchone()
        return self._agent_memory_to_dict(row) if row is not None else {
            "id": memory_id,
            "kind": kind,
            "key": key,
            "value": value,
            "weight": weight_delta,
            "created_at": now,
            "updated_at": now,
        }

    def list_agent_memory(self, kind: str | None = None, limit: int = 20) -> list[dict]:
        if kind:
            cursor = self.connection.execute(
                """
                SELECT * FROM agent_memory
                WHERE kind = ?
                ORDER BY weight DESC, updated_at DESC
                LIMIT ?
                """,
                (kind, limit),
            )
        else:
            cursor = self.connection.execute(
                """
                SELECT * FROM agent_memory
                ORDER BY weight DESC, updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [self._agent_memory_to_dict(row) for row in cursor.fetchall()]

    def _agent_session_to_dict(self, row: sqlite3.Row, include_turns: bool = False) -> dict:
        turns = self.list_agent_turns(row["id"]) if include_turns else []
        return {
            "id": row["id"],
            "paper_id": row["paper_id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "turn_count": len(turns),
            "turns": turns,
        }

    def _agent_turn_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "paper_id": row["paper_id"],
            "question": row["question"],
            "answer": row["answer"],
            "plan": _json_loads(row["plan_json"], []),
            "tool_calls": _json_loads(row["tool_calls_json"], []),
            "reflection": _json_loads(row["reflection_json"], {}),
            "memory_used": _json_loads(row["memory_used_json"], []),
            "created_at": row["created_at"],
        }

    def _agent_memory_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "key": row["key"],
            "value": _json_loads(row["value_json"], {}),
            "weight": row["weight"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _init_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                published TEXT NOT NULL,
                updated TEXT NOT NULL,
                entry_url TEXT NOT NULL,
                pdf_url TEXT NOT NULL,
                categories_json TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(papers)").fetchall()
        }
        migrations = {
            "source": "TEXT NOT NULL DEFAULT 'arxiv'",
            "source_id": "TEXT NOT NULL DEFAULT ''",
            "doi": "TEXT NOT NULL DEFAULT ''",
            "venue": "TEXT NOT NULL DEFAULT ''",
            "year": "INTEGER",
            "citation_count": "INTEGER",
            "reference_count": "INTEGER",
            "influential_citation_count": "INTEGER",
            "external_ids_json": "TEXT NOT NULL DEFAULT '{}'",
            "fields_of_study_json": "TEXT NOT NULL DEFAULT '[]'",
            "tags_json": "TEXT NOT NULL DEFAULT '[]'",
            "local_pdf_path": "TEXT NOT NULL DEFAULT ''",
            "citations_json": "TEXT NOT NULL DEFAULT '[]'",
            "references_json": "TEXT NOT NULL DEFAULT '[]'",
            "related_json": "TEXT NOT NULL DEFAULT '[]'",
            "pdf_text": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in columns:
                self.connection.execute(f"ALTER TABLE papers ADD COLUMN {column} {definition}")
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published DESC)"
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source)")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_sessions (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_sessions_updated ON agent_sessions(updated_at DESC)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_sessions_paper ON agent_sessions(paper_id, updated_at DESC)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_turns (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                plan_json TEXT NOT NULL DEFAULT '[]',
                tool_calls_json TEXT NOT NULL DEFAULT '[]',
                reflection_json TEXT NOT NULL DEFAULT '{}',
                memory_used_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_turns_session ON agent_turns(session_id, created_at)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                weight INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_memory_kind_key ON agent_memory(kind, key)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_feedback (
                id TEXT PRIMARY KEY,
                turn_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                rating TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_task_runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                turn_id TEXT,
                paper_id TEXT NOT NULL,
                status TEXT NOT NULL,
                steps_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_task_runs_session ON agent_task_runs(session_id, updated_at DESC)"
        )
        self.connection.commit()


def decode_summary(row: sqlite3.Row) -> PaperSummary:
    raw = json.loads(row["summary_json"])
    return PaperSummary(**raw)


def decode_json_field(row: sqlite3.Row, field: str) -> list[str]:
    return list(json.loads(row[field]))


def decode_json_object(row: sqlite3.Row, field: str, fallback):
    try:
        return json.loads(row[field] or json.dumps(fallback))
    except (KeyError, TypeError, json.JSONDecodeError):
        return fallback


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str, fallback):
    try:
        return json.loads(value or json.dumps(fallback))
    except (TypeError, json.JSONDecodeError):
        return fallback


def _merge_tags(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for tag in group:
            if tag and tag not in seen:
                seen.add(tag)
                result.append(tag)
    return result


def _normalize_title(value: str) -> str:
    import re

    text = str(value or "").lower()
    text = re.sub(r"在线\s*\(?\d*\)?", " ", text)
    text = re.sub(r"\bpdf\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
