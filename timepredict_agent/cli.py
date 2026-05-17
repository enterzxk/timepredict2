from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json

from .agent import PaperAgent
from .config import load_config
from .storage import decode_json_field, decode_summary, migrate_sqlite_to_mysql


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="timepredict-agent",
        description="Collect and summarize recent time-series forecasting papers.",
    )
    parser.add_argument("--config", help="Path to timepredict-agent TOML config.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect recent papers from enabled sources.")
    collect.add_argument("--query", help="Override source query.")
    collect.add_argument("--max-results", type=int, help="Maximum results per source.")
    collect.add_argument("--recent-days", type=int, help="Only keep papers newer than N days.")
    collect.add_argument(
        "--sources",
        help="Comma-separated sources: arxiv,semantic_scholar,openalex,ieee_xplore,google_scholar.",
    )

    list_cmd = subparsers.add_parser("list", help="List collected papers.")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument("--keyword", help="Search in title, abstract, and summaries.")

    show = subparsers.add_parser("show", help="Show one paper by arXiv id.")
    show.add_argument("arxiv_id")

    export = subparsers.add_parser("export", help="Export a Markdown reading report.")
    export.add_argument("--output", default="reports/papers.md")
    export.add_argument("--limit", type=int, default=50)

    download = subparsers.add_parser("download", help="Download a paper PDF.")
    download.add_argument("paper_id")

    enrich = subparsers.add_parser("enrich", help="Fetch citation/reference data.")
    enrich.add_argument("paper_id")

    recommend = subparsers.add_parser("recommend", help="Recommend similar papers.")
    recommend.add_argument("paper_id")
    recommend.add_argument("--limit", type=int, default=8)

    llm_summary = subparsers.add_parser("llm-summary", help="Generate an LLM deep summary.")
    llm_summary.add_argument("paper_id")

    local_summary = subparsers.add_parser("local-summary", help="Regenerate the local Chinese summary.")
    local_summary.add_argument("paper_id")

    schedule = subparsers.add_parser("schedule", help="Run automatic collection on an interval.")
    schedule.add_argument("--interval-minutes", type=int, default=1440)

    web = subparsers.add_parser("web", help="Start the local visual dashboard.")
    web.add_argument("--host", default="0.0.0.0")
    web.add_argument("--port", type=int, default=8765)

    migrate = subparsers.add_parser("migrate-sqlite-to-mysql", help="Copy local SQLite data into MySQL.")
    migrate.add_argument("--sqlite-path", help="SQLite database path. Defaults to config database_path.")
    migrate.add_argument("--mysql-url", help="MySQL URL. Defaults to config database_url or TIMEPREDICT_DATABASE_URL.")

    subparsers.add_parser("init-config", help="Print an example config.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        print(EXAMPLE_CONFIG)
        return

    config = load_config(args.config)
    if args.command == "web":
        from .web import serve

        serve(config, args.host, args.port)
        return
    if args.command == "schedule":
        from .scheduler import run_scheduler

        run_scheduler(config, args.interval_minutes)
        return
    if args.command == "migrate-sqlite-to-mysql":
        sqlite_path = Path(args.sqlite_path) if args.sqlite_path else config.database_path
        mysql_url = args.mysql_url or config.database_url
        if not mysql_url:
            raise SystemExit("MySQL URL is required: pass --mysql-url or set database_url/TIMEPREDICT_DATABASE_URL.")
        result = migrate_sqlite_to_mysql(sqlite_path, mysql_url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    agent = PaperAgent(config)
    try:
        if args.command == "collect":
            if args.sources:
                config = type(config)(
                    database_path=config.database_path,
                    database_backend=config.database_backend,
                    database_url=config.database_url,
                    report_dir=config.report_dir,
                    pdf_dir=config.pdf_dir,
                    query=config.query,
                    max_results=config.max_results,
                    recent_days=config.recent_days,
                    sources=[item.strip() for item in args.sources.split(",") if item.strip()],
                    keywords=config.keywords,
                )
                agent.close()
                agent = PaperAgent(config)
            try:
                result = agent.collect(args.query, args.max_results, args.recent_days)
            except RuntimeError as exc:
                raise SystemExit(str(exc)) from exc
            print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        elif args.command == "list":
            rows = (
                agent.store.search_papers(args.keyword, args.limit)
                if args.keyword
                else agent.store.list_papers(args.limit)
            )
            for row in rows:
                summary = decode_summary(row)
                print(
                    f"{row['published'][:10]} | {row['arxiv_id']} | "
                    f"{summary.reading_priority.upper()} | {row['title']}"
                )
        elif args.command == "show":
            row = agent.store.find_paper(args.arxiv_id)
            if row is None:
                raise SystemExit(f"Paper not found: {args.arxiv_id}")
            _print_paper(row)
        elif args.command == "export":
            path = agent.export_markdown(Path(args.output), args.limit)
            print(f"Exported: {path}")
        elif args.command == "download":
            path = agent.download_fulltext(args.paper_id)
            print(f"Downloaded: {path}")
        elif args.command == "enrich":
            agent.enrich_citations(args.paper_id)
            print(f"Enriched citations: {args.paper_id}")
        elif args.command == "recommend":
            related = agent.recommend_similar(args.paper_id, args.limit)
            print(json.dumps({"related": related}, ensure_ascii=False, indent=2))
        elif args.command == "llm-summary":
            try:
                result = agent.generate_llm_summary(args.paper_id)
            except RuntimeError as exc:
                raise SystemExit(str(exc)) from exc
            print(json.dumps({"paper_id": result["paper_id"], "model": result["model"]}, ensure_ascii=False, indent=2))
        elif args.command == "local-summary":
            result = agent.refresh_local_summary(args.paper_id)
            print(json.dumps({"paper_id": result["paper_id"]}, ensure_ascii=False, indent=2))
    finally:
        agent.close()


def _print_paper(row) -> None:
    summary = decode_summary(row)
    authors = ", ".join(decode_json_field(row, "authors_json"))
    categories = ", ".join(decode_json_field(row, "categories_json"))
    print(f"# {row['title']}")
    print(f"ID: {row['arxiv_id']}")
    print(f"Source: {row['source']}")
    print(f"Published: {row['published'][:10]}")
    print(f"Authors: {authors}")
    print(f"Categories: {categories}")
    if row["venue"]:
        print(f"Venue: {row['venue']}")
    if row["doi"]:
        print(f"DOI: {row['doi']}")
    print(f"Citations: {row['citation_count'] or 0}")
    if row["local_pdf_path"]:
        print(f"Local PDF: {row['local_pdf_path']}")
    print(f"PDF: {row['pdf_url']}")
    print()
    print(f"Priority: {summary.reading_priority}")
    print(f"Summary: {summary.short_summary}")
    print(f"Relevance: {summary.relevance}")
    print("Key points:")
    for point in summary.key_points:
        print(f"- {point}")


EXAMPLE_CONFIG = """[agent]
database_path = "data/papers.sqlite3"
database_backend = "sqlite"
database_url = ""
report_dir = "reports"
pdf_dir = "data/pdfs"
max_results = 80
recent_days = 1095
sources = ["arxiv", "semantic_scholar", "openalex", "ieee_xplore"]
query = '(((all:time AND all:series) AND (all:forecasting OR all:prediction OR all:forecast)) OR (all:predictive AND all:process AND all:monitoring) OR (all:remaining AND all:time AND all:prediction) OR (all:process AND all:mining) OR (all:incremental AND all:event AND all:log)) AND (cat:cs.LG OR cat:stat.ML OR cat:cs.AI OR cat:cs.DB OR cat:cs.SE)'
keywords = [
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
"""
