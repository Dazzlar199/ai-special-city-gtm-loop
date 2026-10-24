import unittest
from datetime import date

from discovery.scoring import evaluate_candidate


def candidate(**overrides):
    base = {
        "brand_name": "테스트공방",
        "official_url": "https://example.com",
        "category": "생활소품",
        "own_product_count": 7,
        "last_activity_at": "2026-10-01",
        "marketplace_urls": ["https://smartstore.naver.com/test"],
        "observed_channel_gap": True,
        "workload_signals": ["제작", "오프라인 클래스"],
        "expansion_signals": ["선물세트", "연관 생활용품"],
        "public_contact": {"type": "email", "value": "hello@example.com", "url": "mailto:hello@example.com"},
        "evidence": [
            {"kind": "official", "url": "https://example.com", "checked_at": "2026-10-24"},
            {"kind": "store", "url": "https://smartstore.naver.com/test", "checked_at": "2026-10-24"},
        ],
        "stopped": False,
        "reseller_only": False,
    }
    base.update(overrides)
    return base


class ScoringTests(unittest.TestCase):
    def test_complete_public_evidence_scores_100(self):
        result = evaluate_candidate(candidate(), date(2026, 10, 24))
        self.assertEqual(result["fit_score"], 100)
        self.assertEqual(result["gate_status"], "qualified")
        self.assertTrue(result["outreach_eligible"])

    def test_unknown_fields_receive_no_points_and_are_named(self):
        result = evaluate_candidate(candidate(
            own_product_count=None,
            observed_channel_gap=None,
            workload_signals=[],
            expansion_signals=[],
        ), date(2026, 10, 24))
        self.assertEqual(result["fit_score"], 30)
        self.assertIn("own_product_count", result["unknowns"])
        self.assertIn("observed_channel_gap", result["unknowns"])

    def test_stopped_and_reseller_only_records_are_rejected(self):
        self.assertEqual(evaluate_candidate(candidate(stopped=True), date(2026, 10, 24))["gate_status"], "rejected")
        self.assertEqual(evaluate_candidate(candidate(reseller_only=True), date(2026, 10, 24))["gate_status"], "rejected")

    def test_activity_is_current_through_60_day_boundary(self):
        at_boundary = evaluate_candidate(candidate(last_activity_at="2026-08-25"), date(2026, 10, 24))
        stale = evaluate_candidate(candidate(last_activity_at="2026-08-24"), date(2026, 10, 24))
        self.assertEqual(at_boundary["components"]["recent_activity"], 15)
        self.assertEqual(stale["gate_status"], "rejected")

    def test_missing_contact_is_reviewable_but_not_outreach_eligible(self):
        result = evaluate_candidate(candidate(public_contact=None), date(2026, 10, 24))
        self.assertEqual(result["gate_status"], "needs_research")
        self.assertFalse(result["outreach_eligible"])
        self.assertIn("public_contact", result["unknowns"])

    def test_missing_official_source_is_not_qualified(self):
        result = evaluate_candidate(candidate(official_url=None), date(2026, 10, 24))
        self.assertEqual(result["gate_status"], "needs_research")
        self.assertFalse(result["outreach_eligible"])


if __name__ == "__main__":
    unittest.main()
