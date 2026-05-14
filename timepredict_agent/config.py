from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import ast

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    tomllib = None


DEFAULT_QUERY = (
    "(((all:time AND all:series) AND (all:forecasting OR all:prediction OR all:forecast)) "
    "OR (all:predictive AND all:process AND all:monitoring) "
    "OR (all:remaining AND all:time AND all:prediction) "
    "OR (all:process AND all:mining) "
    "OR (all:incremental AND all:event AND all:log)) "
    "AND (cat:cs.LG OR cat:stat.ML OR cat:cs.AI OR cat:cs.DB OR cat:cs.SE)"
)


@dataclass(frozen=True)
class AgentConfig:
    database_path: Path = Path("data/papers.sqlite3")
    report_dir: Path = Path("reports")
    pdf_dir: Path = Path("data/pdfs")
    query: str = DEFAULT_QUERY
    max_results: int = 80
    recent_days: int = 1095
    sources: list[str] = field(default_factory=lambda: ["arxiv", "semantic_scholar", "openalex", "ieee_xplore"])
    keywords: list[str] = field(
        default_factory=lambda: [
            "time series",
            "forecasting",
            "prediction",
            "temporal",
            "multivariate",
            "long-term",
            "predictive process monitoring",
            "event sequence",
            "event sequence prediction",
            "next event prediction",
            "next activity prediction",
            "remaining time",
            "remaining time prediction",
            "business process remaining time prediction",
            "process mining",
            "event log",
            "event log prediction",
            "incremental event log",
            "transformer",
            "business process",
            "incremental learning",
            "concept drift",
        ]
    )


def load_config(path: str | Path | None = None) -> AgentConfig:
    if path is None:
        default_path = Path("timepredict-agent.toml")
        path = default_path if default_path.exists() else None

    if path is None:
        return AgentConfig()

    text = Path(path).read_text(encoding="utf-8")
    raw = tomllib.loads(text) if tomllib else _parse_simple_toml(text)
    agent = raw.get("agent", {})
    return AgentConfig(
        database_path=Path(agent.get("database_path", "data/papers.sqlite3")),
        report_dir=Path(agent.get("report_dir", "reports")),
        pdf_dir=Path(agent.get("pdf_dir", "data/pdfs")),
        query=agent.get("query", DEFAULT_QUERY),
        max_results=int(agent.get("max_results", 80)),
        recent_days=int(agent.get("recent_days", 1095)),
        sources=list(agent.get("sources", AgentConfig().sources)),
        keywords=list(agent.get("keywords", AgentConfig().keywords)),
    )


def _parse_simple_toml(text: str) -> dict[str, dict[str, object]]:
    section = ""
    result: dict[str, dict[str, object]] = {}
    lines = iter(text.splitlines())
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            result.setdefault(section, {})
            continue
        if "=" not in stripped or not section:
            continue

        key, value = [part.strip() for part in stripped.split("=", 1)]
        if value == "[":
            items: list[str] = []
            for array_line in lines:
                array_value = array_line.strip()
                if array_value == "]":
                    break
                items.append(array_value.rstrip(","))
            result[section][key] = [ast.literal_eval(item) for item in items if item]
        else:
            result[section][key] = ast.literal_eval(value)
    return result
