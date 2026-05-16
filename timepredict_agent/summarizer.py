from __future__ import annotations

import re

from .models import Paper, PaperSummary


METHOD_PATTERNS = {
    "Transformer": r"\b(transformer|attention)\b",
    "LSTM": r"\b(lstm|long short-term memory)\b",
    "Autoencoder": r"\b(auto-?encoder|auto encoder)\b",
    "Large language model": r"\b(large language model|llm|language model)\b",
    "Multimodal LLM": r"\b(multimodal large language model|multimodal llm|vision-language|vision language|vlm)\b",
    "Foundation model": r"\b(foundation model|pre-trained|pretrained|large model)\b",
    "Reinforcement learning": r"\b(reinforcement learning|policy optimization|policy gradient)\b",
    "GRPO": r"\b(group relative policy optimization|grpo)\b",
    "Chain-of-thought": r"\b(chain-of-thought|cot|reasoning chain)\b",
    "Affordance grounding": r"\b(affordance|affordance grounding|affordance reasoning)\b",
    "Embodied AI": r"\b(embodied|robot|robotic|manipulation|open-world)\b",
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
    "Incremental event log": r"\b(incremental event logs?|incremental logs?|evolving event logs?)\b",
    "Incremental updating": r"\b(period-based updating|quantity-based updating|concept-drift-based updating|incremental update|model updating)\b",
    "Concept drift": r"\b(concept drift|concept-drift|business changes|dynamic changes)\b",
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
    def summarize(self, paper: Paper, full_text: str = "") -> PaperSummary:
        evidence_text = _evidence_text(paper, full_text)
        sentences = _split_sentences(evidence_text)
        ranked = sorted(sentences, key=self._score_sentence, reverse=True)
        method_tags = self._method_tags(f"{paper.title} {evidence_text}")
        profile = _domain_profile(paper, evidence_text)
        key_points = _chinese_key_points(paper, ranked, method_tags, profile)
        short_summary = _chinese_short_summary(paper, method_tags, profile)
        section_notes = _paper_section_notes(full_text)
        relevance_score = sum(
            term in f"{paper.title} {evidence_text}".lower() for term in RELEVANCE_TERMS
        )
        ai_score = _ai_relevance_score(paper)
        if relevance_score >= 4 or ai_score >= 5:
            reading_priority = "high"
        elif relevance_score >= 2 or ai_score >= 2:
            reading_priority = "medium"
        else:
            reading_priority = "low"
        relevance = self._relevance_text(relevance_score, ai_score, method_tags, profile)
        deep = _local_deep_explanation(paper, method_tags, ranked, profile, section_notes)
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
            innovation_points=_local_innovation_points(profile, method_tags, ranked, section_notes),
            method_comparison=deep["method_comparison"],
            datasets_used=_extract_dataset_names(evidence_text),
            metrics_used=_extract_metric_names(evidence_text),
            future_directions=deep["future_directions"],
        )

    def _score_sentence(self, sentence: str) -> int:
        text = sentence.lower()
        score = 0
        score += 4 if "forecast" in text else 0
        score += 4 if "predictive process monitoring" in text else 0
        score += 3 if "time series" in text else 0
        score += 3 if "process mining" in text or "event log" in text else 0
        score += 3 if "remaining time" in text else 0
        score += 4 if "affordance" in text else 0
        score += 3 if "multimodal" in text or "large language model" in text else 0
        score += 3 if "reinforcement learning" in text or "policy optimization" in text else 0
        score += 2 if "reasoning" in text or "grounding" in text else 0
        score += 2 if "propose" in text or "introduce" in text else 0
        score += 2 if "outperform" in text or "state-of-the-art" in text else 0
        score += 1 if "benchmark" in text or "dataset" in text else 0
        score += 1 if 80 <= len(sentence) <= 260 else 0
        return score

    def _method_tags(self, text: str) -> list[str]:
        tags = [
            label for label, pattern in METHOD_PATTERNS.items() if re.search(pattern, text, re.I)
        ]
        if tags:
            return tags
        if _ai_relevance_score_from_text(text) > 0:
            return ["General AI method"]
        return ["General research method"]

    def _relevance_text(self, score: int, ai_score: int, tags: list[str], profile: dict[str, str]) -> str:
        if score >= 4:
            return f"和时间序列预测高度相关，建议优先阅读；关键词方向：{', '.join(tags[:3])}。"
        if score >= 2:
            return f"和时间序列建模或预测有明显关联，可作为补充阅读；关键词方向：{', '.join(tags[:3])}。"
        if ai_score >= 2:
            return (
                f"和你的主线时间序列/流程预测关系不直接，但属于{profile['domain']}方向。"
                f"如果你想补充 AI/深度学习、推理或多模态方法背景，可以作为方法启发阅读；关键词方向：{', '.join(tags[:3])}。"
            )
        return "相关性较弱，建议只在标题或方法方向与你的研究问题匹配时阅读。"


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _evidence_text(paper: Paper, full_text: str = "") -> str:
    full_text = re.sub(r"\s+", " ", full_text or "").strip()
    if not full_text:
        return paper.abstract
    section_notes = _paper_section_notes(full_text)
    selected = [
        paper.abstract,
        section_notes.get("abstract", ""),
        section_notes.get("method", ""),
        section_notes.get("experiments", ""),
        section_notes.get("results", ""),
        section_notes.get("conclusion", ""),
    ]
    merged = " ".join(item for item in selected if item)
    return merged or full_text[:6000]


def _paper_section_notes(full_text: str) -> dict[str, str]:
    text = re.sub(r"\s+", " ", full_text or "").strip()
    if not text:
        return {}
    section_patterns = {
        "abstract": r"\babstract\b(.{80,1800}?)(?:\b1\s+introduction\b|\bintroduction\b|\bkeywords?\b)",
        "method": r"\b(?:method|methodology|approach|model|framework|proposed method)\b(.{80,2600}?)(?:\bexperiment|\bevaluation|\bresults|\bimplementation|\bconclusion)",
        "experiments": r"\b(?:experiment|experimental setup|evaluation|benchmark)\b(.{80,2600}?)(?:\bablation|\bdiscussion|\bconclusion|\breferences)",
        "results": r"\b(?:results?|ablation|comparison)\b(.{80,2400}?)(?:\bdiscussion|\bconclusion|\blimitation|\breferences)",
        "conclusion": r"\b(?:conclusion|limitations?|future work)\b(.{80,1600}?)(?:\breferences|acknowledg|$)",
    }
    notes: dict[str, str] = {}
    for key, pattern in section_patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            notes[key] = match.group(1).strip()
    metric_sentences = [
        sentence for sentence in _split_sentences(text)
        if re.search(r"\b(MAE|RMSE|MSE|MAPE|accuracy|precision|recall|F1|AUC|IoU|mAP|baseline|retraining)\b", sentence, re.I)
    ]
    if metric_sentences:
        notes["experiments"] = " ".join([notes.get("experiments", ""), *metric_sentences[:4]]).strip()
    if not notes:
        notes["body"] = text[:5000]
    return notes


def _dedupe(sentences: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for sentence in sentences:
        key = sentence.lower()
        if key not in seen:
            seen.add(key)
            result.append(sentence)
    return result


def _chinese_short_summary(paper: Paper, method_tags: list[str], profile: dict[str, str]) -> str:
    title_hint = paper.title
    methods = "、".join(method_tags[:3])
    return (
        f"这篇论文关注“{title_hint}”。从摘要看，它的核心问题是{profile['domain']}，"
        f"主要方法线索包括{methods}。阅读时可以重点看{profile['problem_focus']}，"
        f"以及实验是否证明这种设计在{profile['evaluation_focus']}上比基线更可靠。"
        f"它对读者的价值主要在于：{profile['reader_value']}。"
    )


def _chinese_key_points(paper: Paper, ranked: list[str], method_tags: list[str], profile: dict[str, str]) -> list[str]:
    method_sentence = _find_sentence(ranked, ["propose", "framework", "model", "transformer", "method"])
    experiment_sentence = _find_sentence(ranked, ["benchmark", "dataset", "experiment", "evaluation"])
    result_sentence = _find_sentence(ranked, ["improve", "outperform", "achieve", "strong", "state-of-the-art"])
    points = [
        f"研究问题：论文试图解决{profile['domain']}，重点是{profile['problem_focus']}。",
        f"方法主线：摘要中出现的关键技术标签是{', '.join(method_tags[:4])}，说明论文大概率围绕{profile['method_focus']}展开。",
    ]
    if method_sentence:
        points.append(f"方法细节：论文提出或组合了一个模型流程，用{profile['mechanism_focus']}来形成最终判断。原文线索是：{method_sentence}")
    if experiment_sentence:
        points.append(f"实验设计：论文使用公开数据集或基准任务验证方法效果，重点应核对数据规模、评价指标、对比基线和消融实验。原文线索是：{experiment_sentence}")
    if result_sentence:
        points.append(f"结果解读：摘要声称方法相对基线有提升，阅读正文时需要确认提升幅度是否稳定、是否来自关键模块，以及是否有统计或消融支撑。原文线索是：{result_sentence}")
    points.extend(
        [
            f"输入输出：建议在正文中确认模型输入是什么、输出是什么，以及输出是否能直接支持{profile['evaluation_focus']}。",
            f"训练与优化：重点看作者如何构造训练信号、奖励或损失函数，因为这通常决定方法是否只是工程组合，还是有清楚的优化目标。",
            f"泛化能力：重点看实验是否覆盖跨场景、开放世界或跨数据集设置；如果只在单一数据集上验证，结论要谨慎看待。",
            f"可复现性：留意数据集、标注方式、模型规模、训练成本和消融实验是否写清楚，这些决定你能不能复用或改进该方法。",
        ]
    )
    points.append(f"阅读重点：建议先看{profile['reading_focus']}，最后核对实验指标、消融实验和失败案例。")
    return _dedupe(points[:10])


def _local_deep_explanation(
    paper: Paper,
    method_tags: list[str],
    ranked: list[str],
    profile: dict[str, str],
    section_notes: dict[str, str],
) -> dict[str, str]:
    method_sentence = _find_sentence(ranked, ["propose", "framework", "model", "transformer", "method"])
    experiment_sentence = _find_sentence(ranked, ["benchmark", "dataset", "experiment", "evaluation"])
    result_sentence = _find_sentence(ranked, ["improve", "outperform", "achieve", "strong", "baseline"])
    methods = "、".join(method_tags[:5])
    named_methods = _extract_named_methods(paper.abstract)
    numerical_results = _extract_numerical_results(paper.abstract)
    datasets = _extract_dataset_names(" ".join([paper.abstract, *section_notes.values()]))

    method_detail = f"技术重点集中在{methods}"
    if named_methods:
        method_detail += f"。摘要中提到的具体方法/模型包括：{', '.join(named_methods)}"

    contribution_parts = [f"围绕{profile['domain']}提出新的建模方案"]
    if named_methods:
        contribution_parts.append(f"涉及{', '.join(named_methods[:3])}等具体技术")
    contribution_parts.append("通过实验验证方法有效性")

    result_text = "实验结果显示方法有效"
    if numerical_results:
        result_text = f"摘要中的关键数值结果：{'; '.join(numerical_results)}"
    method_note = _compress_note(section_notes.get("method", ""), 480)
    experiment_note = _compress_note(section_notes.get("experiments", "") or section_notes.get("results", ""), 520)
    conclusion_note = _compress_note(section_notes.get("conclusion", ""), 260)
    dataset_text = f"可识别的数据集/基准包括：{', '.join(datasets)}。" if datasets else "当前材料没有给出足够完整的数据集名称，正文实验部分需要重点补看。"

    return {
        "deep_summary": (
            f"这篇论文聚焦于{profile['domain']}，核心不是简单提出一个新名字，而是试图解决一个具体瓶颈：{profile['problem_focus']}。"
            f"从摘要能看出，作者把问题放在{profile['method_focus']}这个技术框架下处理，{method_detail}。"
            f"{'论文最关键的方法线索是：' + method_sentence + '。' if method_sentence else ''}"
            f"{'从全文方法段还能看到：' + method_note + '。' if method_note else ''}"
            f"理解这篇论文时，可以把它拆成三层：第一层是任务定义，也就是模型到底要判断什么；第二层是方法机制，也就是{profile['mechanism_focus']}如何被组织成训练或推理流程；第三层是验证方式，也就是作者是否真的证明了{profile['evaluation_focus']}。"
            f"因此，这篇论文是否值得精读，主要取决于你是否需要借鉴它的{profile['reader_value']}，以及正文是否把数据构造、消融实验和失败案例交代清楚。"
        ),
        "contribution": "；".join(contribution_parts),
        "method": (
            f"方法可以按流程理解。首先，论文需要把原始输入转成模型能处理的任务表示，这一步对应{profile['problem_focus']}。"
            f"其次，模型主体围绕{methods}展开，用{profile['mechanism_focus']}把输入、推理过程和输出连接起来。"
            f"{'摘要中直接给出的关键实现线索是：' + method_sentence + '。' if method_sentence else ''}"
            f"{'全文方法段提供的线索是：' + method_note + '。' if method_note else ''}"
            f"再次，训练阶段的关键不是只看最终答案，而是看作者是否设计了中间推理、奖励、损失函数或监督信号来约束模型行为。"
            f"最后，推理阶段要看模型输出是否具有可解释性、是否能定位到具体证据，以及是否能在新场景里保持稳定。阅读正文时建议画出“输入-中间模块-训练目标-输出-评价指标”的流程图。"
        ),
        "experiments": (
            f"{result_text}。{dataset_text}"
            f"{'摘要中的实验描述是：' + experiment_sentence + '。' if experiment_sentence else ''}"
            f"{'全文实验/结果段提供的线索是：' + experiment_note + '。' if experiment_note else ''}"
            f"看实验时不要只看是否 outperform，还要看三件事：一是对比基线是否足够强，是否包含同类多模态/强化学习/推理增强方法；二是消融实验是否能证明关键模块确实有用，而不是靠更大模型或更多数据取得提升；三是泛化实验是否覆盖训练分布之外的样本。"
            f"如果论文声称具备开放世界或跨场景泛化能力，正文中应当有清楚的数据划分、失败案例和定性可视化。"
        ),
        "limitations": (
            "需要重点核对三类局限：数据集是否覆盖真实复杂场景、对比基线是否足够强、消融是否能证明每个模块必要。"
            f"{'论文结论/局限段线索：' + conclusion_note + '。' if conclusion_note else '如果当前材料没有全文实验表和消融结果，仅凭摘要不能确认提升幅度和统计可靠性。'}"
        ),
        "reading_notes": f"建议先看{profile['reading_focus']}，再核对实验结果。如果你的研究方向涉及{profile['domain']}，这篇论文值得细读。",
        "method_comparison": (
            f"相较于普通端到端模型，这类方法的重点在于是否显式建模{profile['mechanism_focus']}。"
            f"如果只是把现有大模型接到新数据集上，创新性会偏弱；如果它通过新的训练目标、推理链、奖励设计或 grounding 机制让模型获得更强泛化能力，贡献就更实。"
            f"阅读时建议把它和不使用该机制的基线、只使用监督学习的版本、以及不含关键模块的消融版本逐项比较。"
        ),
        "future_directions": (
            f"后续可以沿三个方向扩展：第一，把方法放到更复杂或更真实的场景中验证，检查{profile['evaluation_focus']}是否仍然成立；"
            f"第二，补充可解释性和失败案例分析，说明模型什么时候可靠、什么时候会误判；"
            f"第三，降低训练和标注成本，让这种方法更容易迁移到新的数据集、任务或应用场景。"
        ),
    }


def _extract_named_methods(text: str) -> list[str]:
    patterns = [
        r"\b([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)\b",
        r"\b([A-Z]{2,}(?:-[A-Z0-9]+)*)\b",
    ]
    candidates = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            word = match.group(1)
            if len(word) > 2 and word not in {"The", "This", "Our", "We", "In", "On", "At", "For", "And", "Or", "Not", "But", "With", "From", "That", "These", "Those", "Each", "Both", "Some", "Many", "Most", "All", "Any", "Every", "Such", "When", "Where", "How", "Why", "What", "Which", "While", "During", "Before", "After", "Above", "Below", "Between", "Under", "Over", "Again", "Further", "Then", "Once", "Here", "There", "Also", "Just", "Only", "Even", "Still", "Already", "Yet", "Soon", "Later", "Often", "Never", "Always", "Sometimes", "Usually", "Generally", "Specifically", "Particularly", "Especially", "Mainly", "Mostly", "Largely", "Primarily", "Basically", "Essentially", "Fundamentally", "Principally", "Chiefly", "Predominantly", "Primarily", "Secondarily", "Tertiary", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"}:
                candidates.add(word)
    return list(candidates)[:5]


def _local_innovation_points(
    profile: dict[str, str],
    method_tags: list[str],
    ranked: list[str],
    section_notes: dict[str, str] | None = None,
) -> list[str]:
    method_sentence = _find_sentence(ranked, ["propose", "framework", "integrate", "unified", "model"])
    tags = set(method_tags)
    points = []
    if "Affordance grounding" in tags:
        points.append("把可供性推理从普通视觉理解推进到可供性 grounding：不仅判断场景里有什么，还判断对象或区域支持什么动作。")
    if "GRPO" in tags or "Reinforcement learning" in tags:
        points.append("使用强化学习/GRPO 优化推理过程，使模型不只模仿标注答案，而是通过奖励信号提升可泛化的推理行为。")
    if "Chain-of-thought" in tags:
        points.append("引入 Chain-of-Thought 或认知式推理链，把可供性判断拆成更可解释的中间推理步骤。")
    if "Multimodal LLM" in tags:
        points.append("把视觉场景理解、语言推理和动作可行性判断统一到多模态大模型框架中。")
    if "Remaining time prediction" in tags and "Incremental event log" in tags:
        points.append("把剩余时间预测从静态离线模型推进到增量事件日志场景：模型需要随着新事件日志到来持续更新，而不是一次训练后长期固定。")
    if "Incremental updating" in tags:
        points.append("提出多种模型更新触发策略，包括按时间周期、按新增日志数量和按概念漂移触发更新，用来适应业务过程动态变化。")
    if "Concept drift" in tags:
        points.append("把业务变化/概念漂移显式纳入预测框架，关注模型在销售渠道扩展、流程行为变化等情况下是否还能保持准确。")
    if {"LSTM", "Transformer", "Autoencoder"} & tags and "Incremental event log" in tags:
        points.append("不是只提出单一模型，而是把 LSTM、Transformer、Auto-encoder 等不同深度模型适配到统一的增量预测框架中，便于比较框架本身的有效性。")
    if not points and method_sentence:
        points.append(f"摘要显示作者提出了新的方法组合或框架，关键线索是：{method_sentence}")
    section_notes = section_notes or {}
    method_note = _compress_note(section_notes.get("method", ""), 260)
    if method_note:
        points.append(f"全文方法段提供的额外创新线索：{method_note}")
    if not points:
        points.append(f"围绕{profile['domain']}组织模型和实验，相比只报告结果的工作，更需要关注其问题定义和实验设计是否成立。")
    return points[:5]


def _compress_note(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    sentences = _split_sentences(text)
    if sentences:
        selected = " ".join(sentences[:3])
    else:
        selected = text
    return selected[:max_chars].rstrip()


def _extract_dataset_names(text: str) -> list[str]:
    datasets = []
    if re.search(r"\bnine real-life event logs\b", text, re.I):
        datasets.append("nine real-life event logs")
    patterns = [
        r"\b([A-Z][A-Za-z0-9_-]{3,}\s+Log)\b",
        r"\b([A-Z][A-Za-z0-9_-]{3,}\s+event logs?)\b",
        r"\bon\s+([A-Z][A-Za-z0-9_-]{3,})\b",
        r"\busing\s+([A-Z][A-Za-z0-9_-]{3,})\b",
        r"\b([A-Z][A-Za-z0-9_-]{3,})\s+(?:dataset|benchmark|data set)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            if name not in {"Comprehensive", "Existing", "Abstract", "Introduction"}:
                datasets.append(name)
    return _dedupe(datasets)[:6]


def _extract_metric_names(text: str) -> list[str]:
    metrics = []
    for metric in ["prediction accuracy", "runtime", "accuracy", "precision", "recall", "F1", "mAP", "IoU", "MAE", "RMSE", "MSE", "AUC"]:
        if re.search(rf"\b{re.escape(metric)}\b", text, re.I):
            metrics.append(metric)
    return _dedupe(metrics)


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


def _domain_profile(paper: Paper, evidence_text: str = "") -> dict[str, str]:
    text = f"{paper.title} {evidence_text or paper.abstract}".lower()
    if "affordance" in text:
        return {
            "domain": "多模态大模型中的可供性推理与可供性定位",
            "problem_focus": "模型如何从视觉场景中判断对象或区域支持哪些动作，并把这种判断泛化到开放世界场景",
            "method_focus": "多模态推理、视觉定位、强化学习优化和链式思考监督",
            "mechanism_focus": "可供性 grounding、Chain-of-Thought 推理和策略优化",
            "evaluation_focus": "可供性识别、视觉 grounding、开放世界泛化和与既有方法的对比",
            "reading_focus": "任务定义、可供性标注/数据构造、GRPO 训练流程、推理链设计、泛化实验",
            "reader_value": "可供性推理框架、强化学习优化思路和开放世界泛化实验设计",
        }
    if any(term in text for term in ["multimodal", "large language model", "llm", "vision-language", "foundation model"]):
        return {
            "domain": "多模态大模型或基础模型的推理与泛化",
            "problem_focus": "模型如何结合视觉、语言和任务上下文完成更可靠的推理或决策",
            "method_focus": "模型结构、训练策略、数据构造和推理流程",
            "mechanism_focus": "表示学习、跨模态对齐、指令/偏好优化或推理增强",
            "evaluation_focus": "基准任务、泛化能力、对比基线和消融实验",
            "reading_focus": "问题定义、数据来源、模型训练方式、推理流程和泛化评估",
            "reader_value": "多模态推理建模、训练策略和泛化评估方法",
        }
    if "reinforcement learning" in text or "policy optimization" in text:
        return {
            "domain": "强化学习驱动的模型优化与决策推理",
            "problem_focus": "如何通过奖励信号或策略优化提升模型在复杂任务中的决策能力",
            "method_focus": "奖励设计、策略优化、训练稳定性和泛化能力",
            "mechanism_focus": "策略更新、奖励建模和推理过程约束",
            "evaluation_focus": "任务成功率、泛化实验、消融实验和训练稳定性",
            "reading_focus": "奖励函数、优化目标、训练流程、对比基线和失败案例",
            "reader_value": "奖励设计、策略优化和复杂任务决策能力提升方法",
        }
    if ("predictive process monitoring" in text or "process mining" in text) and "remaining time" in text:
        domain = "流程挖掘中的业务流程剩余时间预测"
    elif "predictive process monitoring" in text or "process mining" in text:
        domain = "流程挖掘中的预测性流程监控"
    elif "remaining time" in text:
        domain = "业务流程实例的剩余时间预测"
    elif "event log" in text or "event sequence" in text:
        domain = "事件日志或离散事件序列建模"
    elif "incremental" in text and "log" in text:
        domain = "增量事件日志下的持续预测与模型更新"
    elif "anomaly" in text or "relapse" in text:
        domain = "基于时间序列信号进行异常检测或风险预警"
    elif "long-term" in text or "long horizon" in text:
        domain = "长预测步长下的时间序列预测"
    elif "multivariate" in text:
        domain = "多变量时间序列预测"
    elif "probabilistic" in text or "uncertainty" in text:
        domain = "带不确定性估计的时间序列预测"
    else:
        domain = "论文所描述的研究任务"
    return {
        "domain": domain,
        "problem_focus": "作者如何定义输入、输出和预测目标，以及该目标服务什么实际判断",
        "method_focus": "模型结构、表示学习、预测目标或不确定性估计",
        "mechanism_focus": "序列表示、预测误差、上下文特征或多任务信号",
        "evaluation_focus": "预测精度、稳定性、跨数据集泛化和对比基线",
        "reading_focus": "问题定义和数据构造，再看模型结构",
        "reader_value": "任务建模方式、特征/序列表示和实验对比设计",
    }


def _ai_relevance_score(paper: Paper) -> int:
    return _ai_relevance_score_from_text(
        " ".join([paper.title, paper.abstract, paper.venue, " ".join(paper.categories), " ".join(paper.fields_of_study)])
    )


def _ai_relevance_score_from_text(text: str) -> int:
    lowered = text.lower()
    terms = [
        "artificial intelligence",
        "deep learning",
        "machine learning",
        "large language model",
        "llm",
        "multimodal",
        "vision-language",
        "reinforcement learning",
        "policy optimization",
        "affordance",
        "grounding",
        "computer vision",
        "natural language processing",
        "foundation model",
        "transformer",
    ]
    return sum(term in lowered for term in terms)


def _find_sentence(sentences: list[str], keywords: list[str]) -> str:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence
    return ""
