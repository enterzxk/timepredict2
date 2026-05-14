from timepredict_agent.web import _row_to_dict
from timepredict_agent.models import Paper, PaperSummary
from timepredict_agent.storage import PaperStore
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class WebSerializationTest(unittest.TestCase):
    def test_row_to_dict_contains_summary_and_authors(self):
        with TemporaryDirectory() as temp_dir:
            store = PaperStore(Path(temp_dir) / "papers.sqlite3")
            store.upsert_paper(
                Paper(
                    arxiv_id="2501.00005",
                    title="Web Paper",
                    abstract="A time series forecasting paper.",
                    authors=["A. Researcher"],
                    published="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                    entry_url="https://arxiv.org/abs/2501.00005",
                    pdf_url="https://arxiv.org/pdf/2501.00005",
                    categories=["cs.LG"],
                ),
                PaperSummary(
                    short_summary="Useful web summary.",
                    key_points=["Point"],
                    method_tags=["Transformer"],
                    relevance="Relevant.",
                    reading_priority="high",
                ),
            )

            row = store.find_paper("2501.00005")
            payload = _row_to_dict(row)

            self.assertEqual(payload["authors"], ["A. Researcher"])
            self.assertEqual(payload["summary"]["reading_priority"], "high")
            store.close()


if __name__ == "__main__":
    unittest.main()

