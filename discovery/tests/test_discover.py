import unittest

from discovery.discover import run_discovery


class FakeSource:
    definitions = [{"id": "smartstore", "queries": ["site:smartstore.naver.com 수제 공방 자체제작"]}]

    def __init__(self):
        self.queries = []

    def search(self, query, limit=10):
        self.queries.append(query)
        return []


class DiscoveryTests(unittest.TestCase):
    def test_registry_query_is_not_overconstrained_by_all_categories(self):
        source = FakeSource()
        result = run_discovery(limit=5, categories=["공방", "반려동물", "생활소품"], source=source)
        self.assertEqual(source.queries, ["site:smartstore.naver.com 수제 공방 자체제작"])
        self.assertEqual(result["run"]["source_coverage"]["smartstore"], {"queries": 1, "results": 0, "errors": 0})

    def test_direct_source_replaces_search_queries_when_available(self):
        class DirectSource:
            definitions = [{"id": "wadiz", "queries": ["site:wadiz.kr ignored"]}]

            def discover_direct(self, source_id, limit):
                return [{"brand_name": "직접 수집 메이커", "official_url": "https://www.wadiz.io/web/campaign/detail/1", "evidence": []}]

            def search(self, query, limit=10):
                raise AssertionError("direct source must not fall back to web search")

        result = run_discovery(limit=5, source=DirectSource())
        self.assertEqual(result["candidates"][0]["brand_name"], "직접 수집 메이커")
        self.assertEqual(result["run"]["source_coverage"]["wadiz"]["mode"], "direct")


if __name__ == "__main__":
    unittest.main()
