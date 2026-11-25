#!/usr/bin/env python3
"""
네이버 검색광고 API(키워드 도구)만으로 data.json을 최신화합니다.

필요한 Secret 3개
  - NAVER_AD_API_KEY     : 액세스라이선스
  - NAVER_AD_SECRET_KEY  : 비밀키
  - NAVER_AD_CUSTOMER_ID : 고객 ID

네이버 오픈 API(검색 API)는 2026-07-31부터 개발자센터 신규 신청이 막히고
NCP NAVER API HUB(카드 등록 필요)로 이관되어 쓰지 않습니다.
경쟁도는 검색광고 API가 주는 compIdx(낮음/중간/높음)를 그대로 씁니다.
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
KEYWORD_TOOL_URI = "/keywordstool"

# 검색광고 API 경쟁정도(compIdx)를 황금지수에 반영하는 계수
COMPETITION_FACTOR = {"낮음": 1.5, "중간": 1.0, "높음": 0.6}
COMPETITION_RANK = {"낮음": 0, "중간": 1, "높음": 2}

# 추적할 주제(시드) 목록 — 키워드를 바꾸고 싶으면 여기만 수정하면 됩니다.
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
    # ── 경제 (티스토리 1호 · 알쓸집) ──
    ("연말정산 미리보기", "경제"),
    ("청년미래적금 신청", "경제"),
    ("중개형 ISA 개설", "경제"),
    ("주택청약 납입 인정액", "경제"),
    ("버팀목 전세자금대출", "경제"),
    ("소상공인 대환대출", "경제"),
    ("안심상속 원스톱", "경제"),
    ("프리랜서 종합소득세 환급", "경제"),
    ("국민연금 임의가입", "경제"),
    ("청년도약계좌", "경제"),
    ("전세보증금 반환보증", "경제"),
    ("숨은 보험금 찾기", "경제"),
    ("카드포인트 현금화", "경제"),
    ("예금자보호 한도", "경제"),
    # ── 생활 (알쓸집 · 티스토리 1호) ──
    ("자동차세 연납 할인", "생활"),
    ("자동차보험 특약 추천", "생활"),
    ("고효율 가전 환급", "생활"),
    ("주정차 과태료 조회", "생활"),
    ("여권 재발급 준비물", "생활"),
    ("등기부등본 열람", "생활"),
    ("계약갱신청구권", "생활"),
    ("택배 파손 보상", "생활"),
    ("가족관계증명서 인터넷 발급", "생활"),
    ("부동산 실거래가 조회", "생활"),
    ("전입신고 확정일자", "생활"),
    ("자동차 검사 예약", "생활"),
    ("건강보험 자격득실확인서", "생활"),
    ("우체국 택배 방문접수", "생활"),
    # ── 육아 (토리네) ──
    ("아기 카시트 추천", "육아"),
    ("젖병 세척 방법", "육아"),
    ("아기 겨울 외출복", "육아"),
    ("아기 첫 칫솔질", "육아"),
    ("어린이집 입소 준비물", "육아"),
    ("돌잔치 답례품 추천", "육아"),
    ("아기 해열제 종류", "육아"),
    ("아기 기저귀 발진", "육아"),
    ("아기 수면교육 시기", "육아"),
    ("아기 배밀이 시기", "육아"),
    ("아기 중이염 증상", "육아"),
    ("돌아기 우유 전환", "육아"),
    ("아기 물티슈 추천", "육아"),
    ("유아 치약 불소", "육아"),
    ("24개월 언어발달", "육아"),
    # ── 건강 (알쓸집 · 취향상회) ──
    ("국가건강검진 대상자 조회", "건강"),
    ("임플란트 건강보험", "건강"),
    ("노로바이러스 증상", "건강"),
    ("달빛어린이병원", "건강"),
    ("루테인 눈 영양제", "건강"),
    ("온열 찜질기 추천", "건강"),
    ("대상포진 예방접종 비용", "건강"),
    ("비타민D 부족 증상", "건강"),
    ("유산균 추천", "건강"),
    ("오메가3 추천", "건강"),
    ("마그네슘 영양제 추천", "건강"),
    ("A형간염 항체검사", "건강"),
    ("갑상선 기능검사 비용", "건강"),
    ("대장내시경 수면 비용", "건강"),
    ("허리 디스크 스트레칭", "건강"),
    ("두통 MRI 비용", "건강"),
    # ── IT · 살림템 (취향상회 · 티스토리 1호) ──
    ("미니 가습기 추천", "IT"),
    ("로봇청소기 추천", "IT"),
    ("무선 전기포트 추천", "IT"),
    ("전동칫솔 추천", "IT"),
    ("블루투스 이어폰 추천", "IT"),
    ("미니 보조배터리", "IT"),
    ("차량용 방향제 추천", "IT"),
    ("실내 슬리퍼 추천", "IT"),
    ("규조토 발매트", "IT"),
    ("무선청소기 추천", "IT"),
    ("스마트워치 추천", "IT"),
    ("보조배터리 기내 반입", "IT"),
    ("C타입 고속충전기 추천", "IT"),
    ("공기청정기 필터 교체", "IT"),
    ("음식물처리기 추천", "IT"),
    ("태블릿 거치대 추천", "IT"),
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
    """'< 10' 같은 표기를 10으로, 숫자는 그대로 정수화합니다."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace("<", "").replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return 0


def fetch_keyword_rows(hints: list[str], api_key: str, secret_key: str, customer_id: str) -> list[dict]:
    """hintKeywords(최대 5개)로 키워드 도구를 조회합니다."""
    query = urllib.parse.urlencode(
        {
            "hintKeywords": ",".join(h.replace(" ", "") for h in hints),
            "showDetail": "1",
        }
    )
    timestamp = str(int(time.time() * 1000))
    signature = make_signature(timestamp, "GET", KEYWORD_TOOL_URI, secret_key)
    req = urllib.request.Request(
        f"{AD_BASE_URL}{KEYWORD_TOOL_URI}?{query}",
        headers={
            "X-Timestamp": timestamp,
            "X-API-KEY": api_key,
            "X-Customer": customer_id,
            "X-Signature": signature,
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("keywordList", []) or []


def normalize(rows: list[dict]) -> list[dict]:
    items = []
    for row in rows:
        name = row.get("relKeyword") or ""
        if not name:
            continue
        pc = parse_count(row.get("monthlyPcQcCnt"))
        mobile = parse_count(row.get("monthlyMobileQcCnt"))
        items.append(
            {
                "name": name,
                "compact": name.replace(" ", ""),
                "pc": pc,
                "mobile": mobile,
                "volume": pc + mobile,
                "comp": row.get("compIdx") or "중간",
            }
        )
    return items


def score(volume: int, comp: str) -> float:
    return round(volume / 1000 * COMPETITION_FACTOR.get(comp, 1.0), 2)


def find_exact(items: list[dict], phrase: str) -> dict | None:
    key = phrase.replace(" ", "")
    for item in items:
        if item["compact"] == key:
            return item
    return None


def pick_recommendation(items: list[dict], phrase: str, exclude: str, used: set[str]) -> dict | None:
    """주제와 단어가 겹치고 실제 검색량이 있는 관련 키워드 중 가장 쓸만한 것 하나."""
    tokens = [t for t in phrase.split() if len(t) >= 2]
    candidates = []
    for item in items:
        if item["compact"] == exclude or item["compact"] in used or item["volume"] < 100:
            continue
        matched = sum(1 for t in tokens if t in item["name"])
        if matched == 0:
            continue
        candidates.append({**item, "matched": matched})

    if not candidates:
        return None

    def rank_key(c: dict) -> tuple:
        return (-c["matched"], -score(c["volume"], c["comp"]), COMPETITION_RANK.get(c["comp"], 1))

    return sorted(candidates, key=rank_key)[0]


def head_token(phrase: str) -> str:
    """키워드 도구가 잘 찾아주는 핵심 단어(가장 긴 토큰)를 시드 문구에서 뽑습니다."""
    tokens = [t for t in phrase.split() if len(t) >= 2]
    if not tokens:
        return phrase.replace(" ", "")
    return max(tokens, key=len)


def main() -> None:
    ad_api_key = os.environ.get("NAVER_AD_API_KEY", "").strip()
    ad_secret_key = os.environ.get("NAVER_AD_SECRET_KEY", "").strip()
    ad_customer_id = os.environ.get("NAVER_AD_CUSTOMER_ID", "").strip()

    if not all([ad_api_key, ad_secret_key, ad_customer_id]):
        raise SystemExit(
            "필수 환경변수가 없습니다. NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, "
            "NAVER_AD_CUSTOMER_ID를 설정하세요."
        )

    prev_map: dict[str, dict] = {}
    if DATA_PATH.exists():
        old_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        for row in old_data.get("keywords", []):
            if row.get("keyword"):
                prev_map[row["keyword"]] = row

    updated_rows = []
    used_recommends: set[str] = set()
    for phrase, category in SEED_KEYWORDS:
        rows: list[dict] = []
        hints = list(dict.fromkeys([phrase, head_token(phrase)]))
        for hint in hints:
            for attempt in range(2):
                try:
                    rows.extend(
                        fetch_keyword_rows([hint], ad_api_key, ad_secret_key, ad_customer_id)
                    )
                    break
                except Exception as exc:  # 개별 키워드 실패가 전체를 멈추지 않게
                    if attempt == 0:
                        print(f"[warn] '{hint}' 조회 재시도: {exc}")
                        time.sleep(1.5)
                    else:
                        print(f"[warn] '{hint}' 조회 실패: {exc}")
            time.sleep(0.25)

        items = normalize(rows)
        exact = find_exact(items, phrase)
        topic_volume = exact["volume"] if exact else 0
        topic_comp = exact["comp"] if exact else "중간"

        recommend = pick_recommendation(
            items, phrase, exclude=phrase.replace(" ", ""), used=used_recommends
        )
        if recommend:
            used_recommends.add(recommend["compact"])

        if recommend and recommend["volume"] >= max(topic_volume, 100):
            main_volume = recommend["volume"]
            main_comp = recommend["comp"]
        else:
            main_volume = topic_volume
            main_comp = topic_comp

        prev = prev_map.get(phrase)
        trend = "유지"
        if prev and prev.get("monthly_search"):
            diff = main_volume - prev["monthly_search"]
            if diff > prev["monthly_search"] * 0.05:
                trend = "상승"
            elif diff < -prev["monthly_search"] * 0.05:
                trend = "하락"

        updated_rows.append(
            {
                "keyword": phrase,
                "category": category,
                "topic_search": topic_volume,
                "monthly_search": main_volume,
                "pc_search": (recommend or exact or {}).get("pc", 0),
                "mobile_search": (recommend or exact or {}).get("mobile", 0),
                "recommend_keyword": recommend["name"] if recommend else "",
                "recommend_search": recommend["volume"] if recommend else 0,
                "competition": main_comp,
                "golden_ratio": score(main_volume, main_comp),
                "trend": trend,
            }
        )

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
