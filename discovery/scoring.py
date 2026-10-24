from __future__ import annotations

from datetime import date, datetime


WEIGHTS = {
    "own_products": 20,
    "recent_activity": 15,
    "channel_gap": 20,
    "workload_complexity": 15,
    "category_expansion": 15,
    "contactability": 10,
    "evidence_quality": 5,
}


def _parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def evaluate_candidate(candidate: dict, today: date | None = None) -> dict:
    today = today or date.today()
    unknowns = []
    rejected_reasons = []
    components = {key: 0 for key in WEIGHTS}

    if candidate.get("stopped") is True:
        rejected_reasons.append("영업 중단 또는 폐업 신호")
    if candidate.get("reseller_only") is True:
        rejected_reasons.append("자체상품 없는 단순 리셀러")

    activity = _parse_date(candidate.get("last_activity_at"))
    if activity is None:
        unknowns.append("last_activity_at")
    else:
        age = (today - activity).days
        if age < 0:
            unknowns.append("last_activity_at")
        elif age <= 60:
            components["recent_activity"] = WEIGHTS["recent_activity"]
        else:
            rejected_reasons.append("최근 공개 활동이 60일을 초과")

    own_count = candidate.get("own_product_count")
    if own_count is None:
        unknowns.append("own_product_count")
    elif isinstance(own_count, int) and own_count > 0:
        components["own_products"] = WEIGHTS["own_products"]

    gap = candidate.get("observed_channel_gap")
    if gap is True:
        components["channel_gap"] = WEIGHTS["channel_gap"]
    elif gap is None:
        unknowns.append("observed_channel_gap")

    workloads = candidate.get("workload_signals") or []
    if workloads:
        components["workload_complexity"] = WEIGHTS["workload_complexity"]
    else:
        unknowns.append("workload_signals")

    expansions = candidate.get("expansion_signals") or []
    if expansions:
        components["category_expansion"] = WEIGHTS["category_expansion"]
    else:
        unknowns.append("expansion_signals")

    contact = candidate.get("public_contact") or {}
    if contact.get("value") and contact.get("url"):
        components["contactability"] = WEIGHTS["contactability"]
    else:
        unknowns.append("public_contact")

    evidence = candidate.get("evidence") or []
    fresh_evidence = [item for item in evidence if _parse_date(item.get("checked_at")) and (today - _parse_date(item.get("checked_at"))).days <= 30]
    if len({item.get("url") for item in fresh_evidence if item.get("url")}) >= 2:
        components["evidence_quality"] = WEIGHTS["evidence_quality"]
    else:
        unknowns.append("evidence_quality")

    official_url = candidate.get("official_url")
    if not official_url:
        unknowns.append("official_url")

    score = sum(components.values())
    has_contact = components["contactability"] > 0
    has_official = bool(official_url)
    has_current_activity = components["recent_activity"] > 0
    if rejected_reasons:
        gate_status = "rejected"
    elif not (has_contact and has_official and has_current_activity):
        gate_status = "needs_research"
    elif score >= 70:
        gate_status = "qualified"
    else:
        gate_status = "needs_research"

    reasons = [f"{key}: +{value}" for key, value in components.items() if value]
    return {
        "fit_score": score,
        "components": components,
        "gate_status": gate_status,
        "outreach_eligible": gate_status == "qualified" and has_contact,
        "reasons": reasons,
        "rejected_reasons": rejected_reasons,
        "unknowns": sorted(set(unknowns)),
    }
