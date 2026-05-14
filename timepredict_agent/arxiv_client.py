from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
import re
import ssl
import time
import xml.etree.ElementTree as ET

from .models import Paper


ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


class ArxivClient:
    def __init__(self, polite_delay_seconds: float = 3.0) -> None:
        self._last_request_at = 0.0
        self._delay = polite_delay_seconds

    def search(self, query: str, max_results: int, recent_days: int | None = None) -> list[Paper]:
        self._sleep_if_needed()
        params = urlencode(
            {
                "search_query": query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        request = Request(
            f"{ARXIV_API_URL}?{params}",
            headers={"User-Agent": "timepredict-agent/0.1 (local research helper)"},
        )
        body = _read_public_feed(request)
        self._last_request_at = time.monotonic()

        papers = self._parse_feed(body)
        if recent_days is None:
            return papers

        cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
        return [paper for paper in papers if _parse_date(paper.published) >= cutoff]

    def _sleep_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if self._last_request_at and elapsed < self._delay:
            time.sleep(self._delay - elapsed)

    def _parse_feed(self, body: bytes) -> list[Paper]:
        root = ET.fromstring(body)
        papers: list[Paper] = []
        for entry in root.findall(f"{ATOM}entry"):
            links = entry.findall(f"{ATOM}link")
            entry_url = _text(entry.find(f"{ATOM}id"))
            pdf_url = ""
            for link in links:
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href", "")
                    break

            arxiv_id = entry_url.rsplit("/", 1)[-1]
            categories = [node.attrib.get("term", "") for node in entry.findall(f"{ATOM}category")]
            authors = [_text(author.find(f"{ATOM}name")) for author in entry.findall(f"{ATOM}author")]
            comment = _text(entry.find(f"{ARXIV}comment"))
            abstract = _clean_text(_text(entry.find(f"{ATOM}summary")))
            if comment:
                abstract = f"{abstract}\n\nAuthor comment: {_clean_text(comment)}"

            papers.append(
                Paper(
                    arxiv_id=arxiv_id,
                    title=_clean_text(_text(entry.find(f"{ATOM}title"))),
                    abstract=abstract,
                    authors=[author for author in authors if author],
                    published=_text(entry.find(f"{ATOM}published")),
                    updated=_text(entry.find(f"{ATOM}updated")),
                    entry_url=entry_url,
                    pdf_url=pdf_url,
                    categories=[category for category in categories if category],
                )
            )
        return papers


def _text(node: ET.Element | None) -> str:
    return unescape(node.text or "").strip() if node is not None else ""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_date(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    parsed = parsedate_to_datetime(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _read_public_feed(request: Request) -> bytes:
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise RuntimeError(f"Failed to fetch arXiv feed: {exc}") from exc

    context = ssl._create_unverified_context()
    try:
        with urlopen(request, timeout=30, context=context) as response:
            return response.read()
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch arXiv feed: {exc}") from exc
