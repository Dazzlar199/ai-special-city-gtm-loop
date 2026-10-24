import json
import tempfile
import unittest
from pathlib import Path

from discovery.dedupe import merge_candidates
from discovery.store import DiscoveryStore


class DedupeTests(unittest.TestCase):
    def test_same_normalized_name_merges_and_unions_evidence(self):
        merged = merge_candidates([
            {"brand_name": "마옴 집", "official_url": "https://maom.example", "evidence": [{"url": "https://a.example"}]},
            {"brand_name": "마옴집", "official_url": "https://maom.example/about", "evidence": [{"url": "https://b.example"}]},
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual({item["url"] for item in merged[0]["evidence"]}, {"https://a.example", "https://b.example"})
        self.assertTrue(merged[0]["id"].startswith("lead-"))

    def test_same_contact_email_merges_different_names(self):
        merged = merge_candidates([
            {"brand_name": "공방 하나", "public_contact": {"value": "HELLO@example.com"}, "evidence": []},
            {"brand_name": "하나 스튜디오", "public_contact": {"value": "hello@example.com"}, "evidence": []},
        ])
        self.assertEqual(len(merged), 1)

    def test_distinct_marketplace_sellers_do_not_merge_by_host_domain(self):
        merged = merge_candidates([
            {"brand_name": "호재목 공방", "official_url": "https://smartstore.naver.com/hojea", "evidence": []},
            {"brand_name": "요고키친", "official_url": "https://smartstore.naver.com/yogoh", "evidence": []},
            {"brand_name": "누노공방", "official_url": "https://www.instagram.com/nuno_workroom/", "evidence": []},
            {"brand_name": "다른공방", "official_url": "https://www.instagram.com/other_workroom/", "evidence": []},
        ])
        self.assertEqual(len(merged), 4)

    def test_distinct_directory_profiles_do_not_merge_by_shared_path_prefix(self):
        merged = merge_candidates([
            {"brand_name": "메이커 하나", "official_url": "https://www.wadiz.kr/web/maker/detail/111/makerInfo", "evidence": []},
            {"brand_name": "메이커 둘", "official_url": "https://www.wadiz.kr/web/maker/detail/222/makerInfo", "evidence": []},
            {"brand_name": "전시 브랜드 하나", "official_url": "https://seoul.designfestival.co.kr/exhibition/brand-one/", "evidence": []},
            {"brand_name": "전시 브랜드 둘", "official_url": "https://seoul.designfestival.co.kr/exhibition/brand-two/", "evidence": []},
            {"brand_name": "와디즈 메이커 하나", "official_url": "https://www.wadiz.io/web/campaign/detail/111", "evidence": []},
            {"brand_name": "와디즈 메이커 둘", "official_url": "https://www.wadiz.io/web/campaign/detail/222", "evidence": []},
        ])
        self.assertEqual(len(merged), 6)


class StoreTests(unittest.TestCase):
    def test_round_trip_preserves_run_metadata_and_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            store = DiscoveryStore(path)
            payload = {"run": {"status": "complete"}, "candidates": [{"id": "lead-1"}], "source_errors": []}
            store.write(payload)
            self.assertEqual(store.read(), payload)

    def test_malformed_json_is_reported_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            path.write_text("{broken", encoding="utf-8")
            store = DiscoveryStore(path)
            with self.assertRaises(ValueError):
                store.read()
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
