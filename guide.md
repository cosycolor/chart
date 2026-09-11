# 🚀 집 PC에서 바로 이어서 개발/실행하는 방법 가이드

## 1. 회사 PC에서 할 일 (지금 바로 푸시)
터미널에서 이미 초기 커밋이 완료되어 있습니다. 생성해 두신 깃허브 원격 주소를 연결하고 푸시만 하시면 됩니다:
```bash
# 깃허브 레포지토리 URL 연결 (예: https://github.com/내아이디/내레포이름.git)
git remote add origin <당신의_깃허브_레포_URL>

# 푸시
git push -u origin main
```

---

## 2. 집 PC에서 할 일 (처음 시작 시)

### ① 리포지토리 다운로드 (Clone)
원하는 폴더에서 터미널(PowerShell 또는 CMD)을 열고 실행:
```bash
git clone <당신의_깃허브_레포_URL>
cd <레포지토리이름>
```

### ② 필수 패키지 설치
```bash
pip install -r requirements.txt
```

### ③ `.env` 파일 생성 및 키 입력
`.env.example`을 복사하여 `.env` 파일을 만들고 키를 입력합니다:
```ini
# Google Gemini API Key (무료 발급: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=AIzaSy...

# 티스토리 블로그 정보 (선택: 실제 발행 시)
TISTORY_BLOG_NAME=내블로그서브도메인
TISTORY_ACCESS_TOKEN=내액세스토큰
```

### ④ 실행 및 테스트
```bash
# 로컬 미리보기 실행 (차트 + HTML 리포트 생성)
python main.py --dry-run

# 실제 티스토리 발행 실행
python main.py
```

---

## 3. 이후 집 ↔ 회사 간 동기화 작업 흐름

* **집에서 코드를 수정한 후 퇴근/종료 시**:
  ```bash
  git add .
  git commit -m "수정 내용 메모"
  git push
  ```
* **회사에 와서 이어서 작업할 때**:
  ```bash
  git pull
  ```
