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

    def test_summarizer_explains_affordance_reasoning_without_time_series_template(self):
        paper = Paper(
            arxiv_id="s2:2508.06206",
            title="Affordance-R1: Reinforcement Learning for Generalizable Affordance Reasoning in Multimodal Large Language Model",
            abstract=(
                "Affordance reasoning enables robots and embodied agents to infer possible actions from visual scenes. "
                "Existing multimodal large language models struggle with fine-grained affordance grounding and open-world generalization. "
                "To address these challenges, we propose Affordance-R1, the first unified affordance grounding framework that integrates cognitive Chain-of-Thought guided Group Relative Policy Optimization (GRPO) within a reinforcement learning paradigm. "
                "Comprehensive experiments on ReasonAff demonstrate that our model outperforms well-established methods and exhibits open-world generalization."
            ),
            authors=["Hanqing Wang"],
            published="2025-08-08T00:00:00Z",
            updated="2025-08-08T00:00:00Z",
            entry_url="https://example.com/affordance-r1",
            pdf_url="",
            categories=["cs.AI", "cs.CV"],
            venue="AAAI",
            year=2025,
            citation_count=13,
            fields_of_study=["Computer Science", "Artificial Intelligence"],
        )

        summary = ExtractiveSummarizer().summarize(paper)
        combined_text = " ".join(
            [
                summary.short_summary,
                summary.deep_summary,
                summary.method,
                " ".join(summary.key_points),
            ]
        )

        self.assertNotIn("时间序列", combined_text)
        self.assertNotIn("预测数值", combined_text)
        self.assertIn("可供性", combined_text)
        self.assertIn("多模态", combined_text)
        self.assertIn("Reinforcement learning", summary.method_tags)
        self.assertIn("Multimodal LLM", summary.method_tags)
        self.assertIn("GRPO", summary.method_tags)
        self.assertTrue(summary.innovation_points)
        self.assertIn("ReasonAff", summary.datasets_used)
        self.assertGreaterEqual(len(summary.key_points), 8)
        self.assertGreaterEqual(len(summary.deep_summary), 260)
        self.assertGreaterEqual(len(summary.method), 220)
        self.assertGreaterEqual(len(summary.experiments), 180)
        self.assertTrue(summary.method_comparison)
        self.assertTrue(summary.future_directions)

    def test_summarizer_uses_full_text_for_method_and_experiment_details(self):
        paper = Paper(
            arxiv_id="process-fulltext",
            title="Business Process Remaining Time Prediction Based on Incremental Event Logs",
            abstract="This paper studies remaining time prediction for business process instances.",
            authors=["A. Researcher"],
            published="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
            entry_url="",
            pdf_url="",
        )
        full_text = """
        Abstract This work predicts remaining time for running business process cases from incremental event logs.
        1 Introduction The goal is to support process monitoring before a case completes.
        Method The proposed framework first converts each running case prefix into activity, timestamp and resource features.
        It then maintains an incremental event-log window, updates the training set when new traces arrive, and uses a
        remaining-time regression model to learn duration patterns from prefixes. The method compares static training,
        periodic retraining and incremental update strategies.
        Experiments The experiments use business process event logs and compare MAE, RMSE and runtime against baseline
        models including static regression and non-incremental sequence models. Results show that incremental updates
        improve robustness when new process behavior appears, while periodic full retraining costs more time.
        Conclusion The method is useful when event logs evolve over time, but it still depends on data quality and
        requires stronger validation on more public process-mining benchmarks.
        """

        summary = ExtractiveSummarizer().summarize(paper, full_text)

        self.assertIn("incremental event-log window", summary.method)
        self.assertIn("MAE", summary.experiments)
        self.assertIn("periodic full retraining", summary.experiments)
        self.assertIn("RMSE", summary.metrics_used)
        self.assertGreaterEqual(len(summary.deep_summary), 260)
        self.assertTrue(any("增量事件日志" in point or "持续更新" in point for point in summary.innovation_points))


if __name__ == "__main__":
    unittest.main()
