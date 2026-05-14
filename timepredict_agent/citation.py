from __future__ import annotations

from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from os import environ
import json

from .models import CitationSummary, RelatedPaper


FIELDS = "paperId,title,url,citationCount,referenceCount,influentialCitationCount,citations.title,citations.url,references.title,references.url"
RECOMMEND_FIELDS = "title,url,venue,year,citationCount"


class CitationService:
    def fetch_for_row(self, row) -> CitationSummary:
        paper_ref = _semantic_ref(row)
        if not paper_ref:
            return CitationSummary(
                citation_count=row["citation_count"] or 0,
                reference_count=row["reference_count"] or 0,
            )
        try:
            payload = _read_json(
                f"https://api.semanticscholar.org/graph/v1/paper/{quote(paper_ref, safe=':')}"
                f"?fields={FIELDS}"
            )
        except RuntimeError:
            return CitationSummary(
                citation_count=row["citation_count"] or 0,
                reference_count=row["reference_count"] or 0,
            )

        return CitationSummary(
            citation_count=payload.get("citationCount") or 0,
            reference_count=payload.get("referenceCount") or 0,
            influential_citation_count=payload.get("influentialCitationCount") or 0,
            citations=[
                _related(item, "引用了当前论文")
                for item in (payload.get("citations") or [])[:20]
                if item.get("title")
            ],
            references=[
                _related(item, "当前论文参考文献")
                for item in (payload.get("references") or [])[:20]
                if item.get("title")
            ],
        )

    def recommend_from_semantic_scholar(self, row, limit: int = 8) -> list[RelatedPaper]:
        paper_ref = _semantic_ref(row)
        if not paper_ref:
            return []
        url = (
            "https://api.semanticscholar.org/recommendations/v1/papers/forpaper/"
            f"{quote(paper_ref, safe=':')}?limit={limit}&fields={RECOMMEND_FIELDS}"
        )
        try:
            payload = _read_json(url)
        except RuntimeError:
            return []
        recommended = payload.get("recommendedPapers") or []
        return [
            RelatedPaper(
                title=item.get("title") or "",
                source="semantic_scholar",
                url=item.get("url") or "",
                reason="Semantic Scholar 推荐",
                score=float(item.get("citationCount") or 0),
            )
            for item in recommended
            if item.get("title")
        ]


def _semantic_ref(row) -> str:
    external_ids = json.loads(row["external_ids_json"] or "{}")
    if row["source"] == "semantic_scholar" and row["source_id"]:
        return row["source_id"]
    if external_ids.get("DOI"):
        return f"DOI:{external_ids['DOI']}"
    if external_ids.get("ArXiv"):
        return f"ARXIV:{external_ids['ArXiv']}"
    if row["arxiv_id"] and not row["arxiv_id"].startswith(("s2:", "ieee:")):
        return f"ARXIV:{row['arxiv_id'].removesuffix('v1')}"
    return ""


def _related(item: dict, reason: str) -> RelatedPaper:
    return RelatedPaper(
        title=item.get("title") or "",
        source="semantic_scholar",
        url=item.get("url") or "",
        reason=reason,
        score=0.0,
    )


def _read_json(url: str) -> dict:
    headers = {"User-Agent": "timepredict-agent/0.2"}
    if environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = environ["SEMANTIC_SCHOLAR_API_KEY"]
    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"请求失败：{exc}") from exc

