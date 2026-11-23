# 황금 키워드 대시보드

GitHub Pages 정적 웹 + GitHub Actions 일 1회 자동 수집 구조의 네이버 블로그 황금 키워드 대시보드입니다.

## 파일 구성
- `index.html`, `style.css`, `app.js`: 다크모드 정적 대시보드 (요약 카드, 카테고리 필터, 검색, 정렬)
- `data.json`: 바로 열어볼 수 있는 샘플/최신 키워드 데이터 (25개)
- `scripts/fetch_keywords.py`: 네이버 검색광고 API + 네이버 오픈 API 연동 수집 스크립트
- `.github/workflows/update.yml`: 매일 새벽 5시(KST) 자동 실행 및 수동 실행(`workflow_dispatch`)

## 1. GitHub Secrets 설정
리포지토리 **Settings → Secrets and variables → Actions → New repository secret**에 아래 5개 키를 등록하세요.

1. `NAVER_AD_API_KEY`: 네이버 검색광고 API 액세스 라이선스
2. `NAVER_AD_SECRET_KEY`: 네이버 검색광고 API 비밀키
3. `NAVER_AD_CUSTOMER_ID`: 네이버 검색광고 고객 ID (숫자)
4. `NAVER_CLIENT_ID`: 네이버 개발자센터 오픈 API Client ID
5. `NAVER_CLIENT_SECRET`: 네이버 개발자센터 오픈 API Client Secret

## 2. GitHub Pages 배포
1. 리포지토리에 전체 파일을 푸시합니다. (`.github/workflows/update.yml` 포함)
2. **Settings → Pages → Build and deployment**에서 **Source: Deploy from a branch**, **Branch: `main` / `/ (root)`**를 선택하고 저장합니다.
3. **Actions** 탭에서 **Update Golden Keywords** 워크플로를 한 번 수동 실행(`Run workflow`)해 API 연동이 정상 동작하는지 확인하세요.
4. `scripts/fetch_keywords.py`의 `SEED_KEYWORDS` 리스트에 원하는 키워드와 카테고리를 추가/수정하면 다음 실행부터 자동 반영됩니다.
