from timepredict_agent.models import Paper
from timepredict_agent.summarizer import ExtractiveSummarizer
import unittest


class SummarizerTest(unittest.TestCase):
    def test_summarizer_prioritizes_forecasting_papers(self):
        paper = Paper(
            arxiv_id="2501.00001",
            title="A Transformer Foundation Model for Time Series Forecasting",
            abstract=(
                "We introduce a transformer foundation model for time series forecasting. "
                "The method improves long-term multivariate prediction across benchmark datasets. "
                "Experiments show strong probabilistic forecasting performance."
            ),
            authors=["A. Researcher"],
            published="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
            entry_url="https://arxiv.org/abs/2501.00001",
            pdf_url="https://arxiv.org/pdf/2501.00001",
            categories=["cs.LG"],
        )

        summary = ExtractiveSummarizer().summarize(paper)

        self.assertEqual(summary.reading_priority, "high")
        self.assertIn("Transformer", summary.method_tags)
        self.assertIn("Foundation model", summary.method_tags)
        self.assertTrue(summary.key_points)

    def test_summarizer_recognizes_process_monitoring_terms(self):
        paper = Paper(
            arxiv_id="x",
            title="Predictive Process Monitoring for Remaining Time Prediction",
            abstract=(
                "Predictive process monitoring uses process mining over an incremental event log. "
                "We introduce a model for remaining time prediction and next event prediction."
            ),
            authors=[],
            published="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
            entry_url="",
            pdf_url="",
        )

        summary = ExtractiveSummarizer().summarize(paper)

        self.assertIn("Predictive process monitoring", summary.method_tags)
        self.assertIn("Remaining time prediction", summary.method_tags)
        self.assertIn("流程挖掘", summary.deep_summary)


if __name__ == "__main__":
    unittest.main()
