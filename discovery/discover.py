from __future__ import annotations

from datetime import date, datetime

from .dedupe import merge_candidates
from .scoring import evaluate_candidate
from .sources import SearchSource


def run_discovery(limit=25, categories=None, source=None):
    limit = max(1, min(int(limit), 25))
    categories = [str(value).strip() for value in (categories or ["공방", "수제 식품", "반려동물"]) if str(value).strip()][:5]
    source = source or SearchSource.from_registry()
    checked_at = date.today()
    records = []
    errors = []
    source_coverage = {}
    per_query = max(1, min(5, limit))
    for definition in source.definitions:
        coverage = source_coverage.setdefault(definition["id"], {"queries": 0, "results": 0, "errors": 0})
        direct_discover = getattr(source, "discover_direct", None)
        if callable(direct_discover):
            try:
                direct_results = direct_discover(definition["id"], per_query)
            except Exception as error:
                direct_results = None
                errors.append({"source": definition["id"], "query": "direct", "error": str(error)[:300]})
                coverage["errors"] += 1
            if direct_results is not None:
                coverage["mode"] = "direct"
                coverage["queries"] += 1
                coverage["results"] += len(direct_results)
                records.extend(direct_results)
                continue
        for template in definition.get("queries", [])[:2]:
            query = template.format(category=categories[0]) if "{category}" in template else template
            coverage["queries"] += 1
            try:
                found = source.search(query, limit=per_query)
                records.extend(found)
                coverage["results"] += len(found)
            except Exception as error:
                errors.append({"source": definition["id"], "query": query, "error": str(error)[:300]})
                coverage["errors"] += 1
            if len(records) >= limit * 2:
                break
    candidates = merge_candidates(records)[:limit]
    for candidate in candidates:
        candidate["discovery"] = evaluate_candidate(candidate, checked_at)
    reviewable = [item for item in candidates if item["discovery"]["gate_status"] != "rejected"]
    return {
        "run": {
            "status": "complete" if records or not errors else "failed",
            "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "requested_limit": limit,
            "categories": categories,
            "found": len(candidates),
            "reviewable": len(reviewable),
            "qualified": sum(item["discovery"]["gate_status"] == "qualified" for item in candidates),
            "outbound_messages_sent": 0,
            "source_coverage": source_coverage,
        },
        "candidates": candidates,
        "source_errors": errors,
    }
