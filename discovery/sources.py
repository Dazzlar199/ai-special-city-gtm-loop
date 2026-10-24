from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


REGISTRY_PATH = Path(__file__).with_name("queries.json")
USER_AGENT = "AI-Special-City-Prospect-Research/1.0 (public evidence review; ax@ai-specialtime.com)"
WADIZ_FUNDING_API = "https://api.wadiz.io/search/api/search/v2/funding"
WADIZ_EXCLUDED_CATEGORIES = {
    "App·Web", "전자책·클래스", "외국어", "부업·수익", "음악", "도서",
    "인문·교양", "만화·웹툰", "영화·영상", "여행", "멤버십", "후원",
}


def classify_url(url):
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host == "smartstore.naver.com":
        return "smartstore"
    if host in {"instagram.com", "www.instagram.com"}:
        return "instagram"
    if host in {"wadiz.kr", "www.wadiz.kr", "wadiz.io", "www.wadiz.io"}:
        return "wadiz"
    if host in {"tumblbug.com", "www.tumblbug.com"}:
        return "tumblbug"
    if host in {"fanfandaero.kr", "www.fanfandaero.kr"}:
        return "fanfandaero"
    if "k-handmade.com" in host or "designfestival.co.kr" in host or "k-pet.co.kr" in host:
        return "exhibitions"
    return "web"


def is_candidate_url(url):
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host == "smartstore.naver.com":
        return bool(parts) and parts[0] not in {"i", "category", "search", "main"}
    if host.endswith("smartstore.naver.com"):
        return False
    if host in {"instagram.com", "www.instagram.com"}:
        return bool(parts) and parts[0] not in {"p", "reel", "explore", "accounts"}
    if host in {"tumblbug.com", "www.tumblbug.com"}:
        return bool(parts) and parts[0] not in {"discover", "collections", "search"}
    if host in {"wadiz.kr", "www.wadiz.kr", "wadiz.io", "www.wadiz.io"}:
        return len(parts) >= 3 and parts[:2] == ["web", "maker"] or len(parts) >= 4 and parts[:3] == ["web", "campaign", "detail"]
    if host in {"fanfandaero.kr", "www.fanfandaero.kr"}:
        lowered_path = parsed.path.casefold()
        return any(token in lowered_path for token in ("store", "product", "company", "brand")) and "intro" not in lowered_path
    if host.endswith("k-handmade.com"):
        return False
    if host.endswith("designfestival.co.kr"):
        return len(parts) >= 2 and parts[0].casefold() == "exhibition"
    if host.endswith("k-pet.co.kr"):
        generic_sections = {"page", "participation", "information", "overview", "brand-promotion"}
        return bool(parts) and not any(part.casefold() in generic_sections for part in parts)
    return False


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        values = dict(attrs)
        self.current = values.get("href")
        self.text = []

    def handle_data(self, data):
        if self.current:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            self.links.append((self.current, " ".join(self.text).strip()))
            self.current = None
            self.text = []


def _clean_result_url(url):
    parsed = urllib.parse.urlparse(html.unescape(url))
    params = urllib.parse.parse_qs(parsed.query)
    if "uddg" in params:
        return urllib.parse.unquote(params["uddg"][0])
    if parsed.hostname == "inflow.pay.naver.com" and "retUrl" in params:
        return urllib.parse.unquote(params["retUrl"][0])
    if parsed.hostname == "smartstore.naver.com" and parsed.path == "/inflow/outlink/url" and "url" in params:
        return urllib.parse.unquote(params["url"][0])
    return html.unescape(url)


def _clean_title(value):
    value = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return re.sub(r"\s*새 창 열림\s*$", "", value).strip()


def _title_score(value):
    lowered = value.casefold()
    generic = {"이미지", "네이버 스마트스토어", "스마트스토어", "instagram", "와디즈", "텀블벅"}
    if not value or value.isdigit() or lowered in generic or "loading=" in lowered or len(value) > 60:
        return -100
    score = 20 if re.search(r"[가-힣]", value) else 0
    score += max(0, 20 - len(value))
    if any(word in value for word in ("공방", "브랜드", "스튜디오", "상점")):
        score += 10
    return score


def _is_generic_title(value):
    lowered = value.casefold()
    blocked = (
        "공지사항", "참가신청", "신청 기간", "brand promotion", "온라인 참가",
        "앱개발", "웹툰", "소설", "전자책", "온라인 강의", "사주",
    )
    return any(token in lowered for token in blocked)


def extract_search_results(document, query, checked_at=None, limit=10):
    parser = _Links()
    parser.feed(document)
    by_url = {}
    for raw_url, title in parser.links:
        url = _clean_result_url(raw_url)
        if not url.startswith("http") or not is_candidate_url(url):
            continue
        source_type = classify_url(url)
        clean_title = _clean_title(title)
        fallback = urllib.parse.urlparse(url).path.strip("/").split("/")[-1]
        existing = by_url.get(url)
        if existing is None or _title_score(clean_title) > _title_score(existing["brand_name"]):
            by_url[url] = {
                "brand_name": clean_title or fallback,
                "official_url": url,
                "source_type": source_type,
                "discovery_query": query,
                "last_activity_at": None,
                "public_contact": None,
                "evidence": [{"kind": "search_result", "url": url, "checked_at": checked_at or date.today().isoformat(), "excerpt": clean_title or fallback}],
            }
    return [
        row for row in by_url.values()
        if _title_score(row["brand_name"]) >= 0 and not _is_generic_title(row["brand_name"])
    ][:limit]


def parse_wadiz_projects(payload, checked_at=None, limit=10):
    if payload.get("status") != 200 or not isinstance(payload.get("data", {}).get("list"), list):
        raise ValueError("와디즈 목록 응답 형식이 올바르지 않습니다")
    checked_at = checked_at or date.today().isoformat()
    rows = []
    for item in payload["data"]["list"]:
        if item.get("advertisement") is True or item.get("isDeliveryAvailable") is not True:
            continue
        if item.get("categoryName") in WADIZ_EXCLUDED_CATEGORIES:
            continue
        campaign_id = item.get("campaignId")
        user_id = item.get("userId")
        brand_name = item.get("nickName") or item.get("corpName")
        opened = str(item.get("whenOpen") or "")[:10]
        if not campaign_id or not user_id or not brand_name or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", opened):
            continue
        project_url = f"https://www.wadiz.io/web/campaign/detail/{campaign_id}"
        rows.append({
            "brand_name": brand_name,
            "official_url": project_url,
            "maker_url": None,
            "source_type": "wadiz",
            "category": item.get("categoryName") or "카테고리 미확인",
            "last_activity_at": opened,
            "own_product_count": None,
            "observed_channel_gap": None,
            "workload_signals": [],
            "expansion_signals": [],
            "public_contact": None,
            "wadiz_metrics": {
                "participation_count": item.get("participationCnt"),
                "backed_amount": item.get("totalBackedAmount"),
                "product_type": item.get("productType"),
            },
            "evidence": [{
                "kind": "wadiz_project",
                "url": project_url,
                "checked_at": checked_at,
                "excerpt": f"{item.get('title', '')} · {item.get('coreMessage', '')}".strip(" ·"),
            }],
        })
        if len(rows) >= limit:
            break
    return rows


def extract_public_business_email(story_html):
    text = re.sub(r"<[^>]+>", " ", html.unescape(story_html or ""))
    text = re.sub(r"\s+", " ", text)
    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    for match in email_pattern.finditer(text):
        email = match.group(0).casefold()
        if email.endswith(("@wadiz.kr", "@wadiz.io")):
            continue
        context = text[max(0, match.start() - 80): min(len(text), match.end() + 80)]
        if any(token in context for token in ("문의", "고객센터", "메일", "접수", "배송")):
            return email
    return None


def prioritize_wadiz_candidates(rows, limit=10):
    """Keep verified-contact prospects first without disturbing source recency order."""
    return sorted(rows, key=lambda row: row.get("public_contact") is None)[:limit]


class SearchSource:
    def __init__(self, definitions, endpoint="https://search.naver.com/search.naver"):
        self.definitions = definitions
        self.endpoint = endpoint

    @classmethod
    def from_registry(cls):
        return cls(json.loads(REGISTRY_PATH.read_text(encoding="utf-8")))

    def search(self, query, limit=10, timeout=10):
        url = f"{self.endpoint}?{urllib.parse.urlencode({'query': query})}"
        request = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0 Chrome/131 Safari/537.36 {USER_AGENT}"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            document = response.read().decode("utf-8", errors="replace")
        lowered = document.lower()
        if "unusual traffic" in lowered or "verify you are human" in lowered or "anomaly-modal" in lowered:
            raise RuntimeError("검색 서비스가 자동 요청을 제한했습니다")
        return extract_search_results(document, query, limit=limit)

    def discover_direct(self, source_id, limit=10, timeout=12):
        if source_id != "wadiz":
            return None
        body = json.dumps({
            "categoryCode": "", "endYn": "ALL", "order": "recent",
            "limit": max(48, min(limit * 4, 96)), "isMakerClub": False, "startNum": 0,
        }).encode("utf-8")
        request = urllib.request.Request(WADIZ_FUNDING_API, data=body, headers={
            "Content-Type": "application/json",
            "Wadiz-Country": "KR",
            "Wadiz-Language": "ko",
            "Referer": "https://www.wadiz.io/",
            "User-Agent": USER_AGENT,
        })
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = parse_wadiz_projects(payload, limit=max(limit * 2, 10))
        for row in rows:
            campaign_id = row["official_url"].rstrip("/").split("/")[-1]
            story_url = f"https://api.wadiz.io/app/v1/funding/projects/{campaign_id}/story"
            story_request = urllib.request.Request(story_url, headers={
                "Wadiz-Country": "KR",
                "Wadiz-Language": "ko",
                "Referer": "https://www.wadiz.io/",
                "User-Agent": USER_AGENT,
            })
            try:
                with urllib.request.urlopen(story_request, timeout=timeout) as response:
                    story_payload = json.loads(response.read().decode("utf-8"))
                story = story_payload.get("data", {}).get("story", "")
                email = extract_public_business_email(story)
                if email:
                    row["public_contact"] = {
                        "type": "email", "value": email, "url": f"mailto:{email}",
                    }
                row["evidence"].append({
                    "kind": "wadiz_story",
                    "url": row["official_url"],
                    "checked_at": date.today().isoformat(),
                    "excerpt": "와디즈 프로젝트 상세 스토리 확인",
                })
            except Exception as error:
                row.setdefault("source_warnings", []).append(f"상세 확인 실패: {str(error)[:160]}")
        return prioritize_wadiz_candidates(rows, limit=limit)
