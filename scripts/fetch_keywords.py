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

2026-11-26 개편: 시드당 대표 키워드 1개만 뽑던 구조를 버리고,
시드 1개에서 '경쟁도 낮음 + 월 검색량 500~10,000대' 롱테일 키워드를
최대 4개까지 뽑아 data.json 한 행 = 키워드 1개 구조로 바꿨습니다.
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

# 롱테일 황금 구간: 경쟁 낮음 + 월 검색량 500~10,000
LONGTAIL_MIN_VOLUME = 500
LONGTAIL_MAX_VOLUME = 10_000
# 그 아래/위로 채우는 완충 구간
FALLBACK_MIN_VOLUME = 100
FALLBACK_MAX_VOLUME = 30_000

# 시드 1개당 뽑을 최대 행 수(시드 자체가 경쟁 '낮음'이면 그 행 포함)
MAX_PER_SEED = 4
# 전체 행 수 상한
TOTAL_CAP = 500
# 1차 추출로 이보다 적으면 2차로 조금 더 채운다
TOTAL_MIN = 300

# '추천', '가성비'처럼 어느 시드에나 붙는 단어만 겹치는 후보는 관련성 없음으로 본다
GENERIC_TOKENS = {
    "추천", "가성비", "방법", "비용", "시기", "종류", "조회", "신청", "준비물",
    "비교", "순위", "정리", "총정리", "후기", "정보", "확인", "가격", "할인",
    "혜택", "대상", "기준", "정도", "효과", "증상", "통합", "선물", "필수템",
}

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
    ("중개형 ISA", "경제"),
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
    # ── 선물 · 가성비 생활템 (티스토리 2호 '취향상회'용, 2026-11-26 추가) ──
    ("집들이 선물 추천", "생활"),
    ("생일선물 2만원대", "생활"),
    ("부모님 효도 선물", "생활"),
    ("퇴사 선물 추천", "생활"),
    ("감사선물 커피쿠폰", "생활"),
    ("신혼부부 선물", "생활"),
    ("자취생 필수템", "생활"),
    ("캠핑 랜턴 추천", "생활"),
    ("텀블러 보온병 추천", "생활"),
    ("스탠드 무드등", "생활"),
    ("전기방석 추천", "생활"),
    ("디퓨저 추천", "생활"),
    ("핸드워시 선물세트", "생활"),
    ("수건 답례품", "생활"),
    ("커피머신 캡슐", "생활"),
    ("샤워기 필터 추천", "생활"),
    ("미니 청소기 추천", "IT"),
    ("무선 충전기 추천", "IT"),
    ("아이패드 케이스 추천", "IT"),
    ("휴대용 모니터 추천", "IT"),
    ("스마트 플러그 추천", "IT"),
    ("안마기 가성비", "건강"),
    ("마사지건 추천", "건강"),
    ("발 마사지기 추천", "건강"),
    ("혈압계 추천", "건강"),
    ("구강세정기 추천", "건강"),
    ("출산 선물 추천", "육아"),
    ("아기 식판 추천", "육아"),
    ("유모차 쿠션 추천", "육아"),
    ("아기 목욕용품 추천", "육아"),
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


def head_token(phrase: str) -> str:
    """키워드 도구가 잘 찾아주는 핵심 단어를 시드 문구에서 뽑습니다.

    '아기 식판 추천'에서 '아기'보다 '식판'이, '아기 카시트 추천'에서 '카시트'가
    실제 검색어에 가깝기 때문에 범용 단어를 뺀 마지막 토큰을 우선 쓰고,
    없으면 가장 긴 토큰을 씁니다.
    """
    tokens = [t for t in phrase.split() if len(t) >= 2]
    if not tokens:
        return phrase.replace(" ", "")
    specific = [t for t in tokens if t not in GENERIC_TOKENS]
    if specific:
        # 길이가 같으면 뒤에 오는 말이 실제 검색어의 중심어인 경우가 많다
        return max(enumerate(tokens), key=lambda it: (len(it[1]) if it[1] in specific else -1, it[0]))[1]
    return max(tokens, key=len)


def seed_hints(phrase: str) -> list[str]:
    """한 시드에서 조회할 힌트(최대 3개): 전체 문구, 앞 두 단어, 핵심 단어."""
    tokens = phrase.split()
    hints = [phrase]
    if len(tokens) >= 2:
        hints.append("".join(tokens[:2]))
    hints.append(head_token(phrase))
    return list(dict.fromkeys(h.replace(" ", "") for h in hints if h))[:3]


def priority_tier(item: dict) -> int | None:
    """낮을수록 먼저 뽑습니다. None이면 후보에서 제외(경쟁 높음 등)."""
    volume = item["volume"]
    comp = item["comp"]
    if comp == "낮음" and LONGTAIL_MIN_VOLUME <= volume <= LONGTAIL_MAX_VOLUME:
        return 0  # 롱테일 황금 구간 최우선
    if comp == "낮음" and volume >= FALLBACK_MIN_VOLUME:
        return 1  # 경쟁 낮음이면 검색량이 커도 값어치가 있다
    if comp == "중간" and LONGTAIL_MIN_VOLUME <= volume <= LONGTAIL_MAX_VOLUME:
        return 2  # 롱테일이면 경쟁 중간도 차선
    if comp == "중간" and FALLBACK_MIN_VOLUME <= volume <= FALLBACK_MAX_VOLUME:
        return 3
    return None


def is_near_dup(candidate: str, picked: str) -> bool:
    """'무선청소기추천' / '무선청소기추천순위'처럼 꼬리말만 다른 중복을 걸러냅니다."""
    if candidate == picked:
        return True
    if candidate in picked:
        return len(picked) - len(candidate) <= 2
    if picked in candidate:
        return len(candidate) - len(picked) <= 2
    return False


def pick_longtails(items: list[dict], phrase: str, used: set[str], limit: int) -> list[dict]:
    """시드 핵심 단어와 겹치면서 아직 안 쓴 키워드 중, 롱테일·저경쟁 우선으로 limit개."""
    if limit <= 0:
        return []
    tokens = [t for t in phrase.split() if len(t) >= 2]
    specific = [t for t in tokens if t not in GENERIC_TOKENS]
    seed_compact = phrase.replace(" ", "")

    candidates = []
    for item in items:
        if item["volume"] < FALLBACK_MIN_VOLUME:
            continue
        is_self = item["compact"] == seed_compact
        matched = sum(1 for t in tokens if t in item["name"])
        if not is_self and matched == 0:
            continue
        # '추천' 같은 범용 단어만 겹치는 후보는 시드와 무관한 잡음
        if not is_self and specific and not any(t in item["name"] for t in specific):
            continue
        tier = priority_tier(item)
        if tier is None:
            continue
        candidates.append({**item, "matched": matched, "tier": tier})

    candidates.sort(key=lambda c: (c["tier"], -c["matched"], -c["volume"]))

    picked: list[dict] = []
    for cand in candidates:
        if len(picked) >= limit:
            break
        if cand["compact"] in used:
            continue
        if any(is_near_dup(cand["compact"], p["compact"]) for p in picked):
            continue
        picked.append(cand)
    return picked


def build_prev_volume_map(prev_rows: list[dict]) -> dict[str, int]:
    """어제 데이터의 검색량을 키워드별로 모읍니다(추세 계산용)."""
    prev: dict[str, int] = {}
    for row in prev_rows:
        keyword = (row.get("keyword") or "").replace(" ", "")
        volume = row.get("monthly_search") or 0
        if keyword and volume:
            prev[keyword] = volume
        recommend = (row.get("recommend_keyword") or "").replace(" ", "")
        recommend_volume = row.get("recommend_search") or 0
        if recommend and recommend_volume and recommend not in prev:
            prev[recommend] = recommend_volume
    return prev


def make_row(item: dict, seed_phrase: str, category: str, prev_volumes: dict[str, int]) -> dict:
    volume = item["volume"]
    comp = item["comp"]
    prev_volume = prev_volumes.get(item["compact"])
    trend = "유지"
    if prev_volume is None:
        trend = "신규"
    elif prev_volume:
        diff = volume - prev_volume
        if diff > prev_volume * 0.05:
            trend = "상승"
        elif diff < -prev_volume * 0.05:
            trend = "하락"
    return {
        "keyword": item["name"],
        "category": category,
        "seed": seed_phrase,
        "monthly_search": volume,
        "pc_search": item["pc"],
        "mobile_search": item["mobile"],
        "competition": comp,
        "golden_ratio": score(volume, comp),
        "trend": trend,
    }


def main() -> None:
    ad_api_key = os.environ.get("NAVER_AD_API_KEY", "").strip()
    ad_secret_key = os.environ.get("NAVER_AD_SECRET_KEY", "").strip()
    ad_customer_id = os.environ.get("NAVER_AD_CUSTOMER_ID", "").strip()

    if not all([ad_api_key, ad_secret_key, ad_customer_id]):
        raise SystemExit(
            "필수 환경변수가 없습니다. NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, "
            "NAVER_AD_CUSTOMER_ID를 설정하세요."
        )

    prev_volumes: dict[str, int] = {}
    if DATA_PATH.exists():
        old_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        prev_volumes = build_prev_volume_map(old_data.get("keywords", []))

    used: set[str] = set()
    items_by_seed: dict[int, list[dict]] = {}
    rows: list[dict] = []

    for index, (phrase, category) in enumerate(SEED_KEYWORDS):
        api_rows: list[dict] = []
        hints = seed_hints(phrase)
        for hint in hints:
            for attempt in range(2):
                try:
                    api_rows.extend(
                        fetch_keyword_rows([hint], ad_api_key, ad_secret_key, ad_customer_id)
                    )
                    break
                except Exception as exc:  # 개별 키워드 실패가 전체를 멈추지 않게
                    if attempt == 0:
                        print(f"[warn] '{hint}' 조회 재시도: {exc}")
                        time.sleep(1.5)
                    else:
                        print(f"[warn] '{hint}' 조회 실패: {exc}")
            time.sleep(0.2)

        items = normalize(api_rows)
        items_by_seed[index] = items

        exact = find_exact(items, phrase)
        anchor_added = False
        if (
            exact
            and exact["comp"] == "낮음"
            and exact["volume"] >= FALLBACK_MIN_VOLUME
            and exact["compact"] not in used
        ):
            used.add(exact["compact"])
            rows.append(make_row(exact, phrase, category, prev_volumes))
            anchor_added = True

        picked = pick_longtails(
            items,
            phrase,
            used,
            MAX_PER_SEED - (1 if anchor_added else 0),
        )
        for item in picked:
            used.add(item["compact"])
            rows.append(make_row(item, phrase, category, prev_volumes))

    # 1차 추출이 300건에 못 미치면 남은 후보에서 조금씩 더 채운다
    if len(rows) < TOTAL_MIN:
        for extra_round in (1, 2):
            for index, (phrase, category) in enumerate(SEED_KEYWORDS):
                if len(rows) >= TOTAL_MIN:
                    break
                picked = pick_longtails(
                    items_by_seed.get(index, []), phrase, used, extra_round
                )
                for item in picked:
                    used.add(item["compact"])
                    rows.append(make_row(item, phrase, category, prev_volumes))

    # 상한을 넘으면 롱테일·저경쟁 우선 순위가 낮은 행부터 덜어낸다
    if len(rows) > TOTAL_CAP:
        rows.sort(key=lambda r: (-r["golden_ratio"], r["keyword"]))
        rows = rows[:TOTAL_CAP]

    rows.sort(key=lambda r: (-r["golden_ratio"], r["keyword"]))
    kst = timezone(timedelta(hours=9))
    low_count = sum(1 for r in rows if r["competition"] == "낮음")
    longtail_count = sum(
        1
        for r in rows
        if r["competition"] == "낮음"
        and LONGTAIL_MIN_VOLUME <= r["monthly_search"] <= LONGTAIL_MAX_VOLUME
    )
    output = {
        "updated_at": datetime.now(kst).strftime("%Y-%m-%d %H:%M KST"),
        "counts": {
            "total": len(rows),
            "seed_count": len(SEED_KEYWORDS),
            "low_competition": low_count,
            "low_competition_longtail": longtail_count,
        },
        "keywords": rows,
    }
    DATA_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Updated {len(rows)} keywords "
        f"(시드 {len(SEED_KEYWORDS)}개 · 경쟁 낮음 {low_count}건 · "
        f"낮음 롱테일 {longtail_count}건) -> {DATA_PATH}"
    )


if __name__ == "__main__":
    main()
