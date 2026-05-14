from pathlib import Path
from tempfile import TemporaryDirectory
from timepredict_agent.fulltext import PdfDownloader
import unittest


class FulltextTest(unittest.TestCase):
    def test_download_accepts_file_url_pdf(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            source.write_bytes(b"%PDF-1.4\n%test\n")

            path = PdfDownloader(root / "pdfs").download(source.as_uri(), "paper:1")

            self.assertTrue(path.exists())
            self.assertTrue(path.read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

