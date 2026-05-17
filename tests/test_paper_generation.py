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

    if result is None:
        pytest.skip("LLM API call failed (auth error or network issue)")
    assert "sections" in result
    assert len(result["sections"]) > 0


def test_generate_paper_content():
    """测试论文内容生成功能"""
    client = AnthropicSummaryClient()
    if not client.available():
        pytest.skip("LLM not available")

    structure = {
        "sections": [
            {"title": "Introduction", "level": 1, "content_type": "introduction"},
            {"title": "Method", "level": 1, "content_type": "method"},
            {"title": "Experiments", "level": 1, "content_type": "experiment"},
            {"title": "Conclusion", "level": 1, "content_type": "conclusion"}
        ],
        "writing_style": "学术论文风格"
    }

    topic = "基于 Transformer 的时间序列预测"
    outline = ["问题定义", "模型架构", "实验设计", "结果分析"]

    result = client.generate_paper_content(structure, topic, outline)

    if result is None:
        pytest.skip("LLM API call failed (auth error or network issue)")
    assert "content" in result
    assert len(result["content"]) > 0
