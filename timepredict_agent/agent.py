from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
import re

from .config import AgentConfig
from .citation import CitationService
from .fulltext import PdfDownloader, PdfTextExtractor
from .llm_summary import AnthropicSummaryClient
from .models import Paper, SourceResult
from .sources import build_sources
from .storage import PaperStore, decode_json_field, decode_json_object, decode_summary
from .summarizer import ExtractiveSummarizer
from .tagger import classify_paper


@dataclass(frozen=True)
class CollectResult:
    fetched: int
    saved: int
    sources: dict[str, int] | None = None
    errors: dict[str, str] | None = None


class PaperAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.summarizer = ExtractiveSummarizer()
        self.store = PaperStore(config.database_path)
        self.downloader = PdfDownloader(config.pdf_dir)
        self.pdf_extractor = PdfTextExtractor()
        self.citations = CitationService()
        self.llm = AnthropicSummaryClient()

    def close(self) -> None:
        self.store.close()

    def collect(
        self,
        query: str | None = None,
        max_results: int | None = None,
        recent_days: int | None = None,
    ) -> CollectResult:
        base_query = query or self.config.query
        total_limit = max_results or self.config.max_results
        source_results = []
        for source in build_sources(self.config.sources):
            queries = _queries_for_source(source.name, base_query, explicit_query=query is not None)
            per_query_limit = max(3, ceil(total_limit / max(1, len(queries))))
            combined = []
            error_messages = []
            seen_ids: set[str] = set()
            for search_query in queries:
                try:
                    result = source.search(
                        query=search_query,
                        max_results=per_query_limit,
                        recent_days=recent_days if recent_days is not None else self.config.recent_days,
                    )
                except Exception as exc:
                    error_messages.append(str(exc))
                    continue
                if result.error:
                    error_messages.append(result.error)
                for paper in result.papers:
                    key = _dedupe_key(paper)
                    if key in seen_ids:
                        continue
                    seen_ids.add(key)
                    combined.append(paper)
                    if len(combined) >= total_limit:
                        break
                if len(combined) >= total_limit:
                    break
            source_results.append(
                SourceResult(source.name, combined, "；".join(dict.fromkeys(error_messages)))
            )
        papers = []
        per_source: dict[str, int] = {}
        errors: dict[str, str] = {}
        for result in source_results:
            per_source[result.source] = len(result.papers)
            if result.error:
                errors[result.source] = result.error
            papers.extend(result.papers)
        saved = 0
        seen: set[str] = set()
        for paper in papers:
            dedupe_key = _dedupe_key(paper)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            summary = self.summarizer.summarize(paper)
            summary = type(summary)(
                short_summary=summary.short_summary,
                key_points=summary.key_points,
                method_tags=summary.method_tags,
                relevance=summary.relevance,
                reading_priority=summary.reading_priority,
                topic_tags=classify_paper(paper),
                deep_summary=summary.deep_summary,
                contribution=summary.contribution,
                method=summary.method,
                experiments=summary.experiments,
                limitations=summary.limitations,
                reading_notes=summary.reading_notes,
            )
            if self.store.upsert_paper(paper, summary):
                saved += 1
        return CollectResult(fetched=len(papers), saved=saved, sources=per_source, errors=errors)

    def download_fulltext(self, paper_id: str) -> Path:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        path = self.downloader.download(row["pdf_url"], paper_id)
        self.store.update_download_path(paper_id, str(path))
        pdf_text = self.pdf_extractor.extract_text(path)
        if pdf_text:
            self.store.update_pdf_text(paper_id, pdf_text)
        return path

    def enrich_citations(self, paper_id: str) -> None:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        summary = self.citations.fetch_for_row(row)
        self.store.update_citation_data(
            paper_id,
            summary.citation_count,
            summary.reference_count,
            summary.influential_citation_count,
            [item.__dict__ for item in summary.citations],
            [item.__dict__ for item in summary.references],
        )

    def recommend_similar(self, paper_id: str, limit: int = 8) -> list[dict]:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        recommendations = self.citations.recommend_from_semantic_scholar(row, limit)
        if not recommendations:
            recommendations = self._local_recommendations(row, limit)
        payload = [item.__dict__ for item in recommendations]
        self.store.update_related_papers(paper_id, payload)
        return payload

    def generate_llm_summary(self, paper_id: str) -> dict:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        paper = _paper_from_row(row)
        current = decode_summary(row)
        pdf_text = row["pdf_text"] or ""
        if not pdf_text and row["local_pdf_path"]:
            pdf_path = Path(row["local_pdf_path"])
            if pdf_path.exists():
                pdf_text = self.pdf_extractor.extract_text(pdf_path)
                if pdf_text:
                    self.store.update_pdf_text(paper_id, pdf_text)
        summary = self.llm.summarize(paper, current, pdf_text)
        self.store.update_summary(paper_id, summary)
        updated = self.store.find_paper(paper_id)
        return {
            "paper_id": paper_id,
            "model": summary.llm_model,
            "summary": summary.__dict__,
            "paper": updated,
        }

    def refresh_local_summary(self, paper_id: str) -> dict:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        paper = _paper_from_row(row)
        summary = self.summarizer.summarize(paper)
        summary = type(summary)(
            short_summary=summary.short_summary,
            key_points=summary.key_points,
            method_tags=summary.method_tags,
            relevance=summary.relevance,
            reading_priority=summary.reading_priority,
            topic_tags=classify_paper(paper),
            deep_summary=summary.deep_summary,
            contribution=summary.contribution,
            method=summary.method,
            experiments=summary.experiments,
            limitations=summary.limitations,
            reading_notes=summary.reading_notes,
        )
        self.store.update_summary(paper_id, summary)
        return {"paper_id": paper_id, "summary": summary.__dict__, "paper": self.store.find_paper(paper_id)}

    def add_manual_paper(self, payload: dict) -> object:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("论文标题不能为空。")
        abstract = str(payload.get("abstract") or "").strip()
        if not abstract:
            abstract = "用户手动加入的已读论文，暂未填写摘要。"

        year = _optional_year(payload.get("year"))
        published = f"{year}-01-01T00:00:00Z" if year else datetime.now(timezone.utc).isoformat()
        authors = _split_people(payload.get("authors"))
        tags = _split_tags(payload.get("tags"))
        doi = str(payload.get("doi") or "").strip()
        paper_id = str(payload.get("paper_id") or "").strip() or _manual_paper_id(title, doi)

        paper = Paper(
            arxiv_id=paper_id,
            title=title,
            abstract=abstract,
            authors=authors,
            published=published,
            updated=published,
            entry_url=str(payload.get("entry_url") or "").strip(),
            pdf_url=str(payload.get("pdf_url") or "").strip(),
            categories=[],
            source="manual",
            source_id=paper_id,
            doi=doi,
            venue=str(payload.get("venue") or "").strip(),
            year=year,
            external_ids={"DOI": doi} if doi else {},
        )
        summary = self.summarizer.summarize(paper)
        topic_tags = _dedupe_list([*classify_paper(paper), "已读", "手动加入", *tags])
        summary = type(summary)(
            short_summary=summary.short_summary,
            key_points=summary.key_points,
            method_tags=summary.method_tags,
            relevance=summary.relevance,
            reading_priority=summary.reading_priority,
            topic_tags=topic_tags,
            deep_summary=summary.deep_summary,
            contribution=summary.contribution,
            method=summary.method,
            experiments=summary.experiments,
            limitations=summary.limitations,
            reading_notes=summary.reading_notes,
        )
        self.store.upsert_paper(paper, summary)
        return self.store.find_paper(paper_id)

    def generate_literature_review(
        self,
        paper_ids: list[str],
        topic: str = "事件序列预测与预测性流程监控",
        prefer_llm: bool = True,
    ) -> dict:
        rows = []
        missing = []
        for paper_id in paper_ids:
            row = self.store.find_paper(paper_id)
            if row is None:
                missing.append(paper_id)
            else:
                rows.append(row)
        if len(rows) < 2:
            raise ValueError("请至少选择 2 篇已收录论文来生成综述。")

        briefs = [_review_brief(row, index) for index, row in enumerate(rows, 1)]
        used_llm = False
        error = ""
        if prefer_llm and self.llm.available():
            try:
                markdown = self.llm.write_literature_review(briefs, topic)
                used_llm = True
            except RuntimeError as exc:
                error = str(exc)
                markdown = _local_literature_review(briefs, topic)
        else:
            markdown = _local_literature_review(briefs, topic)

        output = self.config.report_dir / "literature_review.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        return {
            "paper_count": len(rows),
            "missing": missing,
            "topic": topic,
            "used_llm": used_llm,
            "llm_error": error,
            "markdown": markdown,
            "path": str(output),
            "url": f"/{output.as_posix()}",
        }

    def export_markdown(self, output_path: Path, limit: int = 50) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.store.list_papers(limit)
        lines = [
            "# Time Series Forecasting Papers",
            "",
            f"导出论文数：{len(rows)}",
            "",
        ]
        for index, row in enumerate(rows, 1):
            summary = decode_summary(row)
            authors = ", ".join(decode_json_field(row, "authors_json")[:6])
            categories = ", ".join(decode_json_field(row, "categories_json"))
            tags = ", ".join(decode_json_object(row, "tags_json", []))
            lines.extend(
                [
                    f"## {index}. {row['title']}",
                    "",
                    f"- ID: `{row['arxiv_id']}`",
                    f"- Source: `{row['source']}`",
                    f"- Published: `{row['published'][:10]}`",
                    f"- Authors: {authors}",
                    f"- Categories: {categories}",
                    f"- Tags: {tags}",
                    f"- Priority: `{summary.reading_priority}`",
                    f"- Citations: `{row['citation_count'] or 0}`",
                    f"- PDF: {row['pdf_url']}",
                    "",
                    f"**摘要速览**：{summary.short_summary}",
                    "",
                    f"**相关性判断**：{summary.relevance}",
                    "",
                    "**要点**：",
                ]
            )
            for point in summary.key_points:
                lines.append(f"- {point}")
            if summary.deep_summary:
                lines.extend(["", f"**深度总结**：{summary.deep_summary}"])
            if summary.innovation_points:
                lines.extend(["", "**创新点**："])
                for point in summary.innovation_points:
                    lines.append(f"- {point}")
            if summary.method_comparison:
                lines.extend(["", f"**方法对比**：{summary.method_comparison}"])
            if summary.datasets_used:
                lines.extend(["", f"**数据集**：{', '.join(summary.datasets_used)}"])
            if summary.metrics_used:
                lines.extend(["", f"**评价指标**：{', '.join(summary.metrics_used)}"])
            if summary.limitations:
                lines.extend(["", f"**局限性**：{summary.limitations}"])
            if summary.future_directions:
                lines.extend(["", f"**未来方向**：{summary.future_directions}"])
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    def _local_recommendations(self, row, limit: int) -> list:
        from .models import RelatedPaper

        target_tags = set(decode_json_object(row, "tags_json", []))
        target_words = set(_title_words(row["title"]))
        scored = []
        for candidate in self.store.list_papers(200):
            if candidate["arxiv_id"] == row["arxiv_id"]:
                continue
            tags = set(decode_json_object(candidate, "tags_json", []))
            words = set(_title_words(candidate["title"]))
            score = len(target_tags & tags) * 2 + len(target_words & words)
            if score:
                scored.append((score, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RelatedPaper(
                title=candidate["title"],
                source=candidate["source"],
                url=candidate["entry_url"],
                reason="本地标签和标题关键词相似",
                score=float(score),
            )
            for score, candidate in scored[:limit]
        ]


def _dedupe_key(paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.external_ids.get("ArXiv"):
        return f"arxiv:{paper.external_ids['ArXiv'].lower()}"
    return f"title:{paper.title.lower()}"


def _queries_for_source(source_name: str, base_query: str, explicit_query: bool) -> list[str]:
    if explicit_query or source_name in {"arxiv", "google_scholar"}:
        return [base_query]
    focused = [
        "event sequence prediction",
        "next event prediction process mining",
        "next activity prediction event log",
        "predictive process monitoring",
        "remaining time prediction process mining",
        "business process remaining time prediction",
        "incremental event log prediction",
        "process mining event sequence transformer",
    ]
    if source_name == "semantic_scholar":
        focused = focused[:3]
    return [base_query, *focused]


def _title_words(title: str) -> list[str]:
    stop = {"the", "a", "an", "for", "and", "or", "with", "using", "of", "in", "on"}
    return [
        word
        for word in re.findall(r"[a-z0-9]+", title.lower())
        if len(word) > 3 and word not in stop
    ]


def _manual_paper_id(title: str, doi: str = "") -> str:
    if doi:
        return f"manual:doi:{_safe_token(doi)}"
    return f"manual:{_safe_token(title)}"


def _safe_token(value: str) -> str:
    value = re.sub(r"^https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9._:-]+", "-", value)
    return value.strip("-")[:120] or "paper"


def _optional_year(value) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not re.fullmatch(r"\d{4}", text):
        raise ValueError("年份必须是 4 位数字，例如 2024。")
    return int(text)


def _split_people(value) -> list[str]:
    text = str(value or "")
    return [item.strip() for item in re.split(r"[,;，；]", text) if item.strip()]


def _split_tags(value) -> list[str]:
    text = str(value or "")
    return [item.strip() for item in re.split(r"[,;，；\n]", text) if item.strip()]


def _dedupe_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _paper_from_row(row) -> object:
    from .models import Paper

    return Paper(
        arxiv_id=row["arxiv_id"],
        title=row["title"],
        abstract=row["abstract"],
        authors=decode_json_field(row, "authors_json"),
        published=row["published"],
        updated=row["updated"],
        entry_url=row["entry_url"],
        pdf_url=row["pdf_url"],
        categories=decode_json_field(row, "categories_json"),
        source=row["source"],
        source_id=row["source_id"],
        doi=row["doi"],
        venue=row["venue"],
        year=row["year"],
        citation_count=row["citation_count"],
        reference_count=row["reference_count"],
        external_ids=decode_json_object(row, "external_ids_json", {}),
        fields_of_study=decode_json_object(row, "fields_of_study_json", []),
    )


def _review_brief(row, index: int) -> dict:
    summary = decode_summary(row)
    authors = ", ".join(decode_json_field(row, "authors_json")[:6])
    tags = ", ".join(decode_json_object(row, "tags_json", []))
    year = row["year"] or (row["published"][:4] if row["published"] else "")
    deep_summary = summary.deep_summary or summary.contribution or summary.method or ""
    return {
        "index": index,
        "id": row["arxiv_id"],
        "title": row["title"],
        "authors": authors,
        "year": year,
        "source": row["source"],
        "url": row["entry_url"],
        "tags": tags,
        "short_summary": summary.short_summary,
        "key_points": "；".join(summary.key_points[:6]),
        "deep_summary": deep_summary,
        "limitations": summary.limitations,
        "method_tags": summary.method_tags,
        "topic_tags": summary.topic_tags,
    }


def _local_literature_review(papers: list[dict], topic: str) -> str:
    tag_groups: dict[str, list[str]] = {}
    for paper in papers:
        for tag in list(paper.get("method_tags") or []) + list(paper.get("topic_tags") or []):
            tag_groups.setdefault(tag, []).append(f"P{paper['index']}")

    lines = [
        f"# {topic}文献综述草稿",
        "",
        "## 摘要式导言",
        (
            f"围绕“{topic}”，所选论文主要覆盖事件序列建模、预测性流程监控、"
            "剩余时间预测、下一事件预测以及相关的时间序列预测方法。整体来看，这些研究共同关注如何从历史观测、事件日志或多变量序列中学习可泛化的时序表示，"
            "并将模型输出用于预测、监控、风险预警或业务过程优化。"
        ),
        "",
        "## 研究背景",
        (
            "事件序列预测与预测性流程监控通常面向正在运行的案例或连续事件流，目标是在过程尚未结束时预测后续事件、剩余时间或异常风险。"
            "这类任务的难点在于事件日志具有异步、不规则、长依赖、概念漂移以及跨案例差异等特征，因此仅依赖传统统计特征往往难以充分刻画复杂过程行为。"
        ),
        "",
        "## 方法脉络",
    ]

    if tag_groups:
        for tag, refs in sorted(tag_groups.items(), key=lambda item: (-len(item[1]), item[0]))[:8]:
            lines.append(f"- **{tag}**：相关论文包括 {', '.join(sorted(set(refs)))}。")
    else:
        lines.append("- 所选论文标签信息较少，建议先对这些论文执行 LLM 深度解读以补全方法维度。")

    lines.extend(["", "## 代表性工作对比"])
    for paper in papers:
        lines.extend(
            [
                f"### [P{paper['index']}] {paper['title']}",
                f"- 作者与年份：{paper['authors'] or '未知'}，{paper['year'] or '未知年份'}",
                f"- 主要线索：{paper['short_summary']}",
                f"- 可引用点：{paper['key_points'] or '从现有摘要暂不能判断。'}",
                f"- 局限或注意事项：{paper['limitations'] or '从所给信息暂不能判断。'}",
                "",
            ]
        )

    lines.extend(
        [
            "## 现有不足",
            (
                "从所选论文看，当前研究仍需要进一步解决跨数据集泛化、长序列依赖、在线更新、概念漂移、"
                "可解释性以及真实业务场景验证不足等问题。对于事件日志场景，还需要特别关注模型是否能在增量日志中持续更新，"
                "以及预测结果是否能被业务人员理解和用于决策。"
            ),
            "",
            "## 未来研究方向",
            "- 构建面向增量事件日志的持续学习框架，降低模型重训成本。",
            "- 在剩余时间预测和下一事件预测中引入更强的过程上下文表示。",
            "- 加强模型解释性，使预测结果能对应到关键事件、瓶颈环节或异常路径。",
            "- 建立更统一的 benchmark，比较不同模型在同一事件日志和指标下的表现。",
            "",
            "## 参考论文索引",
        ]
    )
    for paper in papers:
        lines.append(f"- [P{paper['index']}] {paper['title']}。{paper['url']}")
    return "\n".join(lines)
