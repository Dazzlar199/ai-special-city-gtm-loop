import unittest

from discovery.sources import (
    SearchSource, classify_url, extract_public_business_email,
    extract_search_results, is_candidate_url, parse_wadiz_projects,
    prioritize_wadiz_candidates,
)


HTML = """
<html><body>
  <a class="result__a" href="https://smartstore.naver.com/smallbrand">작은브랜드 스마트스토어</a>
  <a class="result__a" href="https://help.sell.smartstore.naver.com/faq/content.help">스마트스토어 고객센터</a>
  <a class="result__a" href="https://solution.smartstore.naver.com/ko/solution/123">커머스솔루션마켓</a>
  <a class="result__a" href="https://www.wadiz.kr/web/campaign/detail/123">와디즈 작은브랜드</a>
  <a class="result__a" href="https://www.instagram.com/smallbrand/">작은브랜드 Instagram</a>
</body></html>
"""

NAVER_HTML = """
<html><body>
  <a href="https://inflow.pay.naver.com/rd?retUrl=https%3A%2F%2Fsmartstore.naver.com%2Fhojea">이미지 새 창 열림</a>
  <a href="https://inflow.pay.naver.com/rd?retUrl=https%3A%2F%2Fsmartstore.naver.com%2Fhojea">호재목 공방 새 창 열림</a>
  <a href="https://help.sell.smartstore.naver.com/faq">스마트스토어 고객센터</a>
  <a href="https://smartstore.naver.com/main/products/123">개별 상품</a>
  <a href="https://smartstore.naver.com/inflow/outlink/url?url=https%3A%2F%2Fsmartstore.naver.com%2Fspringpicnic">봄소풍 공방</a>
  <a href="https://k-handmade.com/seoul/notice/1">공지사항</a>
  <a href="https://seoul.designfestival.co.kr/event/extend">참가신청 기간 연장안내</a>
  <a href="https://tumblbug.com/webtoon_project">신작 웹툰 제작 프로젝트</a>
  <a href="https://smartstore.naver.com/appmaker">앱개발 대행</a>
</body></html>
"""


class SourceTests(unittest.TestCase):
    def test_classifies_supported_public_sources(self):
        self.assertEqual(classify_url("https://smartstore.naver.com/a"), "smartstore")
        self.assertEqual(classify_url("https://tumblbug.com/a"), "tumblbug")
        self.assertEqual(classify_url("https://fanfandaero.kr/a"), "fanfandaero")
        self.assertEqual(classify_url("https://www.wadiz.io/web/campaign/detail/1"), "wadiz")

    def test_extracts_bounded_results_with_evidence(self):
        rows = extract_search_results(HTML, "공방", "2026-10-24", limit=3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["source_type"], "smartstore")
        self.assertEqual(rows[0]["evidence"][0]["checked_at"], "2026-10-24")
        self.assertNotIn("스마트스토어 고객센터", [row["brand_name"] for row in rows])
        self.assertNotIn("커머스솔루션마켓", [row["brand_name"] for row in rows])

    def test_query_registry_covers_requested_and_additional_sources(self):
        source = SearchSource.from_registry()
        names = {item["id"] for item in source.definitions}
        self.assertTrue({"smartstore", "instagram", "wadiz", "tumblbug", "exhibitions", "fanfandaero"}.issubset(names))

    def test_naver_redirect_is_resolved_and_best_brand_title_is_kept(self):
        rows = extract_search_results(NAVER_HTML, "공방", "2026-10-24", limit=3)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["official_url"], "https://smartstore.naver.com/hojea")
        self.assertEqual(rows[0]["brand_name"], "호재목 공방")
        self.assertEqual(rows[1]["official_url"], "https://smartstore.naver.com/springpicnic")
        self.assertNotIn("공지사항", [row["brand_name"] for row in rows])
        self.assertFalse(any("웹툰" in row["brand_name"] or "앱개발" in row["brand_name"] for row in rows))

    def test_default_search_endpoint_is_naver(self):
        self.assertIn("search.naver.com", SearchSource.from_registry().endpoint)

    def test_platform_editorial_and_directory_shell_pages_are_rejected(self):
        rejected = [
            "https://creator.tumblbug.com/article/1",
            "https://tumblbug.com/",
            "https://seoul.designfestival.co.kr/",
            "https://seoul.designfestival.co.kr/en/participation/brand-promotion/",
            "https://k-handmade.com/seoul/page/23",
            "https://fanfandaero.kr/portal/v2/introV2.do",
        ]
        self.assertTrue(all(not is_candidate_url(url) for url in rejected))
        self.assertTrue(is_candidate_url("https://tumblbug.com/small_brand"))
        self.assertTrue(is_candidate_url("https://www.wadiz.kr/web/maker/detail/1887639/makerInfo"))

    def test_wadiz_api_projects_are_normalized_and_nonphysical_projects_are_excluded(self):
        payload = {
            "status": 200,
            "data": {
                "count": 3,
                "list": [
                    {
                        "campaignId": 427004, "userId": 8388217,
                        "title": "올화이트 고양이 스크래처", "whenOpen": "2026-10-24T16:00:16+09:00",
                        "productType": "PREORDER", "nickName": "Pets Rx", "corpName": "Pets Rx",
                        "participationCnt": 1, "totalBackedAmount": 68900, "advertisement": False,
                        "isDeliveryAvailable": True, "categoryName": "고양이", "coreMessage": "인테리어형 스크래처",
                    },
                    {
                        "campaignId": 418360, "userId": 8830722,
                        "title": "유리 오브제 무드등", "whenOpen": "2026-10-23T20:00:18+09:00",
                        "productType": "REWARD", "nickName": "LULL", "corpName": "LULL",
                        "participationCnt": 37, "totalBackedAmount": 860777, "advertisement": False,
                        "isDeliveryAvailable": True, "categoryName": "인테리어", "coreMessage": "유리 별빛 무드등",
                    },
                    {
                        "campaignId": 426171, "userId": 1782621,
                        "title": "신앙생활 앱", "whenOpen": "2026-10-24T09:00:18+09:00",
                        "productType": "REWARD", "nickName": "GLOWY STUDIO", "corpName": "GLOWY STUDIO",
                        "participationCnt": 11, "totalBackedAmount": 69800, "advertisement": False,
                        "isDeliveryAvailable": True, "categoryName": "App·Web", "coreMessage": "모바일 앱",
                    },
                ],
            },
        }
        rows = parse_wadiz_projects(payload, "2026-10-24", limit=10)
        self.assertEqual([row["brand_name"] for row in rows], ["Pets Rx", "LULL"])
        self.assertEqual(rows[0]["official_url"], "https://www.wadiz.io/web/campaign/detail/427004")
        self.assertIsNone(rows[0]["maker_url"])
        self.assertEqual(rows[0]["last_activity_at"], "2026-10-24")
        self.assertIsNone(rows[0]["own_product_count"])

    def test_wadiz_story_extracts_only_public_business_email_near_contact_language(self):
        story = """
        <p>제품 및 배송 관련 문의: hello@smallbrand.co.kr</p>
        <p>결제 문의: info@wadiz.kr</p>
        <p>이미지 파일명 owner@example.com</p>
        """
        self.assertEqual(extract_public_business_email(story), "hello@smallbrand.co.kr")
        self.assertIsNone(extract_public_business_email("<p>결제 문의 info@wadiz.kr</p>"))

    def test_wadiz_candidates_with_verified_contact_are_kept_before_recent_only_rows(self):
        rows = [
            {"brand_name": "최신 후보", "public_contact": None},
            {"brand_name": "연락 가능 후보", "public_contact": {"type": "email", "value": "hello@example.com"}},
            {"brand_name": "다음 후보", "public_contact": None},
        ]
        selected = prioritize_wadiz_candidates(rows, limit=2)
        self.assertEqual([row["brand_name"] for row in selected], ["연락 가능 후보", "최신 후보"])


if __name__ == "__main__":
    unittest.main()
