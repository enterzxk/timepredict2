from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    published: str
    updated: str
    entry_url: str
    pdf_url: str
    categories: list[str] = field(default_factory=list)
    source: str = "arxiv"
    source_id: str = ""
    doi: str = ""
    venue: str = ""
    year: int | None = None
    citation_count: int | None = None
    reference_count: int | None = None
    external_ids: dict[str, str] = field(default_factory=dict)
    fields_of_study: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PaperSummary:
    short_summary: str
    key_points: list[str]
    method_tags: list[str]
    relevance: str
    reading_priority: str
    topic_tags: list[str] = field(default_factory=list)
    deep_summary: str = ""
    contribution: str = ""
    method: str = ""
    experiments: str = ""
    limitations: str = ""
    reading_notes: str = ""
    llm_model: str = ""
    llm_error: str = ""
    innovation_points: list[str] = field(default_factory=list)
    method_comparison: str = ""
    datasets_used: list[str] = field(default_factory=list)
    metrics_used: list[str] = field(default_factory=list)
    future_directions: str = ""


@dataclass(frozen=True)
class SourceResult:
    source: str
    papers: list[Paper]
    error: str = ""


@dataclass(frozen=True)
class RelatedPaper:
    title: str
    source: str
    url: str
    reason: str
    score: float = 0.0


@dataclass(frozen=True)
class CitationSummary:
    citation_count: int = 0
    reference_count: int = 0
    influential_citation_count: int = 0
    citations: list[RelatedPaper] = field(default_factory=list)
    references: list[RelatedPaper] = field(default_factory=list)
