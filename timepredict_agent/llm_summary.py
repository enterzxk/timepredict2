from __future__ import annotations

from dataclasses import replace
from os import environ
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import os
import re
import ssl
import subprocess
import tempfile

from .models import Paper, PaperSummary


ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 8192
HARD_MAX_TOKENS = 131072


class AnthropicSummaryClient:
    def __init__(self) -> None:
        load_local_env()
        self.base_url = environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        self.model = environ.get(
            "ANTHROPIC_MODEL",
            environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514"),
        )
        self.token = environ.get("ANTHROPIC_AUTH_TOKEN") or environ.get("ANTHROPIC_API_KEY") or ""

    def available(self) -> bool:
        return bool(self.token and self.model)

    def summarize(self, paper: Paper, current: PaperSummary, pdf_text: str = "") -> PaperSummary:
        if not self.available():
            raise RuntimeError("未检测到 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY。")

        payload = {
            "model": self.model,
            "max_tokens": _safe_max_tokens(),
            "temperature": 0.2,
            "system": (
                "你是时间序列预测、业务过程预测、事件序列建模方向的研究助理。"
                "请用简体中文帮助研究者深入理解论文。"
                "你的目标不是翻译摘要，而是帮助读者理解：论文要解决什么问题、为什么重要、方法怎么做、实验说明了什么、有什么局限、该不该精读。"
                "优先严格输出 JSON；如果无法输出 JSON，也必须给出完整中文讲解。"
                "不要输出思考过程，不要输出推理草稿，只输出最终答案。"
            ),
            "messages": [
                {
                    "role": "user",
                    "content": _build_prompt(paper, current, pdf_text),
                }
            ],
        }
        response = _post_json(f"{self.base_url}/v1/messages", payload, self.token)
        text = _message_text(response)
        parsed = _extract_json(text)
        return _merge_summary(current, parsed, self.model)

    def write_literature_review(self, papers: list[dict], topic: str) -> str:
        if not self.available():
            raise RuntimeError("未检测到 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY。")

        payload = {
            "model": self.model,
            "max_tokens": _safe_max_tokens(),
            "temperature": 0.25,
            "system": (
                "你是时间序列预测、事件序列预测、预测性流程监控和流程挖掘方向的论文写作助手。"
                "请帮助研究者基于给定论文写中文文献综述草稿。"
                "必须忠于给定论文，不要编造不存在的数据集、指标、结论或引用。"
                "不要直接大段复制摘要原文，要用自己的话进行综合、归纳和比较。"
            ),
            "messages": [
                {
                    "role": "user",
                    "content": _build_review_prompt(papers, topic),
                }
            ],
        }
        response = _post_json(f"{self.base_url}/v1/messages", payload, self.token)
        text = _message_text(response)
        if not text:
            raise RuntimeError("LLM 返回为空。")
        return text.strip()


def _build_prompt(paper: Paper, current: PaperSummary, pdf_text: str = "") -> str:
    authors = ", ".join(paper.authors[:8])
    pdf_section = ""
    if pdf_text:
        pdf_section = f"\n\n论文全文（前 15000 字符）：\n{pdf_text[:15000]}"
    return f"""
请阅读下面的论文元数据和摘要，生成适合时间序列预测、业务过程预测、事件序列建模研究者阅读的中文深度解读。

你的目标不是翻译摘要，而是帮助读者理解：论文要解决什么问题、为什么重要、方法怎么做、实验说明了什么、有什么局限、该不该精读。

输出要求：
1. 最好只返回一个 JSON 对象，不要使用 Markdown 代码块。
2. JSON 必须以左大括号开头、以右大括号结尾。
3. 所有解释性字段必须使用简体中文，method_tags/topic_tags 可以用英文标签。
4. 如果你无法严格输出 JSON，也请直接输出完整中文讲解，程序会自动兜底保存。
5. 不要人为限制字数，写清楚即可，但避免冗余。

JSON 字段如下：
- short_summary: 3-5 句中文概览，涵盖问题、方法、核心结果
- key_points: 6-10 个关键要点数组，每个要点应该是一个具体的技术点或发现
- method_tags: 3-8 个英文方法标签数组
- topic_tags: 3-8 个英文主题标签数组
- relevance: 详细说明它和时间序列预测/业务过程预测研究的关系，以及对后续研究的启发
- reading_priority: high / medium / low
- deep_summary: 500-800 字中文深度总结，需要涵盖问题定义、方法思路、关键创新、实验结论
- contribution: 详细列出主要贡献，每个贡献点单独说明
- method: 详细的方法机制拆解，包括模型架构、关键模块、训练策略、推理流程
- innovation_points: 数组，列出 3-5 个具体的创新点，每个创新点说明"相比已有方法，本文做了什么不同的"
- method_comparison: 与已有方法（如 Transformer、LSTM、传统方法等）的对比分析，说明本方法的优势和劣势
- experiments: 详细的实验分析，包括数据集、评价指标、对比基线、关键结果、消融实验结论
- datasets_used: 数组，列出论文使用的所有数据集名称
- metrics_used: 数组，列出论文使用的所有评价指标
- limitations: 局限性分析，包括数据假设、方法限制、未验证的场景
- future_directions: 作者提出的或可以推断的未来研究方向
- reading_notes: 给读者的阅读建议，包括：是否值得精读、重点看哪些章节、适合什么背景的读者

论文标题：{paper.title}
作者：{authors}
来源：{paper.source}
发表时间：{paper.published}
venue：{paper.venue}
已有本地摘要：{current.short_summary}
已有要点：{"; ".join(current.key_points)}
摘要：
{paper.abstract}{pdf_section}
""".strip()


def _build_review_prompt(papers: list[dict], topic: str) -> str:
    paper_blocks = []
    for index, paper in enumerate(papers, 1):
        paper_blocks.append(
            f"""
[P{index}] {paper['title']}
作者：{paper['authors']}
年份：{paper['year']}
来源：{paper['source']}
标签：{paper['tags']}
摘要速览：{paper['short_summary']}
关键要点：{paper['key_points']}
深度解读：{paper['deep_summary']}
局限：{paper['limitations']}
""".strip()
        )
    return f"""
请基于下面这些论文，写一篇中文文献综述草稿，主题是：{topic}

写作要求：
1. 输出 Markdown。
2. 结构包含：标题、摘要式导言、研究背景、方法脉络、代表性工作对比、现有不足、未来研究方向、参考论文索引。
3. 每个关键观点后用 [P1]、[P2] 这样的编号标注依据。
4. 不要编造论文中没有的信息。没有证据时写“从所给信息暂不能判断”。
5. 不要把摘要机械拼接，要综合比较这些论文之间的共同点和差异。
6. 语气要像论文相关工作初稿，便于后续人工改写。

论文材料：

{chr(10).join(paper_blocks)}
""".strip()


def _post_json(url: str, payload: dict, token: str) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "x-api-key": token,
        "anthropic-version": ANTHROPIC_VERSION,
        "User-Agent": "timepredict-agent/0.3",
    }
    if "api.anthropic.com" not in url:
        headers["authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM 请求失败：HTTP {exc.code} {detail}") from exc
    except (URLError, TimeoutError) as exc:
        if "SSL" not in str(exc):
            raise RuntimeError(f"LLM 请求失败：{exc!r}") from exc
        context = ssl._create_unverified_context()
        try:
            with urlopen(request, timeout=90, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError) as retry_exc:
            return _post_json_with_curl(url, payload, token, retry_exc)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM 返回不是合法 JSON：{exc}") from exc


def _message_text(response: dict) -> str:
    if isinstance(response.get("content"), str):
        return response["content"].strip()
    if response.get("completion"):
        return str(response["completion"]).strip()
    if response.get("text"):
        return str(response["text"]).strip()
    parts = response.get("content") or []
    return "\n".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()


def _post_json_with_curl(url: str, payload: dict, token: str, cause: Exception) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp:
            temp.write(body)
            temp_name = temp.name
        command = [
            "curl.exe",
            "-sS",
            url,
            "-H",
            "content-type: application/json",
            "-H",
            f"anthropic-version: {ANTHROPIC_VERSION}",
            "-H",
            f"x-api-key: {token}",
            "-H",
            f"authorization: Bearer {token}",
            "--data-binary",
            f"@{temp_name}",
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"curl fallback failed: {completed.stderr.strip()}")
        response = json.loads(completed.stdout)
        if response.get("error"):
            raise RuntimeError(f"LLM 请求失败：{response['error']}")
        return response
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError) as exc:
        raise RuntimeError(f"LLM 请求失败：{cause!r}; curl 兜底也失败：{exc}") from exc
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def _safe_max_tokens() -> int:
    raw = environ.get("TIMEPREDICT_LLM_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
    try:
        requested = int(raw)
    except (TypeError, ValueError):
        requested = DEFAULT_MAX_TOKENS
    return min(max(DEFAULT_MAX_TOKENS, requested), HARD_MAX_TOKENS)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            if text.strip().startswith("{"):
                salvaged = _salvage_json_like_text(text)
                if salvaged:
                    return salvaged
            return _fallback_from_text(text)
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            salvaged = _salvage_json_like_text(match.group(0))
            return salvaged or _fallback_from_text(text)


def _fallback_from_text(text: str) -> dict:
    cleaned = text.strip()
    if not cleaned:
        raise RuntimeError("LLM 返回为空。")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    first = paragraphs[0] if paragraphs else cleaned[:260]
    return {
        "short_summary": first[:260],
        "deep_summary": cleaned,
        "reading_notes": "模型返回了非 JSON 格式内容，已作为完整中文讲解保存。",
        "reading_priority": "medium",
    }


def _salvage_json_like_text(text: str) -> dict:
    fields = [
        "short_summary",
        "relevance",
        "reading_priority",
        "deep_summary",
        "contribution",
        "method",
        "experiments",
        "limitations",
        "reading_notes",
    ]
    result: dict[str, object] = {}
    for field in fields:
        value = _extract_string_field(text, field)
        if value:
            result[field] = value
    for field in ("key_points", "method_tags", "topic_tags"):
        values = _extract_array_field(text, field)
        if values:
            result[field] = values
    if result:
        if "deep_summary" not in result and result.get("short_summary"):
            points = result.get("key_points") if isinstance(result.get("key_points"), list) else []
            result["deep_summary"] = _compose_salvaged_deep_summary(
                str(result["short_summary"]),
                [str(point) for point in points],
            )
        result.setdefault("reading_notes", "模型返回的 JSON 不完整，已尽量提取可用字段。")
    return result


def _extract_string_field(text: str, field: str) -> str:
    match = re.search(rf'"{field}"\s*:\s*"((?:\\.|[^"\\])*)"', text, re.S)
    if not match:
        return ""
    return _decode_json_fragment(match.group(1)).strip()


def _extract_array_field(text: str, field: str) -> list[str]:
    match = re.search(rf'"{field}"\s*:\s*\[(.*?)\]', text, re.S)
    if not match:
        return []
    return [
        _decode_json_fragment(item).strip()
        for item in re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))
        if item.strip()
    ]


def _decode_json_fragment(value: str) -> str:
    if "\\" not in value:
        return value
    return bytes(value, "utf-8").decode("unicode_escape", errors="ignore")


def _compose_salvaged_deep_summary(short_summary: str, points: list[str]) -> str:
    if not points:
        return short_summary
    return short_summary + "\n\n关键理解：\n" + "\n".join(f"- {point}" for point in points[:6])


def _merge_summary(current: PaperSummary, parsed: dict, model: str) -> PaperSummary:
    return replace(
        current,
        short_summary=str(parsed.get("short_summary") or current.short_summary),
        key_points=_string_list(parsed.get("key_points")) or current.key_points,
        method_tags=_string_list(parsed.get("method_tags")) or current.method_tags,
        topic_tags=_string_list(parsed.get("topic_tags")) or current.topic_tags,
        relevance=str(parsed.get("relevance") or current.relevance),
        reading_priority=_priority(parsed.get("reading_priority") or current.reading_priority),
        deep_summary=str(parsed.get("deep_summary") or ""),
        contribution=str(parsed.get("contribution") or ""),
        method=str(parsed.get("method") or ""),
        experiments=str(parsed.get("experiments") or ""),
        limitations=str(parsed.get("limitations") or ""),
        reading_notes=str(parsed.get("reading_notes") or ""),
        llm_model=model,
        llm_error="",
        innovation_points=_string_list(parsed.get("innovation_points")),
        method_comparison=str(parsed.get("method_comparison") or ""),
        datasets_used=_string_list(parsed.get("datasets_used")),
        metrics_used=_string_list(parsed.get("metrics_used")),
        future_directions=str(parsed.get("future_directions") or ""),
    )


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _priority(value) -> str:
    value = str(value).lower().strip()
    return value if value in {"high", "medium", "low"} else "medium"


def load_local_env(root: Path | None = None) -> None:
    root = root or Path.cwd()
    for name in (".env", ".env.local"):
        path = root / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in environ:
                environ[key] = value
