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

    def test_frontend_related_summary_has_back_navigation_contract(self):
        app_js = (Path(__file__).resolve().parents[1] / "timepredict_agent" / "static" / "app.js").read_text(
            encoding="utf-8"
        )

        expected_contracts = [
            "detailHistory",
            "data-history-back",
            "restoreDetailHistory",
            "data-return-recommendations",
            "returnToRecommendationList",
            'id="recommendationSpotlight"',
            'scrollToDetailTarget("recommendationSpotlight"',
        ]

        for contract in expected_contracts:
            with self.subTest(contract=contract):
                self.assertIn(contract, app_js)

    def test_frontend_daily_recommendations_contract(self):
        root = Path(__file__).resolve().parents[1]
        app_js = (root / "timepredict_agent" / "static" / "app.js").read_text(encoding="utf-8")
        index_html = (root / "timepredict_agent" / "static" / "index.html").read_text(encoding="utf-8")

        for contract in [
            'data-nav="daily"',
            "每日推荐",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, index_html)

        for contract in [
            "daily",
            "loadDailyRecommendations",
            "/api/daily-recommendations",
            "renderDailyRecommendationCard",
            "质量信号",
            "加入论文库",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, app_js)

    def test_frontend_review_allows_single_selected_paper(self):
        root = Path(__file__).resolve().parents[1]
        app_js = (root / "timepredict_agent" / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("请至少选择 1 篇论文来生成综述。", app_js)
        self.assertNotIn("请至少选择 2 篇论文来生成综述。", app_js)

    def test_frontend_expert_chat_contract(self):
        root = Path(__file__).resolve().parents[1]
        app_js = (root / "timepredict_agent" / "static" / "app.js").read_text(encoding="utf-8")
        styles_css = (root / "timepredict_agent" / "static" / "styles.css").read_text(encoding="utf-8")
        web_py = (root / "timepredict_agent" / "web.py").read_text(encoding="utf-8")

        for contract in [
            "论文专家 Agent",
            "renderExpertChat",
            "data-expert-submit",
            "data-expert-github",
            "submitExpertQuestion",
            "expertHistoryForPayload",
            "/expert-chat",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, app_js)

        self.assertIn(".expert-chat", styles_css)
        self.assertIn("_handle_expert_chat", web_py)

    def test_frontend_has_standalone_expert_view(self):
        root = Path(__file__).resolve().parents[1]
        app_js = (root / "timepredict_agent" / "static" / "app.js").read_text(encoding="utf-8")
        index_html = (root / "timepredict_agent" / "static" / "index.html").read_text(encoding="utf-8")
        styles_css = (root / "timepredict_agent" / "static" / "styles.css").read_text(encoding="utf-8")

        for contract in [
            'data-nav="expert"',
            "论文专家",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, index_html)

        for contract in [
            "expert",
            "renderExpertPanel",
            "expert-detail",
            "openExpertForSelectedPaper",
            "data-expert-open-selected",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, app_js)

        self.assertIn(".expert-hero", styles_css)

    def test_frontend_expert_view_has_chat_surface_and_collapsible_paper_list(self):
        root = Path(__file__).resolve().parents[1]
        app_js = (root / "timepredict_agent" / "static" / "app.js").read_text(encoding="utf-8")
        styles_css = (root / "timepredict_agent" / "static" / "styles.css").read_text(encoding="utf-8")
        web_py = (root / "timepredict_agent" / "web.py").read_text(encoding="utf-8")

        for contract in [
            "expertPapersCollapsed",
            "expertSessions",
            "loadExpertSessions",
            "createExpertSession",
            "/api/agent/sessions",
            "/api/agent/feedback",
            "data-agent-feedback",
            "agent-status",
            "tool_calls",
            "reflection",
            "expertPaperPanelToggle",
            "expertPaperRail",
            "toggleExpertPaperPanel",
            "renderExpertHistoryPanel",
            "data-expert-new-chat",
            "data-expert-session",
            "data-expert-toggle-papers",
            "expert-shell",
            "expert-collapsed",
            "expert-chat-layout",
            "expert-history-panel",
            "expert-chat-stage",
            "expert-askbar",
            "我们先从哪里开始呢？",
            "data-expert-suggestion",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, app_js)

        for contract in [
            ".content-grid.expert-view",
            ".content-grid.expert-collapsed",
            ".panel-heading-actions",
            ".expert-paper-rail",
            ".workspace.expert-shell .workspace-intro",
            ".workspace.expert-shell .toolbar",
            ".workspace.expert-shell .metrics",
            ".expert-chat-layout",
            ".expert-history-panel",
            ".expert-chat-stage",
            ".expert-askbar",
            ".expert-quick-actions",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, styles_css)

        for contract in [
            "_handle_agent_sessions",
            "_handle_agent_feedback",
            "session_id=payload.get(\"session_id\")",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, web_py)

        for removed_contract in [
            "timepredict.expertSessions.v1",
            "EXPERT_SESSIONS_KEY",
            "window.localStorage.getItem(EXPERT_SESSIONS_KEY)",
            "window.localStorage.setItem(EXPERT_SESSIONS_KEY",
            "expert-stage-topbar",
            "expert-current-paper",
            "expert-context-fold",
            "当前咨询论文",
            "刷新当前论文",
        ]:
            with self.subTest(removed_contract=removed_contract):
                self.assertNotIn(removed_contract, app_js)


if __name__ == "__main__":
    unittest.main()
