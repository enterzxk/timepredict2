from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date
import unittest

from timepredict_agent.agent import PaperAgent
from timepredict_agent.config import AgentConfig
from timepredict_agent.github_search import build_repository_query, repository_from_item
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

    def test_add_uploaded_paper_saves_pdf_and_recommends_similar(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(
                    database_path=root / "papers.sqlite3",
                    report_dir=root / "reports",
                    pdf_dir=root / "pdfs",
                )
            )
            candidate = Paper(
                arxiv_id="candidate-1",
                title="Remaining Time Prediction for Event Logs",
                abstract="This paper studies remaining time prediction and event log process mining.",
                authors=["A. Researcher"],
                published="2025-01-01T00:00:00Z",
                updated="2025-01-01T00:00:00Z",
                entry_url="https://example.com/candidate",
                pdf_url="",
                categories=[],
            )
            agent.store.upsert_paper(
                candidate,
                PaperSummary(
                    short_summary="关注剩余时间预测。",
                    key_points=["基于事件日志预测剩余时间。"],
                    method_tags=["Remaining time prediction", "Process mining"],
                    relevance="和流程预测高度相关。",
                    reading_priority="high",
                ),
            )

            result = agent.add_uploaded_paper(
                "uploaded.pdf",
                b"%PDF-1.4\nminimal test pdf",
                {
                    "title": "Uploaded Remaining Time Prediction Paper",
                    "abstract": "A study about remaining time prediction for event log process mining.",
                    "tags": "Remaining time prediction,Process mining",
                },
            )

            row = result["paper"]
            self.assertEqual(row["source"], "uploaded")
            self.assertTrue(Path(row["local_pdf_path"]).exists())
            self.assertTrue(result["related"])
            self.assertEqual(result["related"][0]["title"], "Remaining Time Prediction for Event Logs")
            agent.close()

    def test_generate_innovation_advice_uses_related_papers(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(
                    database_path=root / "papers.sqlite3",
                    report_dir=root / "reports",
                    pdf_dir=root / "pdfs",
                )
            )
            for paper_id, title in [
                ("target", "Incremental Event Log Remaining Time Prediction"),
                ("related", "Process Mining Remaining Time Prediction Benchmark"),
            ]:
                paper = Paper(
                    arxiv_id=paper_id,
                    title=title,
                    abstract="This work studies event log remaining time prediction for process mining and incremental learning.",
                    authors=["A. Researcher"],
                    published="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                    entry_url=f"https://example.com/{paper_id}",
                    pdf_url="",
                    categories=[],
                )
                agent.store.upsert_paper(
                    paper,
                    PaperSummary(
                        short_summary="关注事件日志剩余时间预测。",
                        key_points=["处理流程挖掘中的预测任务。"],
                        method_tags=["Remaining time prediction", "Process mining"],
                        relevance="和流程预测高度相关。",
                        reading_priority="high",
                    ),
                )

            result = agent.generate_innovation_advice("target", limit=8)

            self.assertTrue(result["related"])
            self.assertTrue(result["advice"])
            self.assertIn("title", result["advice"][0])
            self.assertIn("how", result["advice"][0])
            agent.close()

    def test_ask_paper_expert_answers_with_github_repositories(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(
                    database_path=root / "papers.sqlite3",
                    report_dir=root / "reports",
                    pdf_dir=root / "pdfs",
                )
            )
            agent.llm.token = ""
            try:
                paper = Paper(
                    arxiv_id="dl-paper",
                    title="Deep Residual Learning for Image Recognition",
                    abstract=(
                        "This paper introduces residual learning blocks and compares ResNet "
                        "against plain convolutional neural networks on ImageNet and COCO."
                    ),
                    authors=["A. Researcher"],
                    published="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                    entry_url="https://example.com/resnet",
                    pdf_url="",
                    categories=["cs.CV"],
                )
                summary = PaperSummary(
                    short_summary="论文提出残差学习来训练更深的卷积网络。",
                    key_points=["使用 identity shortcut 缓解深层网络退化问题。"],
                    method_tags=["ResNet", "CNN", "ImageNet"],
                    relevance="深度学习视觉方向高度相关。",
                    reading_priority="high",
                    deep_summary="论文核心是让网络学习残差函数，而不是直接拟合目标映射。",
                    method="残差块把输入通过 shortcut 与卷积层输出相加。",
                    experiments="在 ImageNet 分类和 COCO 检测上对比 plain network 与 ResNet。",
                    innovation_points=["用 identity shortcut 支持超深网络训练。"],
                    method_comparison="相比 plain CNN，残差连接降低优化难度。",
                )
                agent.store.upsert_paper(paper, summary)
                agent.github.search = lambda paper, summary, question, limit=5: [
                    {
                        "full_name": "KaimingHe/deep-residual-networks",
                        "html_url": "https://github.com/KaimingHe/deep-residual-networks",
                        "description": "ResNet implementation",
                        "language": "Lua",
                        "stars": 7600,
                        "updated_at": "2025-01-01T00:00:00Z",
                        "reason": "标题和方法标签匹配",
                    }
                ]

                result = agent.ask_paper_expert(
                    "dl-paper",
                    "这篇论文的方法怎么做？有没有 GitHub 代码可以参考？",
                    include_github=True,
                )

                self.assertFalse(result["used_llm"])
                self.assertIn("方法思想", result["answer"])
                self.assertIn("实验结果", result["answer"])
                self.assertEqual(result["github_repositories"][0]["full_name"], "KaimingHe/deep-residual-networks")
                self.assertIn("KaimingHe/deep-residual-networks", result["answer"])
            finally:
                agent.close()

    def test_ask_paper_expert_explains_requested_term_directly(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(
                    database_path=root / "papers.sqlite3",
                    report_dir=root / "reports",
                    pdf_dir=root / "pdfs",
                )
            )
            agent.llm.token = ""
            try:
                paper = Paper(
                    arxiv_id="remaining-time",
                    title="Business Process Remaining Time Prediction Based on Incremental Event Logs",
                    abstract=(
                        "The framework has LSTM-based, Transformer-based, and Auto-encoder-based "
                        "instantiations for remaining time prediction on event logs."
                    ),
                    authors=["A. Researcher"],
                    published="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                    entry_url="https://example.com/process",
                    pdf_url="",
                    categories=[],
                )
                summary = PaperSummary(
                    short_summary="论文比较 LSTM、Transformer 和 Autoencoder 三种实例化模型。",
                    key_points=["Autoencoder 是其中一种深度模型实例化。"],
                    method_tags=["LSTM", "Transformer", "Autoencoder", "Process mining"],
                    relevance="和业务流程剩余时间预测相关。",
                    reading_priority="high",
                    experiments="nine real-life event logs, prediction accuracy",
                )
                agent.store.upsert_paper(paper, summary)

                result = agent.ask_paper_expert(
                    "remaining-time",
                    "里面的autoencoder是什么意思",
                    include_github=False,
                    prefer_llm=False,
                )

                answer = result["answer"]
                self.assertIn("自编码器", answer)
                self.assertIn("编码器", answer)
                self.assertIn("解码器", answer)
                self.assertIn("在这篇论文里", answer)
                self.assertIn("LSTM", answer)
                self.assertNotIn("你的问题：里面的autoencoder是什么意思\n\n方法思想：", answer)
            finally:
                agent.close()

    def test_refresh_local_summary_preserves_structured_fields(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(database_path=root / "papers.sqlite3", report_dir=root / "reports")
            )
            paper = Paper(
                arxiv_id="affordance-r1",
                title="Affordance-R1: Reinforcement Learning for Generalizable Affordance Reasoning in Multimodal Large Language Model",
                abstract=(
                    "To address these challenges, we propose Affordance-R1, the first unified affordance grounding framework "
                    "that integrates cognitive Chain-of-Thought guided Group Relative Policy Optimization (GRPO) within a reinforcement learning paradigm. "
                    "Comprehensive experiments on ReasonAff demonstrate open-world generalization."
                ),
                authors=["A. Researcher"],
                published="2025-08-08T00:00:00Z",
                updated="2025-08-08T00:00:00Z",
                entry_url="https://example.com/affordance",
                pdf_url="",
                categories=["cs.AI"],
            )
            agent.store.upsert_paper(
                paper,
                PaperSummary(
                    short_summary="Old summary.",
                    key_points=["Old point."],
                    method_tags=["Benchmark"],
                    relevance="Old relevance.",
                    reading_priority="low",
                ),
            )

            try:
                result = agent.refresh_local_summary("affordance-r1")

                self.assertTrue(result["summary"]["innovation_points"])
                self.assertIn("ReasonAff", result["summary"]["datasets_used"])
                self.assertIn("Affordance grounding", result["summary"]["method_tags"])
            finally:
                agent.close()

    def test_daily_recommendations_prefers_quality_signals_and_uses_today_cache(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = PaperAgent(
                AgentConfig(
                    database_path=root / "papers.sqlite3",
                    report_dir=root / "reports",
                    pdf_dir=root / "pdfs",
                )
            )
            top_paper = Paper(
                arxiv_id="top-paper",
                title="Foundation Models for Multimodal Deep Learning",
                abstract="A deep learning paper about foundation models and artificial intelligence.",
                authors=["A. Researcher"],
                published="2026-05-15T00:00:00Z",
                updated="2026-05-15T00:00:00Z",
                entry_url="https://example.com/top",
                pdf_url="",
                categories=["cs.LG"],
                source="semantic_scholar",
                venue="NeurIPS",
                year=2026,
                citation_count=220,
                fields_of_study=["Computer Science"],
            )
            weak_paper = Paper(
                arxiv_id="weak-paper",
                title="A Small Survey of Generic Software Tools",
                abstract="A generic paper without artificial intelligence contribution.",
                authors=["B. Researcher"],
                published="2026-05-15T00:00:00Z",
                updated="2026-05-15T00:00:00Z",
                entry_url="https://example.com/weak",
                pdf_url="",
                categories=[],
                source="semantic_scholar",
                venue="Workshop",
                year=2026,
                citation_count=1,
            )
            try:
                agent._fetch_daily_candidates = lambda max_results, recent_days: [weak_paper, top_paper]

                first = agent.daily_recommendations(limit=2, force=True, today=date(2026, 5, 16))
                agent._fetch_daily_candidates = lambda max_results, recent_days: (_ for _ in ()).throw(
                    AssertionError("cache was not used")
                )
                second = agent.daily_recommendations(limit=2, force=False, today=date(2026, 5, 16))

                self.assertEqual(first["date"], "2026-05-16")
                self.assertEqual(first["items"][0]["paper"]["title"], "Foundation Models for Multimodal Deep Learning")
                self.assertIn("NeurIPS", first["items"][0]["quality_signals"])
                self.assertFalse(first["from_cache"])
                self.assertTrue(second["from_cache"])
                self.assertEqual(second["items"][0]["paper"]["title"], "Foundation Models for Multimodal Deep Learning")
            finally:
                agent.close()

    def test_github_repository_search_query_and_parser(self):
        paper = Paper(
            arxiv_id="resnet",
            title="Deep Residual Learning for Image Recognition",
            abstract="Residual networks improve image recognition.",
            authors=["A. Researcher"],
            published="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
            entry_url="https://example.com/resnet",
            pdf_url="",
            categories=["cs.CV"],
        )
        summary = PaperSummary(
            short_summary="ResNet paper.",
            key_points=[],
            method_tags=["ResNet", "CNN"],
            relevance="Relevant.",
            reading_priority="high",
        )

        query = build_repository_query(paper, summary, "有没有 PyTorch 代码？")
        repository = repository_from_item(
            {
                "full_name": "example/resnet-pytorch",
                "html_url": "https://github.com/example/resnet-pytorch",
                "description": "PyTorch implementation of ResNet on ImageNet",
                "language": "Python",
                "stargazers_count": 1234,
                "updated_at": "2026-01-01T00:00:00Z",
                "topics": ["resnet", "imagenet"],
            },
            ["ResNet", "ImageNet"],
        )

        self.assertIn("Residual", query)
        self.assertIn("in:name,description,readme", query)
        self.assertEqual(repository["full_name"], "example/resnet-pytorch")
        self.assertIn("ResNet", repository["reason"])


if __name__ == "__main__":
    unittest.main()
