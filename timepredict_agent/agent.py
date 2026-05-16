from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import ceil
from pathlib import Path
import hashlib
import json
import re

from .config import AgentConfig
from .citation import CitationService
from .fulltext import PdfDownloader, PdfTextExtractor
from .github_search import GitHubRepositorySearcher
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


TOP_AI_VENUES = [
    "NeurIPS",
    "ICML",
    "ICLR",
    "CVPR",
    "ICCV",
    "ECCV",
    "ACL",
    "EMNLP",
    "NAACL",
    "AAAI",
    "IJCAI",
    "KDD",
    "SIGIR",
    "WWW",
    "WSDM",
    "JMLR",
    "TPAMI",
    "TMLR",
    "Nature",
    "Science",
]

DAILY_AI_KEYWORDS = [
    "artificial intelligence",
    "deep learning",
    "machine learning",
    "foundation model",
    "large language model",
    "multimodal",
    "computer vision",
    "natural language processing",
    "reinforcement learning",
    "generative",
    "diffusion",
    "transformer",
    "representation learning",
]


class PaperAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.summarizer = ExtractiveSummarizer()
        self.store = PaperStore(config.database_path)
        self.downloader = PdfDownloader(config.pdf_dir)
        self.pdf_extractor = PdfTextExtractor()
        self.citations = CitationService()
        self.llm = AnthropicSummaryClient()
        self.github = GitHubRepositorySearcher()

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
            summary = _summary_with_topic_tags(summary, classify_paper(paper))
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

    def generate_innovation_advice(self, paper_id: str, limit: int = 8) -> dict:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        related = decode_json_object(row, "related_json", [])
        if not related:
            related = self.recommend_similar(paper_id, limit)
        related_rows = self._rows_for_related(related)
        advice = _local_innovation_advice(row, related, related_rows)
        return {
            "paper_id": paper_id,
            "related": related,
            "advice": advice,
        }

    def ask_paper_expert(
        self,
        paper_id: str,
        question: str,
        include_github: bool = False,
        github_limit: int = 5,
        prefer_llm: bool = True,
        history: list[dict] | None = None,
    ) -> dict:
        row = self.store.find_paper(paper_id)
        if row is None:
            raise ValueError(f"Paper not found: {paper_id}")
        paper = _paper_from_row(row)
        summary = decode_summary(row)
        pdf_text = self._pdf_text_for_row(row, max_chars=30000)

        repositories = []
        github_error = ""
        if include_github or _question_needs_github(question):
            repositories = self.github.search(paper, summary, question, github_limit)
            github_error = self.github.last_error

        used_llm = False
        llm_error = ""
        if prefer_llm and self.llm.available():
            try:
                answer = self.llm.answer_paper_question(paper, summary, pdf_text, question, repositories, history or [])
                used_llm = True
            except RuntimeError as exc:
                llm_error = str(exc)
                answer = _local_expert_answer(row, summary, question, repositories, pdf_text)
        else:
            answer = _local_expert_answer(row, summary, question, repositories, pdf_text)

        return {
            "paper_id": paper_id,
            "question": question,
            "answer": answer,
            "used_llm": used_llm,
            "llm_error": llm_error,
            "github_error": github_error,
            "github_repositories": repositories,
        }

    def daily_recommendations(
        self,
        limit: int = 10,
        force: bool = False,
        today: date | None = None,
    ) -> dict:
        current_date = (today or datetime.now(timezone.utc).date()).isoformat()
        cache_path = self.config.report_dir / "daily_recommendations.json"
        if not force:
            cached = _read_daily_cache(cache_path)
            if cached.get("date") == current_date and cached.get("items"):
                cached["from_cache"] = True
                return cached

        candidates = self._fetch_daily_candidates(max(limit * 5, 30), recent_days=21)
        items = self._rank_daily_candidates(candidates, limit)
        payload = {
            "date": current_date,
            "topic": "人工智能、深度学习、机器学习、LLM、计算机视觉、NLP、强化学习",
            "from_cache": False,
            "items": items,
            "errors": [],
        }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
        pdf_text = self._pdf_text_for_row(row, max_chars=30000)
        summary = self.summarizer.summarize(paper, pdf_text)
        summary = _summary_with_topic_tags(summary, classify_paper(paper))
        self.store.update_summary(paper_id, summary)
        return {"paper_id": paper_id, "summary": summary.__dict__, "paper": self.store.find_paper(paper_id)}

    def _pdf_text_for_row(self, row, max_chars: int = 30000) -> str:
        pdf_text = row["pdf_text"] or ""
        if pdf_text:
            return pdf_text[:max_chars]
        if row["local_pdf_path"]:
            pdf_path = Path(row["local_pdf_path"])
            if pdf_path.exists():
                pdf_text = self.pdf_extractor.extract_text(pdf_path, max_chars=max_chars)
                if pdf_text:
                    self.store.update_pdf_text(row["arxiv_id"], pdf_text)
        return pdf_text[:max_chars]

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
        summary = _summary_with_topic_tags(summary, topic_tags)
        self.store.upsert_paper(paper, summary)
        return self.store.find_paper(paper_id)

    def add_uploaded_paper(self, filename: str, content: bytes, payload: dict) -> dict:
        if not content:
            raise ValueError("上传文件为空。")
        if not content.startswith(b"%PDF"):
            raise ValueError("当前只支持上传 PDF 文件。")

        digest = hashlib.sha1(content).hexdigest()[:16]
        paper_id = str(payload.get("paper_id") or "").strip() or f"upload:{digest}"
        self.config.pdf_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_token(paper_id).replace(":", "_")
        pdf_path = self.config.pdf_dir / f"{safe_name}.pdf"
        pdf_path.write_bytes(content)

        pdf_text = self.pdf_extractor.extract_text(pdf_path, max_chars=30000)
        title = str(payload.get("title") or "").strip() or _title_from_upload(filename, pdf_text)
        abstract = str(payload.get("abstract") or "").strip() or _abstract_from_upload(pdf_text)
        year = _optional_year(payload.get("year"))
        published = f"{year}-01-01T00:00:00Z" if year else datetime.now(timezone.utc).isoformat()
        authors = _split_people(payload.get("authors"))
        tags = _split_tags(payload.get("tags"))

        paper = Paper(
            arxiv_id=paper_id,
            title=title,
            abstract=abstract,
            authors=authors,
            published=published,
            updated=published,
            entry_url="",
            pdf_url="",
            categories=[],
            source="uploaded",
            source_id=paper_id,
            year=year,
        )
        summary = self.summarizer.summarize(paper, pdf_text)
        topic_tags = _dedupe_list([*classify_paper(paper), "已上传", *tags])
        summary = _summary_with_topic_tags(summary, topic_tags)
        self.store.upsert_paper(paper, summary)
        self.store.update_download_path(paper_id, str(pdf_path))
        if pdf_text:
            self.store.update_pdf_text(paper_id, pdf_text)
        related = self.recommend_similar(paper_id, 8)
        return {
            "paper": self.store.find_paper(paper_id),
            "related": related,
            "pdf_text_available": bool(pdf_text),
        }

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
        target_words = set(_paper_words(row))
        scored = []
        for candidate in self.store.list_papers(200):
            if candidate["arxiv_id"] == row["arxiv_id"]:
                continue
            tags = set(decode_json_object(candidate, "tags_json", []))
            words = set(_paper_words(candidate))
            score = len(target_tags & tags) * 3 + len(target_words & words)
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
                paper_id=candidate["arxiv_id"],
            )
            for score, candidate in scored[:limit]
        ]

    def _fetch_daily_candidates(self, max_results: int, recent_days: int) -> list[Paper]:
        candidates: list[Paper] = []
        seen: set[str] = set()
        source_names = [source for source in self.config.sources if source != "google_scholar"]
        for source in build_sources(source_names):
            queries = _daily_queries_for_source(source.name)
            per_query_limit = max(3, ceil(max_results / max(1, len(queries))))
            for query in queries:
                result = source.search(query=query, max_results=per_query_limit, recent_days=recent_days)
                for paper in result.papers:
                    key = _dedupe_key(paper)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(paper)
                    if len(candidates) >= max_results:
                        return candidates
        return candidates

    def _rank_daily_candidates(self, candidates: list[Paper], limit: int) -> list[dict]:
        scored = []
        for paper in candidates:
            score, signals = _daily_quality_score(paper)
            if score <= 0:
                continue
            scored.append((score, signals, paper))
        scored.sort(key=lambda item: item[0], reverse=True)

        items = []
        for rank, (score, signals, paper) in enumerate(scored[:limit], 1):
            summary = self.summarizer.summarize(paper)
            summary = _summary_with_topic_tags(
                summary,
                _dedupe_list([*classify_paper(paper), "每日推荐", *signals[:4]]),
                reading_priority="high" if score >= 70 else None,
            )
            self.store.upsert_paper(paper, summary)
            row = self.store.find_paper(paper.arxiv_id)
            items.append(
                {
                    "rank": rank,
                    "score": round(score, 1),
                    "quality_signals": signals,
                    "reason": _daily_recommendation_reason(paper, signals),
                    "paper": _paper_payload_from_row(row) if row is not None else _paper_payload_from_paper(paper, summary),
                }
            )
        return items

    def _rows_for_related(self, related: list[dict]) -> list:
        rows = self.store.list_papers(300)
        by_title = {row["title"].strip().lower(): row for row in rows}
        by_url = {row["entry_url"].strip(): row for row in rows if row["entry_url"]}
        matched = []
        seen: set[str] = set()
        for item in related:
            title = str(item.get("title") or "").strip().lower()
            url = str(item.get("url") or "").strip()
            row = by_title.get(title) or by_url.get(url)
            if row is None or row["arxiv_id"] in seen:
                continue
            seen.add(row["arxiv_id"])
            matched.append(row)
        return matched


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


def _daily_queries_for_source(source_name: str) -> list[str]:
    if source_name == "arxiv":
        return [
            'cat:cs.LG OR cat:cs.AI OR cat:cs.CV OR cat:cs.CL',
            'all:"large language model" OR all:"foundation model" OR all:"deep learning"',
        ]
    return [
        "artificial intelligence deep learning foundation model",
        "large language model multimodal learning",
        "computer vision deep learning",
        "natural language processing machine learning",
        "reinforcement learning artificial intelligence",
    ]


def _read_daily_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _daily_quality_score(paper: Paper) -> tuple[float, list[str]]:
    text = " ".join(
        [
            paper.title,
            paper.abstract,
            paper.venue,
            " ".join(paper.categories),
            " ".join(paper.fields_of_study),
        ]
    ).lower()
    signals: list[str] = []
    score = 0.0

    topic_hits = [keyword for keyword in DAILY_AI_KEYWORDS if keyword in text]
    if topic_hits:
        score += min(28.0, 8.0 + len(topic_hits) * 4.0)
        signals.append("AI/深度学习主题")
    elif any(field.lower() in {"computer science", "artificial intelligence"} for field in paper.fields_of_study):
        score += 8.0
        signals.append("计算机科学方向")

    venue = paper.venue or ""
    for top_venue in TOP_AI_VENUES:
        if top_venue.lower() in venue.lower():
            score += 34.0
            signals.append(top_venue)
            break

    citation_count = paper.citation_count or 0
    if citation_count:
        score += min(22.0, 4.0 + citation_count ** 0.5)
        signals.append(f"引用 {citation_count}")

    year = paper.year or _year_from_date(paper.published)
    current_year = datetime.now(timezone.utc).year
    if year and year >= current_year - 1:
        score += 12.0
        signals.append(f"{year} 新近论文")
    elif year and year >= current_year - 3:
        score += 6.0
        signals.append(f"{year} 近年论文")

    if paper.abstract:
        score += 6.0
        signals.append("摘要完整")
    if paper.authors:
        score += 3.0
    if paper.entry_url:
        score += 3.0
    if paper.source == "semantic_scholar":
        score += 3.0
    if paper.source == "arxiv":
        score += 2.0

    return score, _dedupe_list(signals)


def _daily_recommendation_reason(paper: Paper, signals: list[str]) -> str:
    topic = "、".join(signals[:3]) if signals else "主题相关"
    venue = f"，来源于 {paper.venue}" if paper.venue else ""
    return f"质量排序命中：{topic}{venue}。适合作为今天优先浏览的 AI/深度学习论文。"


def _summary_with_topic_tags(summary, topic_tags: list[str], reading_priority: str | None = None):
    return type(summary)(
        short_summary=summary.short_summary,
        key_points=summary.key_points,
        method_tags=summary.method_tags,
        relevance=summary.relevance,
        reading_priority=reading_priority or summary.reading_priority,
        topic_tags=topic_tags,
        deep_summary=summary.deep_summary,
        contribution=summary.contribution,
        method=summary.method,
        experiments=summary.experiments,
        limitations=summary.limitations,
        reading_notes=summary.reading_notes,
        llm_model=summary.llm_model,
        llm_error=summary.llm_error,
        innovation_points=summary.innovation_points,
        method_comparison=summary.method_comparison,
        datasets_used=summary.datasets_used,
        metrics_used=summary.metrics_used,
        future_directions=summary.future_directions,
    )


def _year_from_date(value: str) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", value or "")
    return int(match.group(1)) if match else None


def _paper_payload_from_row(row) -> dict:
    summary = decode_summary(row)
    return {
        "arxiv_id": row["arxiv_id"],
        "title": row["title"],
        "abstract": row["abstract"],
        "authors": decode_json_field(row, "authors_json"),
        "published": row["published"],
        "updated": row["updated"],
        "entry_url": row["entry_url"],
        "pdf_url": row["pdf_url"],
        "categories": decode_json_field(row, "categories_json"),
        "summary": summary.__dict__,
        "source": row["source"],
        "source_id": row["source_id"],
        "doi": row["doi"],
        "venue": row["venue"],
        "year": row["year"],
        "citation_count": row["citation_count"] or 0,
        "reference_count": row["reference_count"] or 0,
        "influential_citation_count": row["influential_citation_count"] or 0,
        "fields_of_study": decode_json_object(row, "fields_of_study_json", []),
        "tags": decode_json_object(row, "tags_json", []),
        "local_pdf_path": row["local_pdf_path"],
        "citations": decode_json_object(row, "citations_json", []),
        "references": decode_json_object(row, "references_json", []),
        "related": decode_json_object(row, "related_json", []),
    }


def _paper_payload_from_paper(paper: Paper, summary) -> dict:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.authors,
        "published": paper.published,
        "updated": paper.updated,
        "entry_url": paper.entry_url,
        "pdf_url": paper.pdf_url,
        "categories": paper.categories,
        "summary": summary.__dict__,
        "source": paper.source,
        "source_id": paper.source_id,
        "doi": paper.doi,
        "venue": paper.venue,
        "year": paper.year,
        "citation_count": paper.citation_count or 0,
        "reference_count": paper.reference_count or 0,
        "influential_citation_count": 0,
        "fields_of_study": paper.fields_of_study,
        "tags": summary.topic_tags,
        "local_pdf_path": "",
        "citations": [],
        "references": [],
        "related": [],
    }


def _title_words(title: str) -> list[str]:
    return _keyword_words(title)


def _paper_words(row) -> list[str]:
    text = " ".join(
        [
            row["title"] or "",
            row["abstract"] or "",
            row["pdf_text"] or "",
            " ".join(decode_json_object(row, "tags_json", [])),
        ]
    )
    return _keyword_words(text)


def _local_innovation_advice(row, related: list[dict], related_rows: list) -> list[dict]:
    summary = decode_summary(row)
    target_tags = _dedupe_list([*summary.method_tags, *summary.topic_tags, *decode_json_object(row, "tags_json", [])])
    related_summaries = [decode_summary(item) for item in related_rows]
    related_tags = _dedupe_list(
        [
            tag
            for item in related_summaries
            for tag in [*item.method_tags, *item.topic_tags]
        ]
    )
    all_text = " ".join(
        [
            row["title"] or "",
            row["abstract"] or "",
            row["pdf_text"] or "",
            " ".join(item.get("title", "") + " " + item.get("reason", "") for item in related),
            " ".join(item["abstract"] or "" for item in related_rows),
        ]
    ).lower()
    is_process = any(term in all_text for term in ["event log", "process mining", "remaining time", "predictive process"])
    has_incremental = any(term in all_text for term in ["incremental", "online", "stream", "concept drift", "evolving"])
    has_transformer = "transformer" in all_text or "attention" in all_text
    has_uncertainty = any(term in all_text for term in ["uncertainty", "probabilistic", "quantile", "confidence"])
    has_explain = any(term in all_text for term in ["explain", "interpret", "attention", "causal"])

    suggestions: list[dict] = []
    if is_process:
        suggestions.append(
            {
                "title": "把剩余时间预测从离线模型推进到增量事件日志场景",
                "why": "上传论文和推荐论文都围绕事件日志/流程预测，但很多工作仍默认训练集相对固定。",
                "how": "设计在线更新或小批量更新机制，比较全量重训、滑动窗口、样本回放和参数高效更新在准确率与更新成本上的差异。",
                "evidence": _advice_evidence(target_tags, related_tags, ["Remaining time prediction", "Process mining", "Incremental event log"]),
            }
        )
    if has_incremental or is_process:
        suggestions.append(
            {
                "title": "显式处理概念漂移，而不是只追求单次预测精度",
                "why": "增量日志里流程路径、资源分配和活动耗时会随时间变化，推荐论文可以作为基线但未必充分处理漂移。",
                "how": "加入漂移检测模块，按阶段切换或校准模型；实验中增加时间切分验证，报告漂移前后 MAE/RMSE 的稳定性。",
                "evidence": _advice_evidence(target_tags, related_tags, ["Incremental event log", "Predictive process monitoring"]),
            }
        )
    if has_transformer or is_process:
        suggestions.append(
            {
                "title": "做过程结构感知的序列表示，而不是直接套通用 Transformer",
                "why": "相似论文常用序列模型或注意力机制，但业务流程还有活动关系、资源、时间间隔和案例上下文。",
                "how": "把活动转移图、时间间隔、资源角色或前缀阶段编码进模型，并做消融验证每类结构信息是否真正贡献性能。",
                "evidence": _advice_evidence(target_tags, related_tags, ["Transformer", "Representation learning", "Process mining"]),
            }
        )
    if not has_uncertainty:
        suggestions.append(
            {
                "title": "加入不确定性估计，让预测结果更适合决策",
                "why": "剩余时间预测只给单点数值时，很难判断当前案例是否可靠、是否需要人工介入。",
                "how": "输出置信区间或分位数预测，评估覆盖率、校准误差和高风险案例识别能力，而不只报告 MAE/RMSE。",
                "evidence": _advice_evidence(target_tags, related_tags, ["Probabilistic", "Remaining time prediction"]),
            }
        )
    if not has_explain:
        suggestions.append(
            {
                "title": "把可解释性变成论文贡献点",
                "why": "流程场景的使用者通常关心为什么这个案例会延迟，而不只是预测还剩多久。",
                "how": "给出关键前缀事件、瓶颈活动、资源因素对预测的贡献，并用案例级解释对比推荐论文中的黑盒预测方法。",
                "evidence": _advice_evidence(target_tags, related_tags, ["Predictive process monitoring", "Process mining"]),
            }
        )
    suggestions.append(
        {
            "title": "建立更强的实验对比矩阵",
            "why": "如果创新点不够明显，实验设计本身也能形成可信贡献：跨数据集、跨时间段、跨模型类别验证。",
            "how": "至少比较传统机器学习、LSTM/GRU、Transformer/注意力模型和增量更新版本，并加入消融、运行时间、更新成本。",
            "evidence": _advice_evidence(target_tags, related_tags, ["Benchmark", "Long-term", "Multivariate"]),
        }
    )
    return suggestions[:5]


def _question_needs_github(question: str) -> bool:
    text = str(question or "").lower()
    return any(
        keyword in text
        for keyword in [
            "github",
            "代码",
            "源码",
            "仓库",
            "repo",
            "repository",
            "实现",
            "复现",
            "开源",
            "baseline",
            "pytorch",
            "tensorflow",
        ]
    )


def _local_expert_answer(row, summary, question: str, repositories: list[dict], pdf_text: str = "") -> str:
    term_answer = _term_definition_answer(row, summary, question)
    if term_answer:
        return term_answer

    title = row["title"]
    tags = _dedupe_list([*summary.method_tags, *summary.topic_tags, *decode_json_object(row, "tags_json", [])])
    method = _first_text(
        summary.method,
        summary.deep_summary,
        summary.short_summary,
        row["abstract"],
        "当前本地信息还不足以拆出完整方法流程，建议先下载全文或点击 LLM 深度解读。",
    )
    innovation = summary.innovation_points or _innovation_from_summary(summary)
    experiments = _first_text(
        summary.experiments,
        _experiment_hint_from_text(pdf_text or row["abstract"] or ""),
        "当前摘要/全文片段里没有清楚的实验细节。建议重点补看数据集、指标、对比基线和消融实验。",
    )
    comparison = _first_text(
        summary.method_comparison,
        "可以把它和同任务的传统机器学习、LSTM/GRU、Transformer/注意力模型以及最新开源实现做横向对比。",
    )
    repo_text = _repositories_for_answer(repositories)
    focus = _reading_focus(summary, tags)

    parts = [
        f"我按“论文导师”的方式帮你看《{title}》。",
        f"你的问题：{question.strip() or '这篇论文该怎么理解？'}",
        "",
        f"方法思想：{method}",
        f"创新点：{'; '.join(innovation[:5]) if innovation else '从当前信息看，创新点需要结合正文进一步确认。'}",
        f"与已有方法对比：{comparison}",
        f"实验结果：{experiments}",
        f"阅读抓手：{focus}",
    ]
    if repo_text:
        parts.extend(["", f"GitHub 参考：{repo_text}"])
    return "\n".join(parts).strip()


TERM_EXPLANATIONS = {
    "autoencoder": {
        "name": "Autoencoder（自编码器）",
        "aliases": ["autoencoder", "auto-encoder", "自编码器"],
        "plain": (
            "它是一类神经网络，核心结构是“编码器 + 解码器”：编码器把输入压缩成一个更短、更抽象的隐向量，"
            "解码器再尝试从这个隐向量还原输入或重构关键特征。训练时通常让重构结果尽量接近原始输入，"
            "所以模型会被迫学到输入数据中最重要的表示。"
        ),
        "paper_role": (
            "在这篇论文里，Autoencoder 不是指“自动编码某段程序”，而是增量剩余时间预测框架的一种深度模型实例化。"
            "它和 LSTM-based、Transformer-based 版本并列，作用是用自编码器学习事件日志/案例前缀特征的压缩表示，"
            "再服务于剩余时间预测，并随着增量事件日志更新。"
        ),
        "contrast": (
            "和 LSTM 相比，LSTM 更强调按时间顺序记住事件序列的长期依赖；和 Transformer 相比，Transformer 更强调用注意力机制找不同事件之间的关系；"
            "Autoencoder 更强调把输入特征压缩成有效表示，适合做降维、去噪、特征学习或作为预测模型前的表示学习模块。"
        ),
        "reading": (
            "你读正文时重点找三件事：作者把哪些事件日志特征喂给自编码器，隐向量如何接到剩余时间预测输出，"
            "以及 Autoencoder-based 版本在九个真实事件日志上是否真的比 LSTM/Transformer 或传统基线更稳。"
        ),
    },
    "lstm": {
        "name": "LSTM（长短期记忆网络）",
        "aliases": ["lstm", "long short-term memory", "长短期记忆"],
        "plain": "它是一种循环神经网络，靠门控机制保留或遗忘历史信息，常用于按时间顺序处理事件序列、文本或时间序列。",
        "paper_role": "在这篇论文里，LSTM-based 版本通常用来按顺序读取事件日志前缀，学习前面发生过的活动如何影响剩余时间。",
        "contrast": "它比普通 RNN 更能处理较长依赖，但并行能力和全局关系建模通常不如 Transformer。",
        "reading": "重点看输入序列如何编码、隐藏状态如何接预测头，以及增量更新时是否容易遗忘旧流程模式。",
    },
    "transformer": {
        "name": "Transformer",
        "aliases": ["transformer", "attention", "注意力"],
        "plain": "它是一类基于注意力机制的神经网络，可以让模型直接比较序列中不同位置的事件，找出哪些历史事件更影响当前预测。",
        "paper_role": "在这篇论文里，Transformer-based 版本通常用于建模事件日志前缀中不同活动、时间间隔或上下文特征之间的关系。",
        "contrast": "它比 LSTM 更容易并行并捕捉长距离关系，但数据量不足时可能更依赖正则化和合理特征设计。",
        "reading": "重点看作者如何编码事件顺序和时间信息，以及注意力模块是否通过消融实验带来稳定提升。",
    },
    "concept drift": {
        "name": "Concept drift（概念漂移）",
        "aliases": ["concept drift", "概念漂移"],
        "plain": "它指数据分布或业务规律随时间变化，导致过去训练好的模型在新数据上变差。",
        "paper_role": "在增量事件日志场景里，流程路径、资源分配、活动耗时变化都可能造成概念漂移，所以模型需要检测或触发更新。",
        "contrast": "普通离线模型默认规律稳定；处理概念漂移的方法会关注何时更新模型、用多少新数据更新、如何避免遗忘旧模式。",
        "reading": "重点看论文是否有漂移触发策略、时间切分实验，以及漂移前后预测精度是否稳定。",
    },
    "process mining": {
        "name": "Process mining（流程挖掘）",
        "aliases": ["process mining", "流程挖掘"],
        "plain": "它是从事件日志中分析业务流程的方法，常看活动顺序、案例轨迹、资源、时间戳和瓶颈。",
        "paper_role": "这篇论文的剩余时间预测就是流程挖掘里的预测性监控任务：给定一个还没结束的案例前缀，预测它还需要多久完成。",
        "contrast": "传统流程挖掘更偏发现和诊断流程；深度学习版本更偏从日志中学习表示并做预测。",
        "reading": "重点看事件日志字段、案例前缀构造、预测目标和业务评价指标。",
    },
}


def _term_definition_answer(row, summary, question: str) -> str:
    term = _requested_term(question, summary)
    if not term:
        return ""
    explanation = TERM_EXPLANATIONS.get(term)
    if not explanation:
        return ""
    tags = _dedupe_list([*summary.method_tags, *summary.topic_tags, *decode_json_object(row, "tags_json", [])])
    lines = [
        f"{explanation['name']}的意思：{explanation['plain']}",
        "",
        f"在这篇论文里：{explanation['paper_role']}",
        "",
        f"和相近方法的区别：{explanation['contrast']}",
        "",
        f"你该怎么看：{explanation['reading']}",
    ]
    if tags:
        lines.append("")
        lines.append(f"当前论文相关标签：{', '.join(tags[:6])}。")
    return "\n".join(lines).strip()


def _requested_term(question: str, summary) -> str:
    text = str(question or "").strip().lower()
    if not text:
        return ""
    asks_definition = any(pattern in text for pattern in ["是什么意思", "什么意思", "是什么", "解释", "含义", "meaning", "what is"])
    if not asks_definition:
        return ""
    known_terms = [*TERM_EXPLANATIONS.keys()]
    for key, explanation in TERM_EXPLANATIONS.items():
        for alias in explanation["aliases"]:
            if alias.lower() in text:
                return key
    for tag in [*summary.method_tags, *summary.topic_tags]:
        normalized = str(tag or "").lower()
        if normalized in known_terms and normalized in text:
            return normalized
    return ""


def _first_text(*values: str) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _innovation_from_summary(summary) -> list[str]:
    points = []
    if summary.contribution:
        points.append(summary.contribution)
    if summary.method:
        points.append(f"方法上：{summary.method}")
    for point in summary.key_points[:3]:
        points.append(point)
    return points


def _experiment_hint_from_text(text: str) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text)
    match = re.search(
        r"((?:experiment|evaluation|result|benchmark|dataset|imagenet|coco|ablation|mae|rmse|accuracy|f1)[^.。]{0,260}[.。])",
        compact,
        re.I,
    )
    return match.group(1).strip() if match else ""


def _reading_focus(summary, tags: list[str]) -> str:
    focus = []
    if tags:
        focus.append(f"先抓方法标签：{', '.join(tags[:5])}")
    if summary.datasets_used:
        focus.append(f"核对数据集：{', '.join(summary.datasets_used[:4])}")
    if summary.metrics_used:
        focus.append(f"看指标：{', '.join(summary.metrics_used[:4])}")
    focus.append("最后看实验表格里的对比基线、消融实验和失败案例")
    return "；".join(focus) + "。"


def _repositories_for_answer(repositories: list[dict]) -> str:
    if not repositories:
        return ""
    lines = []
    for repo in repositories[:5]:
        stars = repo.get("stars", 0)
        language = repo.get("language") or "未知语言"
        reason = repo.get("reason") or "与论文关键词匹配"
        lines.append(f"{repo.get('full_name')}（{language}, {stars} stars，{reason}）")
    return "；".join(lines)


def _advice_evidence(target_tags: list[str], related_tags: list[str], preferred: list[str]) -> list[str]:
    evidence = [tag for tag in preferred if tag in target_tags or tag in related_tags]
    if not evidence:
        evidence = [*target_tags[:2], *related_tags[:2]]
    return _dedupe_list(evidence)[:4]


def _keyword_words(text: str) -> list[str]:
    stop = {
        "the", "a", "an", "for", "and", "or", "with", "using", "of", "in", "on",
        "to", "from", "by", "as", "is", "are", "this", "that", "these", "those",
        "we", "our", "paper", "study", "method", "model", "result", "results",
    }
    seen: set[str] = set()
    words = []
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) <= 3 or word in stop or word in seen:
            continue
        seen.add(word)
        words.append(word)
        if len(words) >= 120:
            break
    return [
        word for word in words
    ]


def _manual_paper_id(title: str, doi: str = "") -> str:
    if doi:
        return f"manual:doi:{_safe_token(doi)}"
    return f"manual:{_safe_token(title)}"


def _safe_token(value: str) -> str:
    value = re.sub(r"^https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9._:-]+", "-", value)
    return value.strip("-")[:120] or "paper"


def _title_from_upload(filename: str, pdf_text: str) -> str:
    for line in (pdf_text or "").splitlines()[:30]:
        stripped = line.strip()
        if 12 <= len(stripped) <= 180 and not stripped.lower().startswith(("abstract", "keywords")):
            return stripped
    stem = Path(filename or "uploaded-paper").stem.strip()
    return stem.replace("_", " ").replace("-", " ") or "Uploaded paper"


def _abstract_from_upload(pdf_text: str) -> str:
    text = re.sub(r"\s+", " ", pdf_text or "").strip()
    if not text:
        return "用户上传的 PDF 论文，当前环境未能提取全文文本。"
    match = re.search(r"\babstract\b[:\s-]*(.{300,1800}?)(?:\bkeywords?\b|\bintroduction\b|1\s+introduction)", text, re.I)
    if match:
        return match.group(1).strip()
    return text[:1800]


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
