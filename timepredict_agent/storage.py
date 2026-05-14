from __future__ import annotations

from pathlib import Path
import json
import sqlite3

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


def _merge_tags(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for tag in group:
            if tag and tag not in seen:
                seen.add(tag)
                result.append(tag)
    return result
