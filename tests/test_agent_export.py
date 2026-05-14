from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from timepredict_agent.agent import PaperAgent
from timepredict_agent.config import AgentConfig
from timepredict_agent.models import Paper, PaperSummary


class AgentExportTest(unittest.TestCase):
    def test_export_markdown_writes_report(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(database_path=root / "papers.sqlite3", report_dir=root / "reports")
            )
            paper = Paper(
                arxiv_id="2501.00004",
                title="A Useful Forecasting Paper",
                abstract="Time series forecasting abstract.",
                authors=["A. Researcher"],
                published="2025-01-01T00:00:00Z",
                updated="2025-01-01T00:00:00Z",
                entry_url="https://arxiv.org/abs/2501.00004",
                pdf_url="https://arxiv.org/pdf/2501.00004",
                categories=["cs.LG"],
            )
            summary = PaperSummary(
                short_summary="This is useful.",
                key_points=["It forecasts time series."],
                method_tags=["Transformer"],
                relevance="Highly relevant.",
                reading_priority="high",
            )
            agent.store.upsert_paper(paper, summary)

            report = agent.export_markdown(root / "reports" / "papers.md")

            self.assertTrue(report.exists())
            self.assertIn("A Useful Forecasting Paper", report.read_text(encoding="utf-8"))
            agent.close()

    def test_generate_literature_review_writes_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(database_path=root / "papers.sqlite3", report_dir=root / "reports")
            )
            for index in range(2):
                paper = Paper(
                    arxiv_id=f"paper-{index}",
                    title=f"Event Sequence Prediction Paper {index}",
                    abstract="Predictive process monitoring and remaining time prediction.",
                    authors=["A. Researcher"],
                    published="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                    entry_url=f"https://example.com/{index}",
                    pdf_url="",
                    categories=[],
                )
                summary = PaperSummary(
                    short_summary="关注事件序列预测。",
                    key_points=["用于预测下一事件。"],
                    method_tags=["Predictive process monitoring"],
                    relevance="和流程预测高度相关。",
                    reading_priority="high",
                )
                agent.store.upsert_paper(paper, summary)

            result = agent.generate_literature_review(
                ["paper-0", "paper-1"],
                topic="事件序列预测",
                prefer_llm=False,
            )

            self.assertFalse(result["used_llm"])
            self.assertIn("事件序列预测文献综述草稿", result["markdown"])
            self.assertTrue((root / "reports" / "literature_review.md").exists())
            agent.close()

    def test_add_manual_paper_marks_read_paper(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(database_path=root / "papers.sqlite3", report_dir=root / "reports")
            )

            row = agent.add_manual_paper(
                {
                    "title": "Manual Event Sequence Prediction Paper",
                    "authors": "A. Researcher, B. Reader",
                    "year": "2024",
                    "abstract": "This paper studies event sequence prediction for process mining.",
                    "entry_url": "https://example.com/manual-paper",
                    "tags": "事件序列预测,已读",
                }
            )

            self.assertEqual(row["source"], "manual")
            self.assertEqual(row["year"], 2024)
            self.assertIn("manual:", row["arxiv_id"])
            self.assertIn("已读", row["tags_json"])
            agent.close()


if __name__ == "__main__":
    unittest.main()
