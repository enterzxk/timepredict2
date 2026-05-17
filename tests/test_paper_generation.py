import pytest
from timepredict_agent.llm_summary import AnthropicSummaryClient


def test_analyze_paper_structure():
    """测试论文结构分析功能"""
    client = AnthropicSummaryClient()
    if not client.available():
        pytest.skip("LLM not available")

    paper_title = "Test Paper"
    abstract = "This is a test abstract."
    pdf_text = (
        "Introduction\nThis is the introduction.\n\n"
        "Method\nThis is the method section.\n\n"
        "Experiments\nThis is the experiments section.\n\n"
        "Conclusion\nThis is the conclusion."
    )

    result = client.analyze_paper_structure(paper_title, abstract, pdf_text)

    assert result is not None
    assert "sections" in result
    assert len(result["sections"]) > 0
