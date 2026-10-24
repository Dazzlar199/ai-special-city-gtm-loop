from __future__ import annotations

from copy import deepcopy

from .models import normalize_email, normalize_name, stable_lead_id, url_identity


def _keys(record):
    keys = set()
    name = normalize_name(record.get("brand_name"))
    url_key = url_identity(record.get("official_url"))
    email = normalize_email((record.get("public_contact") or {}).get("value"))
    if name:
        keys.add(("name", name))
    if url_key:
        keys.add(("url", url_key))
    if email and "@" in email:
        keys.add(("email", email))
    return keys


def _merge_evidence(left, right):
    merged = []
    seen = set()
    for item in [*(left or []), *(right or [])]:
        key = (item.get("url"), item.get("kind"), item.get("excerpt"))
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def _merge_record(target, incoming):
    target["evidence"] = _merge_evidence(target.get("evidence"), incoming.get("evidence"))
    for key, value in incoming.items():
        if key == "evidence":
            continue
        if target.get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
            target[key] = deepcopy(value)
    target["id"] = target.get("id") or incoming.get("id") or stable_lead_id(target)


def merge_candidates(records):
    merged = []
    record_keys = []
    for source in records:
        record = deepcopy(source)
        keys = _keys(record)
        index = next((i for i, known in enumerate(record_keys) if keys & known), None)
        if index is None:
            record["id"] = record.get("id") or stable_lead_id(record)
            merged.append(record)
            record_keys.append(keys)
        else:
            _merge_record(merged[index], record)
            record_keys[index] |= keys
    return merged
