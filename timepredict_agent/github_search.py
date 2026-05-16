from __future__ import annotations

from os import environ
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re

from .models import Paper, PaperSummary


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_USER_AGENT = "timepredict-agent/0.4"


class GitHubRepositorySearcher:
    def __init__(self, token: str | None = None, timeout: int = 20) -> None:
        self.token = token if token is not None else environ.get("GITHUB_TOKEN") or environ.get("GH_TOKEN") or ""
        self.timeout = timeout
        self.last_error = ""

    def search(
        self,
        paper: Paper,
        summary: PaperSummary,
        question: str = "",
        limit: int = 5,
    ) -> list[dict]:
        self.last_error = ""
        query = build_repository_query(paper, summary, question)
        if not query:
            return []
        params = urlencode(
            {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max(1, min(limit, 10)),
            }
        )
        request = Request(f"{GITHUB_SEARCH_URL}?{params}", headers=self._headers())
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self.last_error = f"GitHub 搜索失败：HTTP {exc.code} {detail[:160]}"
            return []
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.last_error = f"GitHub 搜索失败：{exc!r}"
            return []

        terms = _query_terms(paper, summary, question)
        repositories = []
        for item in payload.get("items", []):
            repository = repository_from_item(item, terms)
            if repository:
                repositories.append(repository)
        return repositories[:limit]

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": GITHUB_USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


def build_repository_query(paper: Paper, summary: PaperSummary, question: str = "") -> str:
    terms = _query_terms(paper, summary, question)
    if not terms:
        return ""
    implementation_terms = ["implementation"]
    if _looks_like_deep_learning(paper, summary, question):
        implementation_terms.extend(["pytorch", "tensorflow"])
    query_terms = [*terms[:7], *implementation_terms[:2], "in:name,description,readme", "fork:false", "archived:false"]
    query = " ".join(_sanitize_query_part(term) for term in query_terms if _sanitize_query_part(term))
    return query[:240]


def repository_from_item(item: dict, query_terms: list[str] | None = None) -> dict:
    full_name = str(item.get("full_name") or "").strip()
    html_url = str(item.get("html_url") or "").strip()
    if not full_name or not html_url:
        return {}
    description = str(item.get("description") or "").strip()
    topics = [str(topic) for topic in item.get("topics") or [] if str(topic).strip()]
    matched = _matched_terms(" ".join([full_name, description, " ".join(topics)]), query_terms or [])
    reason = "与论文标题或方法标签匹配"
    if matched:
        reason = f"匹配关键词：{', '.join(matched[:5])}"
    return {
        "full_name": full_name,
        "html_url": html_url,
        "description": description,
        "language": str(item.get("language") or "").strip(),
        "stars": int(item.get("stargazers_count") or 0),
        "updated_at": str(item.get("updated_at") or "").strip(),
        "topics": topics,
        "reason": reason,
    }


def _query_terms(paper: Paper, summary: PaperSummary, question: str = "") -> list[str]:
    candidates = [
        *_important_words(paper.title),
        *summary.method_tags,
        *summary.topic_tags,
        *_important_words(question),
    ]
    return _dedupe([_normalize_term(term) for term in candidates if _normalize_term(term)])[:12]


def _important_words(text: str) -> list[str]:
    stop = {
        "paper", "with", "from", "using", "based", "learning", "model", "models",
        "method", "methods", "towards", "toward", "through", "deep", "neural",
        "this", "that", "have", "github", "code", "repo", "implementation",
    }
    words = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text or ""):
        lowered = word.lower()
        if lowered in stop:
            continue
        words.append(word)
    return words


def _normalize_term(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "").strip())
    if not value:
        return ""
    return value[:48]


def _sanitize_query_part(value: str) -> str:
    if ":" in value and re.fullmatch(r"[A-Za-z_,]+:[A-Za-z_,]+|fork:false|archived:false", value):
        return value
    return re.sub(r"[^A-Za-z0-9_.+-]+", " ", value).strip()


def _looks_like_deep_learning(paper: Paper, summary: PaperSummary, question: str) -> bool:
    text = " ".join(
        [
            paper.title,
            paper.abstract,
            question,
            " ".join(summary.method_tags),
            " ".join(summary.topic_tags),
        ]
    ).lower()
    return any(
        term in text
        for term in [
            "deep learning",
            "neural",
            "transformer",
            "resnet",
            "cnn",
            "llm",
            "multimodal",
            "reinforcement learning",
            "diffusion",
            "pytorch",
        ]
    )


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
