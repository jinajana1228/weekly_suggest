# Weekly Suggest — 배포 실행 가이드

> 이 문서는 Railway(백엔드) + Vercel(프론트엔드) 배포를 완료하기 위한 단계별 실행 가이드다.
> 순서를 따르면 배포가 완료된다.

---

## 0. 서비스 배포 원칙

| 원칙 | 설명 |
|------|------|
| **발행형 서비스** | 사용자 접속 시 재계산 없음. 미리 발행된 에디션만 표시 |
| **latest 우선** | 메인 페이지는 항상 latest published edition |
| **archive 누적** | 이전 에디션은 영구 보관, /archive에서 접근 가능 |
| **정기 발행** | 격주 월요일 오전 8시 (어닝 시즌 시 임시 발행 추가) |

---

## 1. 배포 전 준비물 체크리스트

### 1-1. 계정 및 서비스 준비

- [ ] **GitHub 계정** — 레포지토리를 만들 수 있는 계정
- [ ] **Railway 계정** — railway.app (GitHub으로 가입 권장)
- [ ] **Vercel 계정** — vercel.com (GitHub으로 가입 권장)

### 1-2. 코드 준비 상태 확인

아래 파일들이 `weekly_suggest/` 루트에 있어야 한다:

- [ ] `railway.toml` — Railway 빌드/시작 설정 (이미 존재)
- [ ] `.gitignore` — backend/.env, data/state.db 등 제외 (이미 존재)
- [ ] `backend/requirements.txt` — Python 의존성 (이미 존재)
- [ ] `frontend/next.config.mjs` — BACKEND_URL rewrite 설정 (이미 존재)

### 1-3. 사용자가 직접 생성해야 하는 값

**ADMIN_API_KEY 생성** (배포 전 1회만):

```bash
cd weekly_suggest
python scripts/generate_admin_key.py
```

출력 예시:
```
================================================================
ADMIN_API_KEY:

a3f8e2b1c4d9f0e5a7b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4

================================================================
Copy this value to Railway Variables > ADMIN_API_KEY
```

> 이 64자리 hex 값을 **어딘가에 안전하게 복사 보관** (메모장, 비밀번호 관리자 등).
> Railway Variables에 입력하고, Admin UI 로그인에도 이 값을 사용한다.

### 1-4. GitHub에 push

```bash
cd weekly_suggest

# git 초기화 (아직 안 한 경우)
git init
git add .
git commit -m "initial: weekly_suggest deployment ready"

# GitHub 레포지토리 연결 (미리 GitHub에서 빈 레포 생성 후)
git remote add origin https://github.com/<사용자명>/<레포명>.git
git push -u origin main
```

.gitignore로 자동 제외되는 파일들:
- `backend/.env`, `backend/venv/`
- `data/state.db`, `data/state.db-*`
- `frontend/node_modules/`, `frontend/.next/`

---

## 2. Railway 배포 단계별 가이드

### 2-1. 프로젝트 생성

1. https://railway.app 접속 → 로그인
2. 대시보드 → **New Project** 클릭
3. **Deploy from GitHub repo** 선택
4. `weekly_suggest` 레포지토리 선택
5. **Deploy Now** 클릭

> `railway.toml`이 루트에 있으므로 빌드/시작 명령이 자동 인식된다.
> 별도 Root Directory 설정 불필요.

빌드 명령 (자동 적용):
```
cd backend && pip install -r requirements.txt
```

시작 명령 (자동 적용):
```
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 2-2. 환경변수 설정

Railway 대시보드 → 해당 서비스 클릭 → **Variables** 탭 → 아래 변수 입력:

| 변수명 | 입력 값 | 비고 |
|--------|---------|------|
| `APP_ENV` | `production` | 필수 (`ENV`는 POSIX 예약어라 사용 불가) |
| `LOG_LEVEL` | `INFO` | |
| `DATA_PROVIDER_MODE` | `mock` | 실데이터 전환 전까지 |
| `ADMIN_API_KEY` | _(1-3에서 생성한 64자리 값)_ | 필수 |
| `MIN_PUBLISH_STOCKS` | `5` | |
| `MAX_DATA_QUALITY_FLAGS` | `3` | |
| `CORS_ORIGINS` | _(Vercel 배포 완료 후 입력)_ | 2-4에서 추가 |

> `CORS_ORIGINS`는 Vercel URL 확정 후 입력한다. 지금은 비워두거나 임시로 `http://localhost:3000` 입력.

### 2-3. (권장) Railway Volume 설정 — SQLite 영속성

Volume 없이 배포하면 Railway 인스턴스가 재시작될 때 `state.db`(발행 이력, latest pointer)가 초기화된다.

Volume 설정 방법:
1. Railway 대시보드 → 서비스 → **Volumes** 탭
2. **Add Volume** 클릭
3. Mount Path: `/data` 입력 → 생성
4. Variables 탭에서 추가:

| 변수명 | 입력 값 |
|--------|---------|
| `STATE_DB_PATH` | `/data/state.db` |

> Volume 없이도 배포는 동작한다. 다만 재시작마다 발행 이력이 초기화된다.
> 첫 배포에는 Volume 없이 시작해도 된다.

### 2-4. 배포 완료 확인

Railway 대시보드 → **Deployments** 탭 → 최신 항목 로그에서 확인:
```
Weekly Suggest API starting | env=production | provider=mock
Application startup complete.
```

**Railway Backend URL 확인**: 서비스 → **Settings** → **Domains** 섹션
예시: `https://weekly-suggest-production.up.railway.app`

이 URL을 메모해둔다 → Vercel 설정에 필요.

**빠른 health check** (터미널에서):
```bash
curl https://<railway-url>/health
# 기대값: {"status":"ok","env":"production","provider_mode":"mock","version":"0.2.0"}
```

---

## 3. Vercel 배포 단계별 가이드

### 3-1. 프로젝트 생성

1. https://vercel.com 접속 → 로그인
2. **Add New Project** (또는 **New Project**) 클릭
3. GitHub 레포지토리에서 `weekly_suggest` 선택
4. **Configure Project** 화면에서:
   - **Framework Preset**: `Next.js` (자동 감지)
   - **Root Directory**: `frontend` ← **반드시 `frontend`로 변경** (기본값은 `/`)
   - Build Command: `npm run build` (기본값 유지)
   - Output Directory: `.next` (기본값 유지)

### 3-2. 환경변수 설정

같은 Configure 화면 또는 **Settings → Environment Variables**에서 입력:

| 변수명 | 입력 값 | 비고 |
|--------|---------|------|
| `BACKEND_URL` | `https://<railway-url>` | 끝에 `/` 없이 |
| `NEXT_PUBLIC_API_URL` | `https://<railway-url>/api/v1` | |

입력 예시 (Railway URL이 `https://weekly-suggest-production.up.railway.app`인 경우):
```
BACKEND_URL         = https://weekly-suggest-production.up.railway.app
NEXT_PUBLIC_API_URL = https://weekly-suggest-production.up.railway.app/api/v1
```

### 3-3. 배포 실행

**Deploy** 버튼 클릭 → 빌드 완료 대기 (약 2~3분)

빌드 성공 시 **Vercel Frontend URL** 확인:
예시: `https://weekly-suggest.vercel.app`

### 3-4. Railway CORS_ORIGINS 업데이트

Vercel URL이 확정되면 Railway로 돌아가서:

Railway 대시보드 → Variables 탭 → `CORS_ORIGINS` 값 입력/수정:
```
CORS_ORIGINS = https://weekly-suggest.vercel.app
```

저장 → Railway 자동 재배포 시작 → 완료 대기 (약 1~2분).

---

## 4. Claude vs 사용자 역할 분리

### 지금까지 완료된 것 (Claude)

| 작업 | 파일 | 상태 |
|------|------|------|
| railway.toml 작성 | `railway.toml` | ✅ 완료 |
| .gitignore 작성 | `.gitignore`, `frontend/.gitignore` | ✅ 완료 |
| 환경변수 config | `backend/app/core/config.py` | ✅ 완료 |
| Admin 인증 구조 | `backend/app/api/v1/admin.py` | ✅ 완료 |
| AdminDashboard CSR | `frontend/src/components/admin/AdminDashboard.tsx` | ✅ 완료 |
| next.config.mjs BACKEND_URL | `frontend/next.config.mjs` | ✅ 완료 |
| 시작 시 설정 검증 | `backend/app/main.py` | ✅ 완료 |
| price_context 실데이터 계산 | `backend/app/services/report_builder.py` | ✅ 완료 |
| ADMIN_API_KEY 생성 스크립트 | `scripts/generate_admin_key.py` | ✅ 완료 |
| Smoke test 문서 | `docs/deployment/SMOKE_TEST.md` | ✅ 완료 |
| 실데이터 전환 가이드 | `docs/deployment/REAL_DATA_TRANSITION.md` | ✅ 완료 |

### 사용자가 직접 해야 하는 것

| 작업 | 도구 | 비고 |
|------|------|------|
| ADMIN_API_KEY 생성 | 터미널 `python scripts/generate_admin_key.py` | 1회 |
| GitHub 레포지토리 생성 | github.com | 빈 레포 |
| `git push` | 터미널 | 코드 업로드 |
| Railway 계정 로그인 | railway.app | |
| Railway New Project | Railway 대시보드 | GitHub 레포 연결 |
| Railway 환경변수 입력 | Railway Variables 탭 | 표 참조 |
| Railway Volume 생성 | Railway Volumes 탭 | 선택 사항 |
| Vercel 계정 로그인 | vercel.com | |
| Vercel New Project | Vercel 대시보드 | Root Dir = `frontend` |
| Vercel 환경변수 입력 | Vercel Settings | BACKEND_URL 등 |
| Deploy 버튼 클릭 | Vercel 대시보드 | |
| CORS_ORIGINS 업데이트 | Railway Variables | Vercel URL 확정 후 |

### Claude가 도울 수 있는 것 (URL 제공 후)

| 작업 | 방법 |
|------|------|
| Smoke test 실행 | URL 제공 시 curl 명령 자동 실행 + 결과 분석 |
| 오류 원인 분석 | Railway 로그/에러 메시지 복사 시 진단 |
| 환경변수 값 확인 | 설정값 맞는지 검토 |
| 코드 수정 | 배포 후 발견되는 버그 수정 |
| 발행 스크립트 실행 | 첫 에디션 생성 + 발행 흐름 안내 |

---

## 5. 배포 완료 후 기록해야 할 값

배포 완료 후 아래 표를 채워서 보관해라.
다음 세션에서 이 값들이 있어야 smoke test, 발행, 운영이 가능하다.

```
================================================================
Weekly Suggest 배포 정보 (기록 보관용)
================================================================

Railway Backend URL:
  https://_____________________________________.railway.app

Vercel Frontend URL:
  https://_____________________________________.vercel.app

현재 DATA_PROVIDER_MODE:
  [ ] mock       ← 초기 배포 기본값
  [ ] fmp
  [ ] hybrid

Narrative 모드 (ANTHROPIC_API_KEY 설정 여부):
  [ ] 미설정 (PLACEHOLDER 상태로 운영)
  [ ] 설정됨 → Claude API로 자동 생성

Admin Key 관리:
  [ ] Railway Variables에 ADMIN_API_KEY 설정 완료
  [ ] 생성한 키를 안전한 곳에 저장 완료

Railway Volume:
  [ ] 설정 안 함 (재시작 시 state.db 초기화)
  [ ] /data 마운트 완료, STATE_DB_PATH=/data/state.db 설정

CORS 설정:
  [ ] CORS_ORIGINS = https://<vercel-url> 설정 완료

GitHub 레포지토리:
  https://github.com/_______________/_______________

배포 완료 날짜:
  ________________
================================================================
```

---

## 6. 다음 단계(smoke test) 입력 템플릿

배포가 완료되면, 아래 텍스트에 실제 URL을 채워서 Claude에게 전달한다.
이것이 smoke test + 운영 검증 단계의 시작 프롬프트다.

```
Weekly Suggest 배포가 완료됐어.

Railway Backend URL: https://<여기에-railway-url 입력>
Vercel Frontend URL: https://<여기에-vercel-url 입력>

현재 설정:
- DATA_PROVIDER_MODE: mock
- ANTHROPIC_API_KEY: [설정됨 / 미설정]
- Railway Volume: [설정됨 / 미설정]

다음 작업을 순서대로 진행해줘:
1. backend health check
2. latest report API 응답 확인
3. admin 엔드포인트 인증 확인 (403 검증)
4. Vercel frontend 응답 확인
5. Vercel → Railway API rewrite 동작 확인
6. 브라우저 체크 URL 목록 출력

이상이 있으면 원인 분석 후 수정 방법 알려줘.
이상 없으면 첫 에디션 발행 흐름으로 넘어가줘.
```

---

## 7. 주의사항

### Railway 관련

**Root Directory 설정 불필요**
`railway.toml`이 루트에 있으므로 Railway에서 별도 Root Directory를 설정하면 안 된다.
그대로 레포 루트에서 인식하게 두면 된다.

**무료 플랜 슬립 문제**
Railway 무료 플랜은 일정 시간 트래픽이 없으면 인스턴스가 슬립된다.
첫 요청 시 콜드 스타트 지연(약 10~30초)이 발생할 수 있다.
지속 운영 시 Railway Starter 플랜($5/월) 권장.

**state.db 초기화 문제**
Volume 없이 배포하면 Railway 인스턴스 재시작마다 state.db가 초기화된다.
초기 배포에는 괜찮지만, 에디션을 발행한 이후에는 Volume 설정이 필요하다.

**빌드 실패 시**
```bash
# 로컬에서 먼저 확인
cd backend && pip install -r requirements.txt && python -c "from app.main import app"
```

### Vercel 관련

**Root Directory 반드시 `frontend`로 설정**
설정하지 않으면 레포 루트를 Next.js 프로젝트로 인식해서 빌드 실패.

**BACKEND_URL 형식**
```
올바름:  https://weekly-suggest-production.up.railway.app
틀림:    https://weekly-suggest-production.up.railway.app/   (끝에 / 있으면 안 됨)
틀림:    weekly-suggest-production.up.railway.app           (https:// 없으면 안 됨)
```

**빌드 실패 시**
```bash
# 로컬에서 먼저 확인
cd frontend && npm run build
```

### CORS 관련

배포 후 브라우저 콘솔에서 CORS 오류가 나면:
```
Access to fetch at 'https://xxx.railway.app/...' from origin 'https://xxx.vercel.app' has been blocked by CORS policy
```
→ Railway Variables에서 `CORS_ORIGINS`가 Vercel URL과 정확히 일치하는지 확인.

### Admin Key 관련

- Admin Key는 한 번 생성 후 분실하면 Railway에서 새 키로 교체 후 재배포 필요
- `/admin` 페이지는 URL이 공개되어 있으나 키 없이는 데이터 변경 불가
- Admin Key를 브라우저 localStorage에 저장하므로, 공용 PC에서 사용 후 로그아웃 필요

### 발행 철학 재확인

```
사용자가 접속한다 → latest published edition을 보여준다
새 에디션을 발행하려면 → 스크리닝 → 검토 → publish 흐름을 거쳐야 한다
실시간 재계산은 없다
```

---

## 환경변수 전체 참조

### Railway (Backend)

| 변수 | 필수 | 초기 배포 값 | 설명 |
|------|------|-------------|------|
| `APP_ENV` | ✓ | `production` | 반드시 설정 (`ENV`는 POSIX 예약어 충돌) |
| `LOG_LEVEL` | | `INFO` | DEBUG / INFO / WARNING |
| `DATA_PROVIDER_MODE` | ✓ | `mock` | mock / fmp / hybrid |
| `ADMIN_API_KEY` | ✓ | _(생성값)_ | 64자리 hex |
| `CORS_ORIGINS` | ✓ | _(Vercel URL)_ | 쉼표로 복수 도메인 가능 |
| `MIN_PUBLISH_STOCKS` | | `5` | |
| `MAX_DATA_QUALITY_FLAGS` | | `3` | |
| `STATE_DB_PATH` | Volume 시 | `/data/state.db` | |
| `FMP_API_KEY` | fmp 시 | | FMP 키 |
| `ANTHROPIC_API_KEY` | narrative 시 | | Claude API 키 |

### Vercel (Frontend)

| 변수 | 필수 | 설명 |
|------|------|------|
| `BACKEND_URL` | ✓ | Railway URL (`https://` 포함, 끝 `/` 없이) |
| `NEXT_PUBLIC_API_URL` | ✓ | Railway URL + `/api/v1` |
