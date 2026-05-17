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
                "你是人工智能、深度学习、多模态大模型、强化学习、时间序列预测和业务过程预测方向的研究助理。"
                "请先根据论文标题和摘要判断真实研究领域，再用简体中文帮助研究者深入理解论文。"
                "不要把不属于时间序列/流程预测的论文硬套进时间序列模板。"
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
        response = self._post_messages(payload)
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
        response = self._post_messages(payload)
        text = _message_text(response)
        if not text:
            raise RuntimeError("LLM 返回为空。")
        return text.strip()

    def answer_paper_question(
        self,
        paper: Paper,
        summary: PaperSummary,
        pdf_text: str,
        question: str,
        repositories: list[dict] | None = None,
        history: list[dict] | None = None,
        memory: list[dict] | None = None,
    ) -> str:
        if not self.available():
            raise RuntimeError("未检测到 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY。")

        system_prompt = (
            "你是深度学习和人工智能论文导师。请用简体中文回答用户关于单篇论文的问题。"
            "回答要能让用户不翻正文也尽量理解论文：必须解释方法思想、具体流程、创新点、与已有方法对比、实验设计和结果含义。"
            "只根据给定论文信息和 GitHub 仓库信息作答；信息缺失时明确说缺失，不要编造指标、数据集或结论。"
            "不要输出思考过程。"
        )
        if memory:
            memory_notes = []
            for item in memory[:5]:
                kind = item.get("kind", "")
                key = item.get("key", "")
                if kind == "feedback":
                    memory_notes.append(f"- 用户反馈偏好：{key}")
                elif kind == "preference":
                    memory_notes.append(f"- 用户偏好：{key}")
            if memory_notes:
                system_prompt += "\n\n用户历史反馈和偏好（请在回答中参考）：\n" + "\n".join(memory_notes)

        payload = {
            "model": self.model,
            "max_tokens": _safe_max_tokens(),
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": _build_expert_prompt(paper, summary, pdf_text, question, repositories or [], history or [], memory or []),
                }
            ],
        }
        response = self._post_messages(payload)
        text = _message_text(response)
        if not text:
            raise RuntimeError("LLM 返回为空。")
        return text.strip()

    def classify_intent(self, question: str) -> dict[str, bool] | None:
        if not self.available():
            return None
        try:
            payload = {
                "model": self.model,
                "max_tokens": 200,
                "temperature": 0,
                "system": "你是一个意图分类器。根据用户问题，返回 JSON 格式的意图分类。只返回 JSON，不要其他文字。",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"用户问题：{question}\n\n"
                            "请判断这个问题属于以下哪些意图（true/false）：\n"
                            "- concept: 询问概念定义、术语含义\n"
                            "- method: 询问方法流程、模型架构、技术细节\n"
                            "- experiment: 询问实验设置、数据集、指标、结果\n"
                            "- innovation: 询问创新点、贡献、改进\n"
                            "- comparison: 询问与其他方法的对比、区别\n"
                            "- direction: 询问研究方向、未来工作、选题建议\n"
                            "- code: 需要代码实现、复现、GitHub仓库\n\n"
                            '返回格式：{"concept":bool,"method":bool,"experiment":bool,"innovation":bool,"comparison":bool,"direction":bool,"code":bool}'
                        ),
                    }
                ],
            }
            response = self._post_messages(payload)
            text = _message_text(response).strip()
            import json as _json
            import re as _re
            match = _re.search(r'\{[^}]+\}', text)
            if match:
                result = _json.loads(match.group())
                return {
                    "concept": bool(result.get("concept", False)),
                    "method": bool(result.get("method", False)),
                    "experiment": bool(result.get("experiment", False)),
                    "innovation": bool(result.get("innovation", False)),
                    "comparison": bool(result.get("comparison", False)),
                    "direction": bool(result.get("direction", False)),
                    "code": bool(result.get("code", False)),
                }
        except Exception:
            pass
        return None

    def plan_agent_tasks(
        self,
        question: str,
        paper_title: str,
        intent: dict[str, bool] | None = None,
    ) -> list[dict] | None:
        if not self.available():
            return None
        intent_str = ""
        if intent:
            active = [k for k, v in intent.items() if v]
            if active:
                intent_str = f"用户意图涵盖：{', '.join(active)}"
        try:
            payload = {
                "model": self.model,
                "max_tokens": 400,
                "temperature": 0.1,
                "system": (
                    "你是一个论文研究任务规划器。根据用户问题和论文信息，生成一个有序的子任务列表。"
                    "每个子任务包含 step（步骤描述）和 tools（需要的工具列表）。"
                    '只返回 JSON 数组，格式：[{"step":"...","tools":["..."]}]'
                ),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"论文：{paper_title}\n"
                            f"用户问题：{question}\n"
                            f"{intent_str}\n\n"
                            "请规划 3-6 个子任务来回答这个问题。工具可选：read_paper, search_github, analyze_method, compare_results, summarize, reflect"
                        ),
                    }
                ],
            }
            response = self._post_messages(payload)
            text = _message_text(response).strip()
            match = re.search(r'\[.*\]', text, re.S)
            if match:
                tasks = json.loads(match.group())
                if isinstance(tasks, list):
                    return tasks[:8]
        except Exception:
            pass
        return None

    def reflect_on_answer(
        self,
        question: str,
        answer: str,
        paper_title: str,
    ) -> dict | None:
        if not self.available():
            return None
        try:
            payload = {
                "model": self.model,
                "max_tokens": 500,
                "temperature": 0.1,
                "system": (
                    "你是一个论文回答质量评审员。评估回答的质量并指出不足。"
                    '返回 JSON，格式：{"score":0-10,"strengths":["..."],"weaknesses":["..."],"suggestions":["..."]}'
                ),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"论文：{paper_title}\n"
                            f"用户问题：{question}\n\n"
                            f"回答：\n{answer[:4000]}\n\n"
                            "请评估这个回答：完整性、准确性、清晰度、是否直接回答了用户问题。"
                        ),
                    }
                ],
            }
            response = self._post_messages(payload)
            text = _message_text(response).strip()
            match = re.search(r'\{.*\}', text, re.S)
            if match:
                result = json.loads(match.group())
                return {
                    "score": min(10, max(0, int(result.get("score", 5)))),
                    "strengths": _string_list(result.get("strengths")),
                    "weaknesses": _string_list(result.get("weaknesses")),
                    "suggestions": _string_list(result.get("suggestions")),
                }
        except Exception:
            pass
        return None

    def analyze_paper_structure(self, paper_title: str, abstract: str, pdf_text: str) -> dict | None:
        """分析论文结构，提取章节组织方式"""
        if not self.available():
            return None

        try:
            prompt = f"""请分析以下论文的结构：

标题：{paper_title}
摘要：{abstract}
全文（前 10000 字符）：{pdf_text[:10000]}

请提取：
1. 章节结构（标题和层级）
2. 每个章节的核心内容和论证方式
3. 段落组织模式
4. 引用使用方式
5. 图表使用特点

输出 JSON 格式：
{{
  "sections": [
    {{
      "title": "章节标题",
      "level": 1,
      "content_type": "introduction|method|experiment|conclusion|other",
      "paragraph_count": 3,
      "description": "章节核心内容"
    }}
  ],
  "writing_style": "学术论文风格描述",
  "citation_pattern": "引用方式描述",
  "figure_usage": "图表使用方式"
}}"""

            payload = {
                "model": self.model,
                "max_tokens": 2000,
                "temperature": 0.2,
                "system": "你是学术论文结构分析专家。请分析论文结构并输出 JSON 格式。",
                "messages": [{"role": "user", "content": prompt}]
            }

            response = self._post_messages(payload)
            text = _message_text(response).strip()

            match = re.search(r'\{.*\}', text, re.S)
            if match:
                return json.loads(match.group())

            return None
        except Exception as e:
            print(f"Error analyzing paper structure: {e}")
            return None

    def generate_paper_content(self, structure: dict, topic: str, outline: list[str], code: str = "") -> dict | None:
        """基于结构模板生成论文内容"""
        if not self.available():
            return None

        try:
            sections_desc = "\n".join([
                f"- {s['title']} ({s.get('content_type', 'other')})"
                for s in structure.get('sections', [])
            ])

            outline_desc = "\n".join([f"- {item}" for item in outline])

            prompt = f"""基于以下结构模板和用户输入，生成一篇论文：

结构模板：
{sections_desc}

写作风格：{structure.get('writing_style', '学术论文风格')}

用户输入：
主题：{topic}
大纲要点：
{outline_desc}

{f"代码片段：{code}" if code else ""}

请按照模板结构生成完整论文内容，保持学术论文的严谨性和逻辑性。
每个章节需要详细展开，包含足够的技术细节。
输出 Markdown 格式。"""

            payload = {
                "model": self.model,
                "max_tokens": 8000,
                "temperature": 0.3,
                "system": "你是学术论文写作专家。请根据给定的结构模板和主题生成高质量的学术论文内容。",
                "messages": [{"role": "user", "content": prompt}]
            }

            response = self._post_messages(payload)
            text = _message_text(response).strip()

            if not text:
                return None

            return {
                "content": text,
                "format": "markdown",
                "topic": topic
            }
        except Exception as e:
            print(f"Error generating paper content: {e}")
            return None

    def _post_messages(self, anthropic_payload: dict) -> dict:
        if _uses_openai_chat_format(self.base_url):
            payload = _to_openai_chat_payload(anthropic_payload)
            return _post_json(
                _join_endpoint(self.base_url, "chat/completions"),
                payload,
                self.token,
                api_format="openai",
            )
        return _post_json(
            _join_endpoint(self.base_url, "v1/messages"),
            anthropic_payload,
            self.token,
            api_format="anthropic",
        )


def _build_prompt(paper: Paper, current: PaperSummary, pdf_text: str = "") -> str:
    authors = ", ".join(paper.authors[:8])
    pdf_section = ""
    if pdf_text:
        pdf_section = f"\n\n论文全文（前 15000 字符）：\n{pdf_text[:15000]}"
    return f"""
请阅读下面的论文元数据和摘要，先判断它真实属于哪个研究方向，再生成中文深度解读。

如果论文属于多模态大模型、LLM、强化学习、计算机视觉、NLP、机器人、可供性推理等方向，请按这些方向解释；不要强行写成时间序列预测或业务过程预测论文。

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
- relevance: 详细说明它和用户研究方向的关系。如果它不是时间序列/流程预测论文，要明确说明“直接关系不强”，同时指出它作为 AI/深度学习方法背景的启发
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


def _build_expert_prompt(
    paper: Paper,
    summary: PaperSummary,
    pdf_text: str,
    question: str,
    repositories: list[dict],
    history: list[dict] | None = None,
    memory: list[dict] | None = None,
) -> str:
    authors = ", ".join(paper.authors[:8])
    repo_lines = []
    for repo in repositories[:6]:
        repo_lines.append(
            "- {name} | {url} | {language} | stars={stars} | {description} | {reason}".format(
                name=repo.get("full_name", ""),
                url=repo.get("html_url", ""),
                language=repo.get("language", ""),
                stars=repo.get("stars", 0),
                description=repo.get("description", ""),
                reason=repo.get("reason", ""),
            )
        )
    pdf_section = f"\n\n全文片段（前 18000 字符）：\n{pdf_text[:18000]}" if pdf_text else ""
    history_lines = []
    for turn in (history or [])[-6:]:
        user_text = str(turn.get("question") or "").strip()
        answer_text = str(turn.get("answer") or "").strip()
        if user_text:
            history_lines.append(f"用户：{user_text}")
        if answer_text:
            history_lines.append(f"专家：{answer_text[:800]}")
    history_section = f"\n\n最近对话：\n{chr(10).join(history_lines)}" if history_lines else ""
    memory_section = ""
    if memory:
        memory_lines = []
        for item in memory[:5]:
            kind = item.get("kind", "")
            key = item.get("key", "")
            value = item.get("value", {})
            if kind == "feedback":
                note = value.get("note", key)
                memory_lines.append(f"- 用户反馈：{note}")
            elif kind == "preference":
                memory_lines.append(f"- 用户偏好：{key}（权重 {item.get('weight', 1)}）")
        if memory_lines:
            memory_section = f"\n\n用户偏好记忆：\n{chr(10).join(memory_lines)}"
    return f"""
用户问题：{question}

请按下面结构回答：
1. 先用 2-3 句话回答用户最关心的问题。
2. 方法思想：解释这篇论文想解决什么问题、核心直觉是什么。
3. 具体怎么做：按输入、模型/模块、训练目标、推理流程拆开讲。
4. 创新点：逐条说明相对已有方法哪里不同。
5. 对比实验和结果：说明数据集、指标、基线、主要结果、消融或泛化结论；缺失就明确写“当前材料未提供”。
6. GitHub/复现建议：如果给了仓库，说明每个仓库可能能参考什么；不要保证它一定是官方代码，除非信息里能证明。
7. 读者建议：告诉用户是否值得细读、重点看哪些部分。

论文标题：{paper.title}
作者：{authors}
来源：{paper.source}
发表时间：{paper.published}
venue：{paper.venue}
摘要：{paper.abstract}

已有中文解读：
短摘要：{summary.short_summary}
关键要点：{"；".join(summary.key_points)}
方法标签：{", ".join(summary.method_tags)}
主题标签：{", ".join(summary.topic_tags)}
深度总结：{summary.deep_summary}
主要贡献：{summary.contribution}
方法拆解：{summary.method}
创新点：{"；".join(summary.innovation_points)}
方法对比：{summary.method_comparison}
实验结论：{summary.experiments}
数据集：{", ".join(summary.datasets_used)}
评价指标：{", ".join(summary.metrics_used)}
局限：{summary.limitations}

GitHub 候选仓库：
{chr(10).join(repo_lines) if repo_lines else "未检索到或用户未要求检索。"}{history_section}{memory_section}{pdf_section}
""".strip()


def _uses_openai_chat_format(base_url: str) -> bool:
    lowered = str(base_url or "").rstrip("/").lower()
    if "api.deepseek.com" in lowered and not lowered.endswith("/anthropic"):
        return True
    return bool(environ.get("OPENAI_API_KEY") and "api.openai.com" in lowered)


def _join_endpoint(base_url: str, endpoint: str) -> str:
    return f"{str(base_url).rstrip('/')}/{endpoint.lstrip('/')}"


def _to_openai_chat_payload(anthropic_payload: dict) -> dict:
    messages = []
    system = str(anthropic_payload.get("system") or "").strip()
    if system:
        messages.append({"role": "system", "content": system})
    for message in anthropic_payload.get("messages") or []:
        role = message.get("role") or "user"
        content = message.get("content") or ""
        messages.append({"role": role, "content": content})
    payload = {
        "model": anthropic_payload.get("model"),
        "messages": messages,
        "temperature": anthropic_payload.get("temperature", 0.2),
        "max_tokens": anthropic_payload.get("max_tokens", _safe_max_tokens()),
        "stream": False,
    }
    return {key: value for key, value in payload.items() if value is not None}


def _post_json(url: str, payload: dict, token: str, api_format: str = "anthropic") -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"content-type": "application/json", "User-Agent": "timepredict-agent/0.4"}
    if api_format == "openai":
        headers["authorization"] = f"Bearer {token}"
    else:
        headers["x-api-key"] = token
        headers["anthropic-version"] = ANTHROPIC_VERSION
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
            return _post_json_with_curl(url, payload, token, retry_exc, api_format=api_format)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM 返回不是合法 JSON：{exc}") from exc


def _message_text(response: dict) -> str:
    choices = response.get("choices") or []
    if choices:
        first = choices[0] or {}
        message = first.get("message") or {}
        if message.get("content"):
            return str(message["content"]).strip()
        if first.get("text"):
            return str(first["text"]).strip()
    if isinstance(response.get("content"), str):
        return response["content"].strip()
    if response.get("completion"):
        return str(response["completion"]).strip()
    if response.get("text"):
        return str(response["text"]).strip()
    parts = response.get("content") or []
    return "\n".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()


def _post_json_with_curl(
    url: str,
    payload: dict,
    token: str,
    cause: Exception,
    api_format: str = "anthropic",
) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp:
            temp.write(body)
            temp_name = temp.name
        headers = [
            "content-type: application/json",
        ]
        if api_format == "openai":
            headers.append(f"authorization: Bearer {token}")
        else:
            headers.extend(
                [
                    f"anthropic-version: {ANTHROPIC_VERSION}",
                    f"x-api-key: {token}",
                    f"authorization: Bearer {token}",
                ]
            )
        command = [
            "curl.exe",
            "-sS",
            url,
        ]
        for header in headers:
            command.extend(["-H", header])
        command.extend(["--data-binary", f"@{temp_name}"])
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
