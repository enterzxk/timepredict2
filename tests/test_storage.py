from timepredict_agent.models import Paper, PaperSummary
from timepredict_agent.storage import PaperStore, decode_summary
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest


class StorageTest(unittest.TestCase):
    def test_store_upserts_and_reads_paper(self):
        with TemporaryDirectory() as temp_dir:
            store = PaperStore(Path(temp_dir) / "papers.sqlite3")
            paper = Paper(
                arxiv_id="2501.00002",
                title="Time Series Forecasting",
                abstract="A paper about time series forecasting.",
                authors=["A. Researcher"],
                published="2025-01-01T00:00:00Z",
                updated="2025-01-01T00:00:00Z",
                entry_url="https://arxiv.org/abs/2501.00002",
                pdf_url="https://arxiv.org/pdf/2501.00002",
                categories=["cs.LG"],
            )
            summary = PaperSummary(
                short_summary="A short summary.",
                key_points=["A key point."],
                method_tags=["Transformer"],
                relevance="Highly relevant.",
                reading_priority="high",
            )

            self.assertTrue(store.upsert_paper(paper, summary))
            row = store.find_paper("2501.00002")

            self.assertIsNotNone(row)
            self.assertEqual(row["title"], "Time Series Forecasting")
            self.assertEqual(decode_summary(row).reading_priority, "high")
            store.close()

    def test_find_paper_by_title_or_url_handles_upload_suffix(self):
        with TemporaryDirectory() as temp_dir:
            store = PaperStore(Path(temp_dir) / "papers.sqlite3")
            paper = Paper(
                arxiv_id="paper-1",
                title="Business Process Remaining Time Prediction Based on Incremental Event Logs 在线(1)",
                abstract="Remaining time prediction for process mining.",
                authors=["A. Researcher"],
                published="2025-01-01T00:00:00Z",
                updated="2025-01-01T00:00:00Z",
                entry_url="https://example.com/paper",
                pdf_url="",
                categories=[],
            )
            summary = PaperSummary(
                short_summary="Summary",
                key_points=["Point"],
                method_tags=["Process mining"],
                relevance="Relevant",
                reading_priority="high",
            )
            store.upsert_paper(paper, summary)

            by_title = store.find_paper_by_title_or_url(
                title="Business Process Remaining Time Prediction Based on Incremental Event Logs"
            )
            by_url = store.find_paper_by_title_or_url(url="https://example.com/paper")

            self.assertEqual(by_title["arxiv_id"], "paper-1")
            self.assertEqual(by_url["arxiv_id"], "paper-1")
            store.close()


if __name__ == "__main__":
    unittest.main()
