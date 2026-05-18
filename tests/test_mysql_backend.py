from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from timepredict_agent.config import AgentConfig, load_config
from timepredict_agent.models import Paper, PaperSummary
from timepredict_agent.storage import PaperStore, create_paper_store, migrate_sqlite_to_mysql


class FakeDestinationStore:
    def __init__(self) -> None:
        self.replaced: dict[str, list[dict]] = {}
        self.closed = False

    def replace_rows(self, table: str, rows: list[dict]) -> None:
        self.replaced[table] = rows

    def close(self) -> None:
        self.closed = True


class MySQLBackendTest(unittest.TestCase):
    def test_config_reads_mysql_backend(self):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "timepredict-agent.toml"
            config_path.write_text(
                """
[agent]
database_backend = "mysql"
database_url = "mysql://timepredict:secret@127.0.0.1:3306/timepredict"
database_path = "data/papers.sqlite3"
report_dir = "reports"
pdf_dir = "data/pdfs"
""",
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.database_backend, "mysql")
            self.assertEqual(
                config.database_url,
                "mysql://timepredict:secret@127.0.0.1:3306/timepredict",
            )

    def test_create_paper_store_uses_mysql_when_configured(self):
        config = AgentConfig(
            database_backend="mysql",
            database_url="mysql://timepredict:secret@127.0.0.1:3306/timepredict",
        )
        sentinel_store = object()

        with patch.object(PaperStore, "from_mysql", return_value=sentinel_store) as from_mysql:
            store = create_paper_store(config)

        self.assertIs(store, sentinel_store)
        from_mysql.assert_called_once_with("mysql://timepredict:secret@127.0.0.1:3306/timepredict")

    def test_migrate_sqlite_to_mysql_copies_core_tables(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "papers.sqlite3"
            source = PaperStore(sqlite_path)
            source.upsert_paper(
                Paper(
                    arxiv_id="paper-1",
                    title="Migration Paper",
                    abstract="Migration test abstract.",
                    authors=["A. Researcher"],
                    published="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                    entry_url="https://example.com/paper-1",
                    pdf_url="https://example.com/paper-1.pdf",
                    categories=["cs.LG"],
                ),
                PaperSummary(
                    short_summary="Summary",
                    key_points=["Point"],
                    method_tags=["Transformer"],
                    relevance="Relevant",
                    reading_priority="high",
                ),
            )
            session = source.create_agent_session("paper-1", "Migration chat")
            turn = source.add_agent_turn(
                session_id=session["id"],
                paper_id="paper-1",
                question="What is the method?",
                answer="A concise answer.",
                plan=[{"type": "read_context"}],
                tool_calls=[{"tool": "paper_context"}],
                reflection={"score": 0.9},
                memory_used=[],
            )
            run = source.create_agent_task_run(session["id"], "paper-1", [{"type": "read_context"}])
            source.update_agent_task_run(run["id"], "completed", [{"type": "read_context"}], turn["id"])
            source.add_agent_feedback(turn["id"], session["id"], "bad", "too_generic", "Need experiments.")
            source.close()

            destination = FakeDestinationStore()
            result = migrate_sqlite_to_mysql(
                sqlite_path,
                "mysql://timepredict:secret@127.0.0.1:3306/timepredict",
                target_store=destination,
            )

        self.assertEqual(result["backend"], "mysql")
        self.assertEqual(result["tables"]["papers"], 1)
        self.assertEqual(result["tables"]["agent_sessions"], 1)
        self.assertEqual(result["tables"]["agent_turns"], 1)
        self.assertEqual(result["tables"]["agent_feedback"], 1)
        self.assertEqual(result["tables"]["agent_memory"], 1)
        self.assertEqual(result["tables"]["agent_task_runs"], 1)
        self.assertEqual(destination.replaced["papers"][0]["title"], "Migration Paper")
        self.assertTrue(destination.closed)


if __name__ == "__main__":
    unittest.main()
