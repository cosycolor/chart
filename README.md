# 📈 한국 증시 당일 상한가 & 1,000만주 특징주 자동화 분석기

한국거래소(KRX) 공식 시세 데이터를 기반으로 **상한가** 및 **거래량 1,000만 주 이상** 급등 종목을 추출하고, **40일봉 캔들차트 생성 + 최신 뉴스 스크랩 + Google Gemini LLM을 통한 진짜 상승 이유 팩트체크** 후 **티스토리 블로그에 매일 15:40 자동 발행**하는 GitHub Actions 기반 All-in-One 시스템입니다.

---

## ✨ 주요 기능

1. **거래소 100% 공식 데이터 연동**:
   - `PyKrx`를 통해 당일 장 마감 기준 상한가(등락률 29.5% 이상) 및 1,000만주 이상 거래량 종목 정확히 선별
   - 네이버 증권 / FnGuide 연동으로 최근 분기 매출액 및 당기순이익 자동 수집
2. **40일봉 캔들 차트 자동 생성**:
   - 5일, 20일 이동평균선과 거래량 보조지표가 포함된 HTS 스타일 고화질 PNG 차트 자동 생성
3. **Google Gemini AI 팩트체크**:
   - 당일 포털/특징주 뉴스 기사를 종합하여 단순 시황 기사는 필터링하고 **주가 급등의 핵심 원인 1문장 + 상세 포인트 + 대표 기사 링크** 도출
4. **티스토리 자동 포스팅 & 미려한 서식**:
   - 반응형 요약 표, 종목별 차트 이미지 첨부, 깔끔한 카드형 디자인 적용
5. **서버 비용 0원 & 완전 자동화 (GitHub Actions)**:
   - 평일 매일 오후 3시 40분(장 마감 직후) 자동 실행

---

## 🛠️ 빠른 시작 (로컬 테스트)

### 1. 필수 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 키를 입력합니다.
```ini
# Google Gemini API Key (무료 발급: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# 티스토리 설정 (포스팅 테스트 시)
TISTORY_BLOG_NAME=내블로그명
TISTORY_ACCESS_TOKEN=발급받은_액세스토큰
```

### 3. 실행 명령어
```bash
# 1) 로컬 테스트 모드 (블로그 포스팅 없이 차트 생성 및 HTML 리포트 미리보기)
python main.py --dry-run

# 2) 특정 과거 날짜 기준 테스트 (예: 2026년 9월 10일)
python main.py --date 20260910 --dry-run

# 3) 실제 티스토리 포스팅 모드
python main.py
```

실행 후 `output/` 폴더에 생성된 `report_YYYYMMDD.html` 파일을 브라우저로 열어 완성된 블로그 게시글을 확인할 수 있습니다.

---

## 🚀 GitHub Actions 완전 자동화 설정 가이드

본인의 GitHub 리포지토리에 코드를 올린 후 아래 3단계만 진행하면 매일 장마감 후 자동으로 블로그 글이 올라옵니다.

### 1단계: 깃허브 리포지토리 생성 및 푸시
```bash
git init
git add .
git commit -m "Initial commit: Daily Stock Analyzer"
git remote add origin https://github.com/사용자아이디/리포지토리이름.git
git branch -M main
git push -u origin main
```

### 2단계: GitHub Secrets 등록
GitHub 리포지토리 페이지 ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret** 클릭 후 아래 항목 등록:

| Secret 이름 | 설명 | 필수 여부 |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google AI Studio에서 발급받은 API 키 | **필수** |
| `TISTORY_BLOG_NAME` | 티스토리 블로그 서브도메인명 (예: `mystock` -> `mystock.tistory.com`) | **필수** |
| `TISTORY_ACCESS_TOKEN` | 티스토리 OAuth2 Access Token | **필수** |
| `TISTORY_CATEGORY_ID` | 글이 등록될 카테고리 번호 (기본값: `0`) | 선택 |
| `TISTORY_VISIBILITY` | `3`(공개발행, 기본값) 또는 `0`(비공개발행) | 선택 |
| `NAVER_CLIENT_ID` | 네이버 개발자센터 검색 API ID | 선택 |
| `NAVER_CLIENT_SECRET` | 네이버 개발자센터 검색 API Secret | 선택 |

### 3단계: 자동 실행 확인
* **자동 실행**: 평일(월~금) 한국 시간 **오후 3시 40분**에 스케줄러가 알아서 실행됩니다.
* **수동 즉시 실행**: GitHub 리포지토리의 **Actions** 탭 ➔ **Daily Stock Analysis & Tistory Publisher** 워크플로우 선택 ➔ **[Run workflow]** 버튼을 누르면 지금 즉시 실행해볼 수 있습니다.
