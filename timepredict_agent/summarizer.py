from __future__ import annotations

import re

from .models import Paper, PaperSummary


METHOD_PATTERNS = {
    "Transformer": r"\b(transformer|attention)\b",
    "Foundation model": r"\b(foundation model|pre-trained|pretrained|large model)\b",
    "Diffusion": r"\b(diffusion|score-based)\b",
    "Probabilistic": r"\b(probabilistic|uncertainty|quantile|distribution)\b",
    "Multivariate": r"\b(multivariate|multi-variate|cross-channel)\b",
    "Long-term": r"\b(long-term|long horizon|long-range)\b",
    "Benchmark": r"\b(benchmark|dataset|empirical|evaluation)\b",
    "Anomaly": r"\b(anomaly|outlier)\b",
    "Representation learning": r"\b(representation|embedding|contrastive)\b",
    "Process mining": r"\b(process mining|event log|business process)\b",
    "Predictive process monitoring": r"\b(predictive process monitoring|predictive monitoring|process monitoring)\b",
    "Remaining time prediction": r"\b(remaining time prediction|remaining time|duration prediction)\b",
    "Incremental event log": r"\b(incremental event log|incremental log|evolving event log)\b",
}

RELEVANCE_TERMS = [
    "time series",
    "forecast",
    "forecasting",
    "prediction",
    "temporal",
    "multivariate",
    "long-term",
    "predictive process monitoring",
    "process mining",
    "remaining time prediction",
    "remaining time",
    "event log",
    "incremental event log",
]


class ExtractiveSummarizer:
    def summarize(self, paper: Paper) -> PaperSummary:
        sentences = _split_sentences(paper.abstract)
        ranked = sorted(sentences, key=self._score_sentence, reverse=True)
        method_tags = self._method_tags(f"{paper.title} {paper.abstract}")
        key_points = _chinese_key_points(paper, ranked, method_tags)
        short_summary = _chinese_short_summary(paper, method_tags)
        relevance_score = sum(
            term in f"{paper.title} {paper.abstract}".lower() for term in RELEVANCE_TERMS
        )
        reading_priority = "high" if relevance_score >= 4 else "medium" if relevance_score >= 2 else "low"
        relevance = self._relevance_text(relevance_score, method_tags)
        deep = _local_deep_explanation(paper, method_tags, ranked)
        return PaperSummary(
            short_summary=short_summary,
            key_points=key_points,
            method_tags=method_tags,
            relevance=relevance,
            reading_priority=reading_priority,
            deep_summary=deep["deep_summary"],
            contribution=deep["contribution"],
            method=deep["method"],
            experiments=deep["experiments"],
            limitations=deep["limitations"],
            reading_notes=deep["reading_notes"],
            innovation_points=[],
            method_comparison="",
            datasets_used=[],
            metrics_used=[],
            future_directions="",
        )

    def _score_sentence(self, sentence: str) -> int:
        text = sentence.lower()
        score = 0
        score += 4 if "forecast" in text else 0
        score += 4 if "predictive process monitoring" in text else 0
        score += 3 if "time series" in text else 0
        score += 3 if "process mining" in text or "event log" in text else 0
        score += 3 if "remaining time" in text else 0
        score += 2 if "propose" in text or "introduce" in text else 0
        score += 2 if "outperform" in text or "state-of-the-art" in text else 0
        score += 1 if "benchmark" in text or "dataset" in text else 0
        score += 1 if 80 <= len(sentence) <= 260 else 0
        return score

    def _method_tags(self, text: str) -> list[str]:
        tags = [
            label for label, pattern in METHOD_PATTERNS.items() if re.search(pattern, text, re.I)
        ]
        return tags or ["General time-series method"]

    def _relevance_text(self, score: int, tags: list[str]) -> str:
        if score >= 4:
            return f"和时间序列预测高度相关，建议优先阅读；关键词方向：{', '.join(tags[:3])}。"
        if score >= 2:
            return f"和时间序列建模或预测有明显关联，可作为补充阅读；关键词方向：{', '.join(tags[:3])}。"
        return "相关性较弱，建议只在标题或方法方向与你的研究问题匹配时阅读。"


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _dedupe(sentences: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for sentence in sentences:
        key = sentence.lower()
        if key not in seen:
            seen.add(key)
            result.append(sentence)
    return result


def _chinese_short_summary(paper: Paper, method_tags: list[str]) -> str:
    title_hint = paper.title
    domain = _domain_hint(paper)
    methods = "、".join(method_tags[:3])
    return (
        f"这篇论文关注“{title_hint}”。从摘要看，它的核心问题是{domain}，"
        f"主要方法线索包括{methods}。阅读时可以重点看作者如何定义预测目标、"
        "如何把模型输出转化为可评估的结果，以及实验是否证明这种设计比基线更可靠。"
    )


def _chinese_key_points(paper: Paper, ranked: list[str], method_tags: list[str]) -> list[str]:
    problem = _domain_hint(paper)
    method_sentence = _find_sentence(ranked, ["propose", "framework", "model", "transformer", "method"])
    experiment_sentence = _find_sentence(ranked, ["benchmark", "dataset", "experiment", "evaluation"])
    result_sentence = _find_sentence(ranked, ["improve", "outperform", "achieve", "strong", "state-of-the-art"])
    points = [
        f"研究问题：论文试图解决{problem}，重点不只是预测数值本身，也包括预测结果如何服务后续判断或决策。",
        f"方法主线：摘要中出现的关键技术标签是{', '.join(method_tags[:4])}，说明论文大概率围绕模型结构、表示学习或不确定性估计展开。",
    ]
    if method_sentence:
        points.append(f"方法细节：论文提出或组合了一个模型流程，用预测偏差、异常信号或多任务表示来形成最终判断。原文线索是：{method_sentence}")
    if experiment_sentence:
        points.append(f"实验设计：论文使用公开数据集或基准任务验证方法效果，重点应核对数据规模、评价指标、对比基线和消融实验。原文线索是：{experiment_sentence}")
    if result_sentence:
        points.append(f"结果解读：摘要声称方法相对基线有提升，阅读正文时需要确认提升幅度是否稳定、是否来自关键模块，以及是否有统计或消融支撑。原文线索是：{result_sentence}")
    points.append("阅读重点：建议先看问题定义和数据构造，再看模型结构，最后核对实验指标、消融实验和失败案例。")
    return _dedupe(points[:6])


def _local_deep_explanation(paper: Paper, method_tags: list[str], ranked: list[str]) -> dict[str, str]:
    problem = _domain_hint(paper)
    method_sentence = _find_sentence(ranked, ["propose", "framework", "model", "transformer", "method"])
    experiment_sentence = _find_sentence(ranked, ["benchmark", "dataset", "experiment", "evaluation"])
    result_sentence = _find_sentence(ranked, ["improve", "outperform", "achieve", "strong", "baseline"])
    methods = "、".join(method_tags[:5])
    named_methods = _extract_named_methods(paper.abstract)
    numerical_results = _extract_numerical_results(paper.abstract)

    method_detail = f"技术重点集中在{methods}"
    if named_methods:
        method_detail += f"。摘要中提到的具体方法/模型包括：{', '.join(named_methods)}"

    contribution_parts = [f"围绕{problem}提出新的建模方案"]
    if named_methods:
        contribution_parts.append(f"涉及{', '.join(named_methods[:3])}等具体技术")
    contribution_parts.append("通过实验验证方法有效性")

    result_text = "实验结果显示方法有效"
    if numerical_results:
        result_text = f"摘要中的关键数值结果：{'; '.join(numerical_results)}"

    return {
        "deep_summary": (
            f"这篇论文聚焦于{problem}。{method_detail}。"
            f"{'摘要中的关键描述：' + method_sentence if method_sentence else ''}"
        ),
        "contribution": "；".join(contribution_parts),
        "method": (
            f"方法层面涉及{methods}。"
            f"{'关键描述：' + method_sentence if method_sentence else ''}"
        ),
        "experiments": (
            f"{result_text}。"
            f"{'实验描述：' + experiment_sentence if experiment_sentence else ''}"
        ),
        "limitations": "仅凭摘要无法判断数据规模和跨场景泛化能力，建议阅读正文实验部分。",
        "reading_notes": (
            "建议先看问题定义和方法描述，再核对实验结果。"
            f"如果你的研究方向涉及{problem}，这篇论文值得细读。"
        ),
    }


def _extract_named_methods(text: str) -> list[str]:
    patterns = [
        r"\b([A-Z][A-Za-z]*(?:-[A-Za-z]+)*)\b",
        r"\b([A-Z]{2,}(?:-[A-Z0-9]+)*)\b",
    ]
    candidates = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            word = match.group(1)
            if len(word) > 2 and word not in {"The", "This", "Our", "We", "In", "On", "At", "For", "And", "Or", "Not", "But", "With", "From", "That", "These", "Those", "Each", "Both", "Some", "Many", "Most", "All", "Any", "Every", "Such", "When", "Where", "How", "Why", "What", "Which", "While", "During", "Before", "After", "Above", "Below", "Between", "Under", "Over", "Again", "Further", "Then", "Once", "Here", "There", "Also", "Just", "Only", "Even", "Still", "Already", "Yet", "Soon", "Later", "Often", "Never", "Always", "Sometimes", "Usually", "Generally", "Specifically", "Particularly", "Especially", "Mainly", "Mostly", "Largely", "Primarily", "Basically", "Essentially", "Fundamentally", "Principally", "Chiefly", "Predominantly", "Primarily", "Secondarily", "Tertiary", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"}:
                candidates.add(word)
    return list(candidates)[:5]


def _extract_numerical_results(text: str) -> list[str]:
    results = []
    patterns = [
        r"(\d+\.?\d*%?\s*(?:improvement|reduction|increase|decrease|better|worse|higher|lower|faster|slower|accuracy|precision|recall|F1|MAE|MSE|RMSE|MAPE|sMAPE))",
        r"(?:achiev|obtain|reach|attain|result)\w*\s+(\d+\.?\d*%?)",
        r"(\d+\.?\d*%?)\s+(?:improvement|reduction|increase|decrease|better|higher|lower)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            results.append(match.group(1).strip())
    return results[:3]


def _domain_hint(paper: Paper) -> str:
    text = f"{paper.title} {paper.abstract}".lower()
    if "predictive process monitoring" in text or "process mining" in text:
        return "流程挖掘中的预测性流程监控"
    if "remaining time" in text:
        return "业务流程实例的剩余时间预测"
    if "event log" in text or "event sequence" in text:
        return "事件日志或离散事件序列建模"
    if "incremental" in text and "log" in text:
        return "增量事件日志下的持续预测与模型更新"
    if "anomaly" in text or "relapse" in text:
        return "基于时间序列信号进行异常检测或风险预警"
    if "long-term" in text or "long horizon" in text:
        return "长预测步长下的时间序列预测"
    if "multivariate" in text:
        return "多变量时间序列预测"
    if "probabilistic" in text or "uncertainty" in text:
        return "带不确定性估计的时间序列预测"
    return "时间序列预测或时序建模"


def _find_sentence(sentences: list[str], keywords: list[str]) -> str:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence
    return ""
