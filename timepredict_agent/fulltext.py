from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import re
import ssl


class PdfDownloader:
    def __init__(self, pdf_dir: Path) -> None:
        self.pdf_dir = pdf_dir

    def download(self, pdf_url: str, paper_id: str) -> Path:
        if not pdf_url:
            raise ValueError("该论文没有可下载 PDF 链接。")
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", paper_id)
        target = self.pdf_dir / f"{safe_id}.pdf"
        if target.exists() and target.stat().st_size > 0:
            return target

        request = Request(pdf_url, headers={"User-Agent": "timepredict-agent/0.2"})
        try:
            with urlopen(request, timeout=60) as response:
                content = response.read()
        except (URLError, TimeoutError) as exc:
            if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                raise RuntimeError(f"PDF 下载失败：{exc!r}") from exc
            try:
                context = ssl._create_unverified_context()
                with urlopen(request, timeout=60, context=context) as response:
                    content = response.read()
            except (URLError, TimeoutError) as retry_exc:
                raise RuntimeError(f"PDF 下载失败：{retry_exc!r}") from retry_exc

        if not content.startswith(b"%PDF"):
            raise RuntimeError("下载结果不是有效 PDF。")
        target.write_bytes(content)
        return target


class PdfTextExtractor:
    """从 PDF 中提取文本内容，用于 LLM 分析。"""

    def extract_text(self, pdf_path: Path, max_chars: int = 15000) -> str:
        if not pdf_path.exists():
            return ""
        try:
            import pymupdf
        except ImportError:
            return ""
        try:
            doc = pymupdf.open(str(pdf_path))
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            doc.close()
            raw_text = "\n".join(pages_text)
            cleaned = self._clean_text(raw_text)
            return cleaned[:max_chars]
        except Exception:
            return ""

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"-\n(\w)", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) < 3 and stripped.isdigit():
                continue
            cleaned_lines.append(stripped)
        return "\n".join(cleaned_lines).strip()
