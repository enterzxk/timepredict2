from timepredict_agent.llm_summary import _extract_json, _merge_summary, _safe_max_tokens
from timepredict_agent.models import PaperSummary
import unittest


class LlmSummaryTest(unittest.TestCase):
    def test_safe_max_tokens_clamps_overlarge_env_value(self):
        import os

        old_value = os.environ.get("TIMEPREDICT_LLM_MAX_TOKENS")
        os.environ["TIMEPREDICT_LLM_MAX_TOKENS"] = "1800000"
        try:
            self.assertEqual(_safe_max_tokens(), 131072)
        finally:
            if old_value is None:
                os.environ.pop("TIMEPREDICT_LLM_MAX_TOKENS", None)
            else:
                os.environ["TIMEPREDICT_LLM_MAX_TOKENS"] = old_value

    def test_extract_json_from_markdown_like_response(self):
        payload = _extract_json('好的：{"reading_priority":"high","key_points":["A"]}')

        self.assertEqual(payload["reading_priority"], "high")
        self.assertEqual(payload["key_points"], ["A"])

    def test_extract_json_falls_back_to_text_summary(self):
        payload = _extract_json("这是一段普通中文讲解，没有 JSON。")

        self.assertIn("普通中文讲解", payload["deep_summary"])
        self.assertEqual(payload["reading_priority"], "medium")

    def test_extract_json_salvages_truncated_json_like_text(self):
        payload = _extract_json(
            '{"short_summary":"中文概览","deep_summary":"深度解释","key_points":["要点一","要点二"],'
        )

        self.assertEqual(payload["short_summary"], "中文概览")
        self.assertEqual(payload["deep_summary"], "深度解释")
        self.assertEqual(payload["key_points"], ["要点一", "要点二"])

    def test_extract_json_composes_summary_when_deep_summary_is_missing(self):
        payload = _extract_json('{"short_summary":"中文概览","key_points":["要点一","要点二"],')

        self.assertIn("中文概览", payload["deep_summary"])
        self.assertIn("要点一", payload["deep_summary"])

    def test_merge_summary_keeps_defaults(self):
        current = PaperSummary(
            short_summary="old",
            key_points=["old point"],
            method_tags=["Transformer"],
            relevance="old relevance",
            reading_priority="medium",
        )

        merged = _merge_summary(
            current,
            {
                "short_summary": "new",
                "deep_summary": "deep",
                "reading_priority": "high",
            },
            "test-model",
        )

        self.assertEqual(merged.short_summary, "new")
        self.assertEqual(merged.key_points, ["old point"])
        self.assertEqual(merged.deep_summary, "deep")
        self.assertEqual(merged.llm_model, "test-model")


if __name__ == "__main__":
    unittest.main()
