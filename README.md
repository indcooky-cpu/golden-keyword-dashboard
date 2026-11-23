# 황금 키워드 대시보드

GitHub Pages 정적 웹 + GitHub Actions 일 1회 자동 수집 구조의 네이버 키워드 대시보드입니다.
검색광고 API(키워드 도구)만으로 동작하며, 네이버 오픈 API(검색 API)는 쓰지 않습니다.
(검색 API는 2026-07-31부터 개발자센터 신규 신청이 막히고 NCP NAVER API HUB로 이관되었습니다.)

## 파일 구성
- `index.html`, `style.css`, `app.js`: 다크모드 정적 대시보드 (요약 카드, 카테고리 필터, 검색, 정렬)
- `data.json`: 최신 키워드 데이터 25건
- `scripts/fetch_keywords.py`: 네이버 검색광고 API 연동 수집 스크립트
- `.github/workflows/update.yml`: 매일 새벽 5시(KST) 자동 실행 및 수동 실행(`workflow_dispatch`)

## 1. GitHub Secrets 설정
리포지토리 **Settings → Secrets and variables → Actions → New repository secret**에 아래 3개 키를 등록하세요.

1. `NAVER_AD_API_KEY`: 네이버 검색광고 API 액세스라이선스
2. `NAVER_AD_SECRET_KEY`: 네이버 검색광고 API 비밀키
3. `NAVER_AD_CUSTOMER_ID`: 네이버 검색광고 고객 ID (숫자)

발급 위치: 네이버애즈(ads.naver.com) 로그인 → 도구 → **SA API 사용 관리** → 서비스 신청 → 액세스라이선스 / 비밀키 / CUSTOMER_ID 확인

## 2. GitHub Pages 배포
1. 리포지토리에 전체 파일을 푸시합니다. (`.github/workflows/update.yml` 포함)
2. **Settings → Pages → Build and deployment**에서 **Source: Deploy from a branch**, **Branch: `main` / `/ (root)`**를 선택하고 저장합니다.
3. **Actions** 탭에서 **Update Golden Keywords** 워크플로를 한 번 수동 실행(`Run workflow`)해 API 연동이 정상 동작하는지 확인하세요.
4. `scripts/fetch_keywords.py`의 `SEED_KEYWORDS` 리스트에 원하는 주제와 카테고리를 추가/수정하면 다음 실행부터 자동 반영됩니다.

## 3. 지표 계산
- **주제 검색량**: 추적 주제 문구 자체의 월간 검색량(PC+모바일)
- **추천 키워드 / 추천 검색량**: 주제와 단어가 겹치면서 실제 검색량(100 이상)이 있는 관련 키워드 중 가장 쓸만한 것
- **경쟁도**: 검색광고 API의 `compIdx`(낮음/중간/높음)
- **황금지수**: `월간 검색량(천 단위) × 경쟁도 계수` (낮음 1.5 / 보통 1.0 / 높음 0.6)
