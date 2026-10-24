from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import urlparse


def normalize_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def normalize_email(value: str | None) -> str:
    return (value or "").strip().casefold()


def root_domain(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").casefold()
    return host.removeprefix("www.")


def url_identity(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    parts = [part.casefold() for part in parsed.path.split("/") if part]
    hosted = {
        "smartstore.naver.com", "instagram.com", "tumblbug.com", "wadiz.kr", "wadiz.io",
        "k-handmade.com", "seoul.designfestival.co.kr", "fanfandaero.kr",
    }
    if host in hosted and parts:
        return f"{host}/{'/'.join(parts)}"
    return host


def stable_lead_id(candidate: dict) -> str:
    contact = normalize_email((candidate.get("public_contact") or {}).get("value"))
    identity = contact or url_identity(candidate.get("official_url")) or normalize_name(candidate.get("brand_name"))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"lead-{digest}"
