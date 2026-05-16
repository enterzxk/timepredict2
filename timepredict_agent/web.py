from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import cgi
import io
import json
import mimetypes

from .agent import PaperAgent
from .config import AgentConfig
from .llm_summary import AnthropicSummaryClient
from .storage import decode_json_field, decode_summary
from .storage import decode_json_object


STATIC_DIR = Path(__file__).parent / "static"


def serve(config: AgentConfig, host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = _make_handler(config)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"TimePredict Agent UI: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def _make_handler(config: AgentConfig):
    class TimePredictHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                parsed = urlparse(self.path)
                if parsed.path == "/api/papers":
                    self._handle_list(parsed.query)
                    return
                if parsed.path == "/api/papers/resolve":
                    self._handle_resolve_paper(parsed.query)
                    return
                if parsed.path == "/api/daily-recommendations":
                    self._handle_daily_recommendations(parsed.query)
                    return
                if parsed.path.startswith("/api/papers/"):
                    self._handle_show(unquote(parsed.path.rsplit("/", 1)[-1]))
                    return
                if parsed.path == "/api/status":
                    llm = AnthropicSummaryClient()
                    self._send_json(
                        {
                            "database_path": str(config.database_path),
                            "report_dir": str(config.report_dir),
                            "pdf_dir": str(config.pdf_dir),
                            "max_results": config.max_results,
                            "recent_days": config.recent_days,
                            "sources": config.sources,
                            "llm_available": llm.available(),
                            "llm_model": llm.model,
                        }
                    )
                    return
                if parsed.path.startswith("/reports/"):
                    self._serve_file(Path(".") / parsed.path.lstrip("/"))
                    return
                self._serve_static(parsed.path)
            except Exception as exc:
                self._send_json({"error": f"服务器处理请求失败：{exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_POST(self) -> None:
            try:
                parsed = urlparse(self.path)
                if parsed.path == "/api/collect":
                    self._handle_collect()
                    return
                if parsed.path == "/api/export":
                    self._handle_export()
                    return
                if parsed.path == "/api/review":
                    self._handle_review()
                    return
                if parsed.path == "/api/papers/manual":
                    self._handle_manual_paper()
                    return
                if parsed.path == "/api/papers/upload":
                    self._handle_upload_paper()
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/download"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_download(paper_id)
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/enrich"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_enrich(paper_id)
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/recommend"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_recommend(paper_id)
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/innovation-advice"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_innovation_advice(paper_id)
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/expert-chat"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_expert_chat(paper_id)
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/llm-summary"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_llm_summary(paper_id)
                    return
                if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/local-summary"):
                    paper_id = unquote(parsed.path.split("/")[-2])
                    self._handle_local_summary(paper_id)
                    return
                if parsed.path == "/api/papers/batch-llm-summary":
                    self._handle_batch_llm_summary()
                    return
                if parsed.path == "/api/papers/batch-download":
                    self._handle_batch_download()
                    return
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self._send_json({"error": f"服务器处理请求失败：{exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, format: str, *args) -> None:
            return

        def _handle_list(self, query_string: str) -> None:
            params = parse_qs(query_string)
            keyword = params.get("keyword", [""])[0].strip()
            limit = _to_int(params.get("limit", ["50"])[0], 50)
            agent = PaperAgent(config)
            try:
                rows = (
                    agent.store.search_papers(keyword, limit)
                    if keyword
                    else agent.store.list_papers(limit)
                )
                self._send_json({"papers": [_row_to_dict(row) for row in rows]})
            finally:
                agent.close()

        def _handle_show(self, arxiv_id: str) -> None:
            agent = PaperAgent(config)
            try:
                row = agent.store.find_paper(arxiv_id)
                if row is None:
                    self._send_json({"error": "Paper not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"paper": _row_to_dict(row)})
            finally:
                agent.close()

        def _handle_resolve_paper(self, query_string: str) -> None:
            params = parse_qs(query_string)
            paper_id = params.get("paper_id", [""])[0].strip()
            title = params.get("title", [""])[0].strip()
            url = params.get("url", [""])[0].strip()
            agent = PaperAgent(config)
            try:
                row = agent.store.find_paper(paper_id) if paper_id else None
                if row is None:
                    row = agent.store.find_paper_by_title_or_url(title=title, url=url)
                if row is None:
                    self._send_json({"error": "Paper not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"paper": _row_to_dict(row)})
            finally:
                agent.close()

        def _handle_daily_recommendations(self, query_string: str) -> None:
            params = parse_qs(query_string)
            limit = _to_int(params.get("limit", ["10"])[0], 10)
            force = params.get("force", ["0"])[0] in {"1", "true", "yes"}
            agent = PaperAgent(config)
            try:
                self._send_json(agent.daily_recommendations(limit=limit, force=force))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            finally:
                agent.close()

        def _handle_collect(self) -> None:
            payload = self._read_json()
            active_config = config
            if payload.get("sources"):
                active_config = type(config)(
                    database_path=config.database_path,
                    report_dir=config.report_dir,
                    pdf_dir=config.pdf_dir,
                    query=config.query,
                    max_results=config.max_results,
                    recent_days=config.recent_days,
                    sources=payload.get("sources"),
                    keywords=config.keywords,
                )
            agent = PaperAgent(active_config)
            try:
                result = agent.collect(
                    query=payload.get("query") or None,
                    max_results=_optional_int(payload.get("max_results")),
                    recent_days=_optional_int(payload.get("recent_days")),
                )
                self._send_json(
                    {
                        "result": result.__dict__,
                        "papers": [],
                    }
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            finally:
                agent.close()

        def _handle_export(self) -> None:
            payload = self._read_json()
            output = Path(payload.get("output") or "reports/papers.md")
            limit = _to_int(payload.get("limit"), 50)
            agent = PaperAgent(config)
            try:
                path = agent.export_markdown(output, limit)
                self._send_json({"path": str(path), "url": f"/{path.as_posix()}"})
            finally:
                agent.close()

        def _handle_review(self) -> None:
            payload = self._read_json()
            paper_ids = payload.get("paper_ids", [])
            topic = payload.get("topic") or "事件序列预测与预测性流程监控"
            agent = PaperAgent(config)
            try:
                result = agent.generate_literature_review(
                    paper_ids=paper_ids,
                    topic=topic,
                    prefer_llm=bool(payload.get("prefer_llm", True)),
                )
                self._send_json(result)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            finally:
                agent.close()

        def _handle_manual_paper(self) -> None:
            payload = self._read_json()
            agent = PaperAgent(config)
            try:
                row = agent.add_manual_paper(payload)
                self._send_json({"paper": _row_to_dict(row)})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            finally:
                agent.close()

        def _handle_upload_paper(self) -> None:
            try:
                filename, content, payload = self._read_multipart_upload()
                agent = PaperAgent(config)
                try:
                    result = agent.add_uploaded_paper(filename, content, payload)
                finally:
                    agent.close()
                self._send_json(
                    {
                        "paper": _row_to_dict(result["paper"]),
                        "related": result["related"],
                        "pdf_text_available": result["pdf_text_available"],
                    }
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def _handle_download(self, paper_id: str) -> None:
            agent = PaperAgent(config)
            try:
                path = agent.download_fulltext(paper_id)
                self._send_json({"path": str(path)})
            except (RuntimeError, ValueError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            finally:
                agent.close()

        def _handle_enrich(self, paper_id: str) -> None:
            agent = PaperAgent(config)
            try:
                agent.enrich_citations(paper_id)
                row = agent.store.find_paper(paper_id)
                self._send_json({"paper": _row_to_dict(row)})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            finally:
                agent.close()

        def _handle_recommend(self, paper_id: str) -> None:
            payload = self._read_json()
            agent = PaperAgent(config)
            try:
                related = agent.recommend_similar(paper_id, _to_int(payload.get("limit"), 8))
                self._send_json({"related": related})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            finally:
                agent.close()

        def _handle_innovation_advice(self, paper_id: str) -> None:
            payload = self._read_json()
            agent = PaperAgent(config)
            try:
                result = agent.generate_innovation_advice(paper_id, _to_int(payload.get("limit"), 8))
                self._send_json(result)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            finally:
                agent.close()

        def _handle_expert_chat(self, paper_id: str) -> None:
            payload = self._read_json()
            question = str(payload.get("question") or "").strip()
            if not question:
                self._send_json({"error": "请输入想问论文专家的问题。"}, HTTPStatus.BAD_REQUEST)
                return
            agent = PaperAgent(config)
            try:
                result = agent.ask_paper_expert(
                    paper_id,
                    question,
                    include_github=bool(payload.get("include_github", False)),
                    github_limit=_to_int(payload.get("github_limit"), 5),
                    prefer_llm=bool(payload.get("prefer_llm", True)),
                    history=payload.get("history") if isinstance(payload.get("history"), list) else [],
                )
                self._send_json(result)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            finally:
                agent.close()

        def _handle_llm_summary(self, paper_id: str) -> None:
            agent = PaperAgent(config)
            try:
                agent.generate_llm_summary(paper_id)
                row = agent.store.find_paper(paper_id)
                self._send_json({"paper": _row_to_dict(row)})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            finally:
                agent.close()

        def _handle_local_summary(self, paper_id: str) -> None:
            agent = PaperAgent(config)
            try:
                agent.refresh_local_summary(paper_id)
                row = agent.store.find_paper(paper_id)
                self._send_json({"paper": _row_to_dict(row)})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            finally:
                agent.close()

        def _handle_batch_llm_summary(self) -> None:
            payload = self._read_json()
            paper_ids = payload.get("paper_ids", [])
            if not paper_ids:
                self._send_json({"error": "No paper IDs provided"}, HTTPStatus.BAD_REQUEST)
                return
            results = []
            agent = PaperAgent(config)
            try:
                for paper_id in paper_ids:
                    try:
                        agent.generate_llm_summary(paper_id)
                        results.append({"paper_id": paper_id, "status": "ok"})
                    except (ValueError, RuntimeError) as exc:
                        results.append({"paper_id": paper_id, "status": "error", "error": str(exc)})
                self._send_json({"results": results})
            finally:
                agent.close()

        def _handle_batch_download(self) -> None:
            payload = self._read_json()
            paper_ids = payload.get("paper_ids", [])
            if not paper_ids:
                self._send_json({"error": "No paper IDs provided"}, HTTPStatus.BAD_REQUEST)
                return
            results = []
            agent = PaperAgent(config)
            try:
                for paper_id in paper_ids:
                    try:
                        path = agent.download_fulltext(paper_id)
                        results.append({"paper_id": paper_id, "status": "ok", "path": str(path)})
                    except (ValueError, RuntimeError) as exc:
                        results.append({"paper_id": paper_id, "status": "error", "error": str(exc)})
                self._send_json({"results": results})
            finally:
                agent.close()

        def _read_json(self) -> dict:
            length = _to_int(self.headers.get("Content-Length"), 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw or "{}")

        def _read_multipart_upload(self) -> tuple[str, bytes, dict]:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                raise ValueError("请使用 multipart/form-data 上传 PDF。")
            length = _to_int(self.headers.get("Content-Length"), 0)
            if length <= 0:
                raise ValueError("上传内容为空。")
            body = self.rfile.read(length)
            environ = {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": str(length),
            }
            form = cgi.FieldStorage(
                fp=io.BytesIO(body),
                headers=self.headers,
                environ=environ,
                keep_blank_values=True,
            )
            file_item = form["file"] if "file" in form else None
            if file_item is None or not getattr(file_item, "filename", ""):
                raise ValueError("请选择要上传的 PDF 文件。")
            content = file_item.file.read()
            payload = {}
            for key in ("title", "authors", "year", "abstract", "tags"):
                if key in form:
                    payload[key] = form.getvalue(key)
            return file_item.filename, content, payload

        def _serve_static(self, path: str) -> None:
            relative = "index.html" if path in ("", "/") else path.lstrip("/")
            self._serve_file(STATIC_DIR / relative)

        def _serve_file(self, path: Path) -> None:
            try:
                resolved = path.resolve()
                if not resolved.exists() or resolved.is_dir():
                    self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                    return
                content = resolved.read_bytes()
                content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
                if resolved.suffix in {".html", ".css", ".js"}:
                    content_type = f"{content_type}; charset=utf-8"
                if resolved.suffix == ".md":
                    content_type = "text/markdown; charset=utf-8"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except OSError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return TimePredictHandler


def _row_to_dict(row) -> dict:
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


def _to_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    return _to_int(value, 0)
