from timepredict_agent.models import Paper
from timepredict_agent.agent import _queries_for_source
from timepredict_agent.sources import (
    GoogleScholarSource,
    _GoogleScholarHtmlParser,
    _dedupe_papers,
    _ieee_public_to_paper,
    _looks_relevant_to_time_series,
    _openalex_abstract,
    _plain_query,
    build_sources,
)
from timepredict_agent.tagger import ccf_rank, classify_paper
import unittest


class SourcesAndTagsTest(unittest.TestCase):
    def test_build_sources_skips_unknown_names(self):
        sources = build_sources(["arxiv", "missing", "google_scholar", "openalex"])

        self.assertEqual([source.name for source in sources], ["arxiv", "google_scholar", "openalex"])

    def test_google_scholar_returns_compliant_search_entry(self):
        result = GoogleScholarSource().search("time series forecasting", 5, None)

        self.assertEqual(result.papers, [])
        self.assertIn("scholar.google.com", result.error)

    def test_google_scholar_html_parser_extracts_saved_results(self):
        parser = _GoogleScholarHtmlParser(max_results=5)
        parser.feed(
            """
            <div class="gs_ri">
              <h3 class="gs_rt"><a href="https://example.com/paper">A Time Series Forecasting Paper</a></h3>
              <div class="gs_a">A Author, B Author - ICML, 2024 - example.com</div>
              <div class="gs_rs">We study long-term forecasting with transformers.</div>
            </div>
            """
        )

        self.assertEqual(len(parser.papers), 1)
        self.assertEqual(parser.papers[0].source, "google_scholar")
        self.assertEqual(parser.papers[0].year, 2024)
        self.assertIn("Forecasting", parser.papers[0].title)

    def test_ieee_public_record_maps_to_paper(self):
        paper = _ieee_public_to_paper(
            {
                "articleNumber": "123",
                "articleTitle": "<b>Forecasting</b> with IEEE",
                "publicationYear": "2023",
                "publicationTitle": "IEEE Transactions",
                "documentLink": "/document/123",
                "authors": [{"preferredName": "Ada Lovelace"}],
            }
        )

        self.assertEqual(paper.source, "ieee_xplore")
        self.assertEqual(paper.arxiv_id, "ieee:123")
        self.assertEqual(paper.title, "Forecasting with IEEE")
        self.assertTrue(paper.entry_url.startswith("https://ieeexplore.ieee.org"))

    def test_openalex_abstract_reconstructs_inverted_index(self):
        abstract = _openalex_abstract({"Forecasting": [1], "Time": [0], "works": [2]})

        self.assertEqual(abstract, "Time Forecasting works")

    def test_plain_query_removes_arxiv_categories(self):
        query = _plain_query("((all:time AND all:series) AND cat:cs.LG OR cat:stat.ML)")

        self.assertEqual(query, "time series")

    def test_relevance_filter_keeps_time_series_papers(self):
        paper = Paper(
            arxiv_id="x",
            title="Long-term Time Series Forecasting",
            abstract="",
            authors=[],
            published="",
            updated="",
            entry_url="",
            pdf_url="",
        )

        self.assertTrue(_looks_relevant_to_time_series(paper))

    def test_source_dedupe_removes_same_title(self):
        paper = Paper(
            arxiv_id="x",
            title="Long-term Time Series Forecasting",
            abstract="",
            authors=[],
            published="",
            updated="",
            entry_url="",
            pdf_url="",
        )

        self.assertEqual(len(_dedupe_papers([paper, paper])), 1)

    def test_non_arxiv_sources_use_event_sequence_query_expansion(self):
        queries = _queries_for_source("openalex", "base query", explicit_query=False)

        self.assertIn("event sequence prediction", queries)
        self.assertIn("remaining time prediction process mining", queries)
        self.assertEqual(_queries_for_source("arxiv", "base query", explicit_query=False), ["base query"])

    def test_classify_paper_adds_topic_and_ccf_tags(self):
        paper = Paper(
            arxiv_id="x",
            title="Transformer Foundation Model for Predictive Process Monitoring",
            abstract="We study probabilistic multivariate forecasting for remaining time prediction over incremental event logs.",
            authors=[],
            published="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
            entry_url="",
            pdf_url="",
            venue="ICML",
        )

        tags = classify_paper(paper)

        self.assertIn("Transformer", tags)
        self.assertIn("Foundation model", tags)
        self.assertIn("Predictive process monitoring", tags)
        self.assertIn("Remaining time prediction", tags)
        self.assertIn("Incremental event log", tags)
        self.assertIn("CCF-A", tags)
        self.assertEqual(ccf_rank("Proceedings of ICML"), "CCF-A")


if __name__ == "__main__":
    unittest.main()
