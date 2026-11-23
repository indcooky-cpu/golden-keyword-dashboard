#!/usr/bin/env python3
"""
네이버 검색광고 API(월간 검색량) + 네이버 오픈 API(블로그 문서 수)를 호출해
data.json을 최신화합니다.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data.json"

AD_BASE_URL = "https://api.searchad.naver.com"
OPEN_BLOG_URL = "https://openapi.naver.com/v1/search/blog.json"

SEED_KEYWORDS = [
    ("초등 예체능 학원비 세액공제", "경제"),
    ("고향사랑기부제 20만원 공제", "경제"),
    ("실손24 병원 서류없이 청구", "생활"),
    ("착오송금 반환지원 1억원", "경제"),
    ("건보 본인부담상한액 환급", "건강"),
    ("운전면허 갱신 생일 6개월", "생활"),
    ("수도계량기 동파 예방법", "생활"),
    ("독감 무료접종 3가 백신", "건강"),
    ("근로장려금 기한후 신청", "경제"),
    ("영유아 검진 시기 준비물", "육아"),
    ("아기 이유식 초기 큐브 보관", "육아"),
    ("모바일 주민등록증 발급", "IT"),
    ("월세 세액공제 배우자", "경제"),
    ("전기요금 복지할인 출산가구", "육아"),
    ("어카운트인포 휴면계좌 해지", "경제"),
    ("겨울철 자동차 배터리 전압", "생활"),
    ("챗GPT 코덱스 한도 통합", "IT"),
    ("아기 낮잠 깨시 계산", "육아"),
    ("문화누리카드 잔액조회", "생활"),
    ("스케일링 건강보험 적용", "건강"),
    ("도시가스 절약 캐시백", "생활"),
    ("AI 전화 스팸 차단 설정", "IT"),
    ("유아 문센 겨울학기 준비물", "육아"),
    ("수면안대 온열안대 추천", "건강"),
    ("노트북 듀얼모니터 거치대", "IT"),
]


def make_signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def parse_count(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace("<", "").replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return 0


def fetch_search_volume(keywords: list[str], api_key: str, secret_key: str, customer_id: str) -> dict[str, int]:
    uri = "/keywordstool"
    results: dict[str, int] = {}

    # 네이버 검색광고 API는 1회 최대 5개 힌트 키워드 전달 가능
    for i in range(0, len(keywords), 5):
        chunk = keywords[i : i + 5]
        # 공백 제거한 형태로 hintKeywords 전달 후 매핑
        query = urllib.parse.urlencode(
            {
                "hintKeywords": ",".join(k.replace(" ", "") for k in chunk),
                "showDetail": "1",
            }
        )
        timestamp = str(int(time.time() * 1000))
        signature = make_signature(timestamp, "GET", uri, secret_key)

        req = urllib.request.Request(
            f"{AD_BASE_URL}{uri}?{query}",
            headers={
                "X-Timestamp": timestamp,
                "X-API-KEY": api_key,
                "X-Customer": customer_id,
                "X-Signature": signature,
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        for row in payload.get("keywordList", []):
            rel_kw = row.get("relKeyword", "")
            pc = parse_count(row.get("monthlyPcQcCnt"))
            mobile = parse_count(row.get("monthlyMobileQcCnt"))
            results[rel_kw] = pc + mobile
        time.sleep(0.2)

    return results


def fetch_blog_docs(keyword: str, client_id: str, client_secret: str) -> int:
    query = urllib.parse.urlencode({"query": keyword, "display": 1})
    req = urllib.request.Request(
        f"{OPEN_BLOG_URL}?{query}",
        headers={
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return int(payload.get("total", 0))


def classify_competition(ratio: float) -> str:
    if ratio >= 1.5:
        return "낮음"
    if ratio >= 0.7:
        return "보통"
    return "높음"


def main() -> None:
    ad_api_key = os.environ.get("NAVER_AD_API_KEY", "").strip()
    ad_secret_key = os.environ.get("NAVER_AD_SECRET_KEY", "").strip()
    ad_customer_id = os.environ.get("NAVER_AD_CUSTOMER_ID", "").strip()
    client_id = os.environ.get("NAVER_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "").strip()

    if not all([ad_api_key, ad_secret_key, ad_customer_id, client_id, client_secret]):
        raise SystemExit(
            "필수 환경변수가 없습니다. NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, "
            "NAVER_AD_CUSTOMER_ID, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET를 설정하세요."
        )

    prev_map: dict[str, dict] = {}
    if DATA_PATH.exists():
        old_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        for row in old_data.get("keywords", []):
            prev_map[row["keyword"]] = row

    kw_list = [k for k, _ in SEED_KEYWORDS]
    volumes = fetch_search_volume(kw_list, ad_api_key, ad_secret_key, ad_customer_id)

    updated_rows = []
    for kw, category in SEED_KEYWORDS:
        vol = volumes.get(kw.replace(" ", ""), volumes.get(kw, 0))
        docs = fetch_blog_docs(kw, client_id, client_secret)
        ratio = round(vol / max(docs, 1), 2)

        prev = prev_map.get(kw)
        trend = "유지"
        if prev and prev.get("monthly_search"):
            diff = vol - prev["monthly_search"]
            if diff > prev["monthly_search"] * 0.05:
                trend = "상승"
            elif diff < -prev["monthly_search"] * 0.05:
                trend = "하락"

        updated_rows.append(
            {
                "keyword": kw,
                "category": category,
                "monthly_search": vol,
                "blog_docs": docs,
                "golden_ratio": ratio,
                "competition": classify_competition(ratio),
                "trend": trend,
            }
        )
        time.sleep(0.12)

    updated_rows.sort(key=lambda x: x["golden_ratio"], reverse=True)
    kst = timezone(timedelta(hours=9))
    output = {
        "updated_at": datetime.now(kst).strftime("%Y-%m-%d %H:%M KST"),
        "keywords": updated_rows,
    }
    DATA_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {len(updated_rows)} keywords -> {DATA_PATH}")


if __name__ == "__main__":
    main()
