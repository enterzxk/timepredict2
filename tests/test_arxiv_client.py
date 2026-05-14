from timepredict_agent.arxiv_client import ArxivClient
import unittest


SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2501.00003v1</id>
    <updated>2025-01-02T00:00:00Z</updated>
    <published>2025-01-01T00:00:00Z</published>
    <title>Sample Time Series Forecasting Paper</title>
    <summary>We introduce a method for time series forecasting.</summary>
    <author><name>A. Researcher</name></author>
    <category term="cs.LG" />
    <link title="pdf" href="http://arxiv.org/pdf/2501.00003v1" />
  </entry>
</feed>
"""


class ArxivClientTest(unittest.TestCase):
    def test_parse_feed_returns_papers(self):
        papers = ArxivClient()._parse_feed(SAMPLE_FEED)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].arxiv_id, "2501.00003v1")
        self.assertEqual(papers[0].title, "Sample Time Series Forecasting Paper")
        self.assertEqual(papers[0].categories, ["cs.LG"])


if __name__ == "__main__":
    unittest.main()

