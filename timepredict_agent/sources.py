from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from os import environ
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import re

from .arxiv_client import ArxivClient
from .models import Paper, SourceResult


SEMANTIC_FIELDS = ",".join(
    [
        "paperId",
        "externalIds",
        "url",
        "title",
        "abstract",
        "venue",
        "year",
        "publicationDate",
        "authors",
        "fieldsOfStudy",
        "citationCount",
        "referenceCount",
        "openAccessPdf",
    ]
)


class PaperSource(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        raise NotImplementedError


class ArxivSource(PaperSource):
    name = "arxiv"

    def __init__(self) -> None:
        self.client = ArxivClient()

    def search(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        try:
            papers = self.client.search(query, max_results, recent_days)
            return SourceResult(self.name, papers)
        except RuntimeError as exc:
            return SourceResult(self.name, [], str(exc))


class SemanticScholarSource(PaperSource):
    name = "semantic_scholar"

    def search(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        params = urlencode(
            {
                "query": _semantic_query(query),
                "limit": min(max_results, 100),
                "fields": SEMANTIC_FIELDS,
            }
        )
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
        try:
            payload = _read_json(url)
        except RuntimeError as exc:
            return SourceResult(self.name, [], str(exc))

        cutoff_year = None
        if recent_days is not None:
            cutoff_year = datetime.now(timezone.utc).year - max(1, recent_days // 365 + 1)

        papers: list[Paper] = []
        for item in payload.get("data", []):
            paper = _semantic_to_paper(item)
            if not paper.title or not paper.abstract:
                continue
            if cutoff_year and paper.year and paper.year < cutoff_year:
                continue
            papers.append(paper)
        return SourceResult(self.name, papers)


class OpenAlexSource(PaperSource):
    name = "openalex"

    def search(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        filters = ["type:article"]
        if recent_days is not None:
            start_date = datetime.now(timezone.utc).date() - timedelta(days=recent_days)
            filters.append(f"from_publication_date:{start_date.isoformat()}")
        params = urlencode(
            {
                "search": _plain_query(query),
                "filter": ",".join(filters),
                "sort": "publication_date:desc",
                "per-page": min(max(max_results * 4, max_results), 200),
            }
        )
        url = f"https://api.openalex.org/works?{params}"
        try:
            payload = _read_json(url)
        except RuntimeError as exc:
            return SourceResult(self.name, [], str(exc))

        papers = [_openalex_to_paper(item) for item in payload.get("results", [])]
        papers = _dedupe_papers([paper for paper in papers if paper.title and _looks_relevant_to_time_series(paper)])
        return SourceResult(self.name, papers[:max_results])


class IeeeXploreSource(PaperSource):
    name = "ieee_xplore"

    def search(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        api_key = environ.get("IEEE_XPLORE_API_KEY", "").strip()
        if not api_key:
            return self._search_public_site(query, max_results, recent_days)
        params = urlencode(
            {
                "apikey": api_key,
                "format": "json",
                "max_records": min(max_results, 100),
                "sort_order": "desc",
                "sort_field": "publication_year",
                "querytext": _plain_query(query),
            }
        )
        url = f"https://ieeexploreapi.ieee.org/api/v1/search/articles?{params}"
        try:
            payload = _read_json(url)
        except RuntimeError as exc:
            return SourceResult(self.name, [], str(exc))

        papers = [_ieee_to_paper(item) for item in payload.get("articles", [])]
        return SourceResult(self.name, [paper for paper in papers if paper.title])

    def _search_public_site(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        body = {
            "newsearch": True,
            "queryText": _plain_query(query),
            "highlight": False,
            "returnFacets": ["ALL"],
            "returnType": "SEARCH",
            "matchPubs": True,
            "pageNumber": 1,
            "rowsPerPage": min(max_results, 100),
            "sortType": "newest",
        }
        if recent_days is not None:
            body["ranges"] = [
                f"{datetime.now(timezone.utc).year - max(0, recent_days // 365)}_{datetime.now(timezone.utc).year}_Year"
            ]
        try:
            payload = _read_json(
                "https://ieeexplore.ieee.org/rest/search",
                payload=body,
                headers={
                    "Origin": "https://ieeexplore.ieee.org",
                    "Referer": "https://ieeexplore.ieee.org/search/searchresult.jsp",
                },
            )
        except RuntimeError as exc:
            return SourceResult(
                self.name,
                [],
                f"IEEE 公开检索抓取失败：{exc}。如果网络或站点策略拦截，可配置 IEEE_XPLORE_API_KEY 使用官方 Metadata API。",
            )

        records = payload.get("records") or payload.get("articles") or []
        papers = [_ieee_public_to_paper(item) for item in records]
        papers = _dedupe_papers([paper for paper in papers if paper.title and _looks_relevant_to_time_series(paper)])
        return SourceResult(self.name, papers[:max_results])


class GoogleScholarSource(PaperSource):
    name = "google_scholar"

    def __init__(self, html_path: str | Path = "data/google_scholar.html") -> None:
        self.html_path = Path(html_path)

    def search(self, query: str, max_results: int, recent_days: int | None) -> SourceResult:
        scholar_url = f"https://scholar.google.com/scholar?{urlencode({'q': _plain_query(query)})}"
        if not self.html_path.exists():
            return SourceResult(
                self.name,
                [],
                "Google Scholar 不适合无人值守自动抓取。请在浏览器打开检索结果，保存网页到 "
                f"{self.html_path.as_posix()} 后再收集；检索入口：{scholar_url}",
            )

        try:
            html = self.html_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return SourceResult(self.name, [], f"读取 Google Scholar HTML 失败：{exc}")

        parser = _GoogleScholarHtmlParser(max_results=max_results)
        parser.feed(html)
        papers = [paper for paper in parser.papers if paper.title]
        return SourceResult(self.name, papers[:max_results])


def build_sources(names: list[str]) -> list[PaperSource]:
    registry: dict[str, PaperSource] = {
        "arxiv": ArxivSource(),
        "semantic_scholar": SemanticScholarSource(),
        "openalex": OpenAlexSource(),
        "ieee_xplore": IeeeXploreSource(),
        "google_scholar": GoogleScholarSource(),
    }
    return [registry[name] for name in names if name in registry]


def _read_json(url: str, payload: dict | None = None, headers: dict[str, str] | None = None) -> dict:
    request_headers = {
        "User-Agent": "timepredict-agent/0.2 (local research helper; contact: local)",
        "Accept": "application/json,text/plain,*/*",
    }
    request_headers.update(headers or {})
    if environ.get("SEMANTIC_SCHOLAR_API_KEY") and "semanticscholar.org" in url:
        request_headers["x-api-key"] = environ["SEMANTIC_SCHOLAR_API_KEY"]
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=request_headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"请求失败：{exc}") from exc


def _semantic_to_paper(item: dict) -> Paper:
    external_ids = {k: str(v) for k, v in (item.get("externalIds") or {}).items() if v}
    arxiv_id = external_ids.get("ArXiv") or item.get("paperId") or item.get("title", "")
    pdf_url = ((item.get("openAccessPdf") or {}).get("url") or "")
    published = item.get("publicationDate") or str(item.get("year") or "")
    if published and len(published) == 4:
        published = f"{published}-01-01T00:00:00Z"
    authors = [author.get("name", "") for author in item.get("authors", [])]
    return Paper(
        arxiv_id=f"s2:{arxiv_id}",
        title=item.get("title") or "",
        abstract=item.get("abstract") or "",
        authors=[author for author in authors if author],
        published=published or "",
        updated=published or "",
        entry_url=item.get("url") or "",
        pdf_url=pdf_url,
        categories=[],
        source="semantic_scholar",
        source_id=item.get("paperId") or "",
        doi=external_ids.get("DOI", ""),
        venue=item.get("venue") or "",
        year=item.get("year"),
        citation_count=item.get("citationCount"),
        reference_count=item.get("referenceCount"),
        external_ids=external_ids,
        fields_of_study=item.get("fieldsOfStudy") or [],
    )


def _openalex_to_paper(item: dict) -> Paper:
    source_id = str(item.get("id") or item.get("doi") or item.get("display_name") or "")
    doi = (item.get("doi") or "").replace("https://doi.org/", "")
    publication_date = item.get("publication_date") or ""
    year = item.get("publication_year")
    authors = [
        (((authorship.get("author") or {}).get("display_name")) or "")
        for authorship in item.get("authorships", [])
    ]
    locations = item.get("locations") or []
    best_oa = item.get("best_oa_location") or {}
    primary = item.get("primary_location") or {}
    pdf_url = best_oa.get("pdf_url") or primary.get("pdf_url") or ""
    entry_url = item.get("id") or primary.get("landing_page_url") or item.get("doi") or ""
    host = primary.get("source") or {}
    return Paper(
        arxiv_id=f"openalex:{_safe_id(source_id)}",
        title=item.get("display_name") or "",
        abstract=_openalex_abstract(item.get("abstract_inverted_index") or {}),
        authors=[author for author in authors if author],
        published=f"{publication_date}T00:00:00Z" if publication_date else "",
        updated=f"{publication_date}T00:00:00Z" if publication_date else "",
        entry_url=entry_url,
        pdf_url=pdf_url,
        categories=[],
        source="openalex",
        source_id=source_id,
        doi=doi,
        venue=host.get("display_name") or "",
        year=int(year) if str(year).isdigit() else None,
        citation_count=item.get("cited_by_count"),
        external_ids={"DOI": doi} if doi else {},
        fields_of_study=[concept.get("display_name", "") for concept in item.get("concepts", [])[:5]],
    )


def _ieee_to_paper(item: dict) -> Paper:
    article_number = str(item.get("article_number") or item.get("arnumber") or item.get("doi") or "")
    title = item.get("title") or item.get("article_title") or ""
    abstract = item.get("abstract") or ""
    authors_raw = item.get("authors", {}).get("authors", []) if isinstance(item.get("authors"), dict) else []
    authors = [author.get("full_name", "") for author in authors_raw]
    year = item.get("publication_year")
    doi = item.get("doi") or ""
    pdf_url = item.get("pdf_url") or item.get("html_url") or ""
    url = item.get("html_url") or item.get("abstract_url") or ""
    return Paper(
        arxiv_id=f"ieee:{article_number}",
        title=title,
        abstract=abstract,
        authors=[author for author in authors if author],
        published=f"{year}-01-01T00:00:00Z" if year else "",
        updated=f"{year}-01-01T00:00:00Z" if year else "",
        entry_url=url,
        pdf_url=pdf_url,
        categories=[],
        source="ieee_xplore",
        source_id=article_number,
        doi=doi,
        venue=item.get("publication_title") or "",
        year=int(year) if str(year).isdigit() else None,
        external_ids={"DOI": doi, "IEEE": article_number},
    )


def _ieee_public_to_paper(item: dict) -> Paper:
    article_number = str(
        item.get("articleNumber")
        or item.get("article_number")
        or item.get("arnumber")
        or item.get("recordId")
        or item.get("doi")
        or ""
    )
    title = _strip_html(item.get("articleTitle") or item.get("title") or "")
    abstract = _strip_html(item.get("abstract") or item.get("description") or "")
    year = item.get("publicationYear") or item.get("publication_year") or item.get("year")
    doi = item.get("doi") or ""
    authors = _ieee_public_authors(item)
    document_link = item.get("documentLink") or item.get("htmlLink") or item.get("html_url") or ""
    if document_link.startswith("/"):
        document_link = f"https://ieeexplore.ieee.org{document_link}"
    pdf_url = item.get("pdfLink") or item.get("pdf_url") or ""
    if pdf_url.startswith("/"):
        pdf_url = f"https://ieeexplore.ieee.org{pdf_url}"
    return Paper(
        arxiv_id=f"ieee:{article_number or _safe_id(title)}",
        title=title,
        abstract=abstract,
        authors=authors,
        published=f"{year}-01-01T00:00:00Z" if year else "",
        updated=f"{year}-01-01T00:00:00Z" if year else "",
        entry_url=document_link,
        pdf_url=pdf_url,
        categories=[],
        source="ieee_xplore",
        source_id=article_number,
        doi=doi,
        venue=item.get("publicationTitle") or item.get("publication_title") or "",
        year=int(year) if str(year).isdigit() else None,
        external_ids={"DOI": doi, "IEEE": article_number},
    )


def _ieee_public_authors(item: dict) -> list[str]:
    authors = item.get("authors") or []
    if isinstance(authors, list):
        result = []
        for author in authors:
            if isinstance(author, dict):
                result.append(author.get("preferredName") or author.get("full_name") or author.get("name") or "")
            else:
                result.append(str(author))
        return [author for author in result if author]
    if isinstance(authors, dict):
        nested = authors.get("authors") or []
        return [
            author.get("full_name") or author.get("preferredName") or author.get("name") or ""
            for author in nested
            if isinstance(author, dict)
        ]
    return []


def _semantic_query(query: str) -> str:
    return _plain_query(query).replace("cat:cs.LG", "").replace("cat:stat.ML", "")


def _plain_query(query: str) -> str:
    query = re.sub(r"cat:[^\s)]+", " ", query)
    replacements = {
        "all:": "",
        "AND": " ",
        "OR": " ",
        "(": " ",
        ")": " ",
        '"': "",
    }
    for old, new in replacements.items():
        query = query.replace(old, new)
    return " ".join(query.split())


def _openalex_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions.append((int(index), word))
    positions.sort()
    return " ".join(word for _, word in positions)


def _safe_id(value: str) -> str:
    value = re.sub(r"^https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9._:-]+", "-", value)
    return value.strip("-")[:120] or "unknown"


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", str(value)).strip()


def _looks_relevant_to_time_series(paper: Paper) -> bool:
    text = " ".join([paper.title, paper.abstract, paper.venue, " ".join(paper.fields_of_study)]).lower()
    keywords = [
        "time series",
        "forecast",
        "prediction",
        "predictive",
        "temporal",
        "sequence",
        "event log",
        "predictive process monitoring",
        "process monitoring",
        "remaining time prediction",
        "incremental event log",
        "business process",
        "process mining",
        "anomaly detection",
        "multivariate",
        "long-term",
        "irregular",
    ]
    return any(keyword in text for keyword in keywords)


def _dedupe_papers(papers: list[Paper]) -> list[Paper]:
    seen: set[str] = set()
    result: list[Paper] = []
    for paper in papers:
        key = paper.doi.lower() if paper.doi else re.sub(r"\W+", " ", paper.title.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(paper)
    return result


class _GoogleScholarHtmlParser(HTMLParser):
    def __init__(self, max_results: int) -> None:
        super().__init__()
        self.max_results = max_results
        self.papers: list[Paper] = []
        self._in_item = False
        self._in_title = False
        self._in_meta = False
        self._in_snippet = False
        self._current: dict[str, str] = {}
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if tag == "div" and "gs_ri" in classes:
            self._in_item = True
            self._current = {"title": "", "url": "", "meta": "", "abstract": ""}
        if not self._in_item:
            return
        if tag == "h3" and "gs_rt" in classes:
            self._in_title = True
            self._parts = []
        elif tag == "a" and self._in_title and not self._current.get("url"):
            self._current["url"] = attr.get("href") or ""
        elif tag == "div" and "gs_a" in classes:
            self._in_meta = True
            self._parts = []
        elif tag == "div" and "gs_rs" in classes:
            self._in_snippet = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title or self._in_meta or self._in_snippet:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_title and tag == "h3":
            self._current["title"] = " ".join(" ".join(self._parts).split())
            self._in_title = False
        elif self._in_meta and tag == "div":
            self._current["meta"] = " ".join(" ".join(self._parts).split())
            self._in_meta = False
        elif self._in_snippet and tag == "div":
            self._current["abstract"] = " ".join(" ".join(self._parts).split())
            self._in_snippet = False
        elif self._in_item and tag == "div" and self._current.get("title"):
            self._add_current()
            self._in_item = False

    def _add_current(self) -> None:
        if len(self.papers) >= self.max_results:
            return
        title = self._current.get("title", "")
        meta = self._current.get("meta", "")
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", meta)
        year = int(year_match.group(1)) if year_match else None
        authors = _scholar_authors(meta)
        self.papers.append(
            Paper(
                arxiv_id=f"scholar:{_safe_id(title)}",
                title=title,
                abstract=self._current.get("abstract", ""),
                authors=authors,
                published=f"{year}-01-01T00:00:00Z" if year else "",
                updated=f"{year}-01-01T00:00:00Z" if year else "",
                entry_url=self._current.get("url", ""),
                pdf_url="",
                categories=[],
                source="google_scholar",
                source_id=_safe_id(title),
                year=year,
                venue=_scholar_venue(meta),
            )
        )


def _scholar_authors(meta: str) -> list[str]:
    head = meta.split("-", 1)[0]
    return [part.strip() for part in head.split(",") if part.strip()][:8]


def _scholar_venue(meta: str) -> str:
    parts = [part.strip() for part in meta.split("-")]
    return parts[1] if len(parts) > 1 else ""
