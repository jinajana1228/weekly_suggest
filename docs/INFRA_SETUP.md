# Weekly Suggest — 인프라 연결 구조

> **최종 업데이트**: 2026-03-17
> **대상 독자**: 인프라 구조를 파악하거나 새로 설정하려는 사람
> **실제 API 키/비밀번호는 이 문서에 없다** — Railway/Vercel 대시보드에서 직접 확인

---

## 1. 현재 운영 중인 서비스 URL

| 서비스 | URL | 역할 |
|--------|-----|------|
| **Vercel (프론트엔드)** | https://weekly-suggest.vercel.app | 사용자 접속 메인 페이지 |
| **Railway (백엔드)** | https://weeklysuggest-production.up.railway.app | FastAPI + JSON 데이터 |
| **GitHub Repository** | https://github.com/jinajana1228/weekly_suggest | 코드 + 데이터 저장소 |
| **Backend Health** | https://weeklysuggest-production.up.railway.app/health | 서버 상태 확인 |
| **Admin UI** | https://weekly-suggest.vercel.app/admin | 운영자 관리 페이지 |

---

## 2. 전체 서비스 연결 구조

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Repository                                           │
│  https://github.com/jinajana1228/weekly_suggest              │
│                                                             │
│  ├── main 브랜치 push                                        │
│  │     ├── Railway 자동 재배포 트리거 (3~5분)                │
│  │     └── Vercel 자동 빌드 트리거 (1~2분)                  │
│  │                                                          │
│  └── .github/workflows/biweekly_prepare.yml                 │
│        └── GitHub Actions (GitHub 클라우드 서버 실행)        │
│              PC 전원 OFF 상태여도 자동 실행됨               │
│              └── D-1 자동 준비 → prep 브랜치 push           │
└─────────────────────────────────────────────────────────────┘
           │ push                           │ push
   ┌───────▼────────────────┐     ┌─────────▼──────────────┐
   │  Railway (백엔드)       │     │   Vercel (프론트엔드)    │
   │                        │◄────│                         │
   │  FastAPI               │HTTPS│  Next.js 14 (SSR)       │
   │  SQLite (state.db)     │     │  5분 revalidate          │
   │  JSON 리포트 파일       │     │  /api/v1/* → Railway    │
   │                        │     │  프록시 rewrite          │
   │  *.up.railway.app      │     │  *.vercel.app           │
   └────────────────────────┘     └─────────────────────────┘
          ▲                                   ▲
    운영자 CLI (로컬)                    사용자 브라우저
    scripts/publish_release.py
```

---

## 3. GitHub 설정

**Repository**: https://github.com/jinajana1228/weekly_suggest

### 역할
- 코드 단일 저장소 (frontend + backend + scripts + data)
- Railway / Vercel 배포 소스 (push 시 자동 배포 트리거)
- GitHub Actions D-1 자동화 실행 환경

### Actions Secrets (Settings → Secrets and variables → Actions)

| Secret | 용도 | 현재 상태 |
|--------|------|---------|
| `FMP_API_KEY` | D-1 자동화 실데이터 사용 시 | [직접 입력 필요 — 실데이터 전환 시] |
| `GITHUB_TOKEN` | prep 브랜치 push | 자동 제공, 설정 불필요 |

### 브랜치 구조

| 브랜치 | 설명 |
|--------|------|
| `main` | 프로덕션 기준 브랜치 (push = 즉시 배포) |
| `prep/biweekly-YYYYMMDD` | D-1 자동 준비 결과 브랜치 (GitHub Actions 자동 생성) |

---

## 4. Railway 설정 (백엔드)

**URL**: https://weeklysuggest-production.up.railway.app

### 역할
- FastAPI 서버 호스팅 (Docker 기반)
- JSON 리포트 파일 서빙 (`data/mock/reports/`, `data/mock/chart/`)
- SQLite 상태 DB (`state.db`) 관리
- `main` 브랜치 push 시 자동 재배포 (3~5분)

### 빌드/시작 구성 (`railway.toml` — 루트에 존재)

```
빌드: cd backend && pip install -r requirements.txt
시작: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

> `railway.toml` 이 프로젝트 루트에 있어 Railway 가 자동 인식.
> Railway 대시보드에서 별도 Root Directory 설정 불필요.

### 환경변수 (Variables 탭) — 현재 설정 기준

| 변수 | 현재 값 | 비고 |
|------|---------|------|
| `APP_ENV` | `production` | 필수 (`ENV` 는 POSIX 예약어라 사용 불가) |
| `ADMIN_API_KEY` | (별도 보관) | Admin UI 접근 키, 64자리 hex |
| `CORS_ORIGINS` | `https://weekly-suggest.vercel.app` | Vercel URL 정확히 입력 |
| `DATA_PROVIDER_MODE` | `mock` | 현재 mock 모드 운영 중 |
| `LOG_LEVEL` | `INFO` | |
| `MIN_PUBLISH_STOCKS` | `5` | |
| `MAX_DATA_QUALITY_FLAGS` | `3` | |

### 선택 환경변수 (미설정 시 기본값 또는 fallback)

| 변수 | 조건 | 현재 상태 |
|------|------|---------|
| `FMP_API_KEY` | fmp/hybrid 모드 전환 시 | [직접 입력 필요] |
| `ANTHROPIC_API_KEY` | LLM narrative 생성 시 | [직접 입력 필요] |
| `STATE_DB_PATH` | Volume 마운트 시 | [Volume 설정 후 `/data/state.db` 입력] |

### Volume (SQLite 영속성)

Railway 인스턴스는 재배포 시 임시 파일이 초기화된다.
`state.db` (발행 이력, latest_pointer)를 보존하려면 Volume 설정:

```
Railway 대시보드 → 해당 서비스 → Volumes 탭
→ Add Volume → Mount Path: /data
→ Variables 탭 → STATE_DB_PATH = /data/state.db
```

> Volume 없이도 서비스는 동작한다.
> fallback: `state.db` 없으면 `edition_latest.json` 을 직접 읽음.
> 에디션 발행 이후에는 Volume 설정 권장.

### 데이터 변경 원칙

```
⚠️  Railway 재배포 버튼 클릭 ≠ 데이터 변경
```

리포트 데이터 변경은 반드시 이 순서로:
1. `scripts/publish_release.py prepare` → JSON 파일 생성
2. `scripts/publish_release.py commit` → git push
3. Railway 자동 재배포 (3~5분 대기)

### Health Check

```bash
curl https://weeklysuggest-production.up.railway.app/health
# 기대 응답: {"status":"ok","env":"production","provider_mode":"mock","version":"0.2.0"}
```

---

## 5. Vercel 설정 (프론트엔드)

**URL**: https://weekly-suggest.vercel.app

### 역할
- Next.js 14 프론트엔드 호스팅 (SSR, 5분 revalidate)
- `/api/v1/*` 경로를 Railway API 로 투명 프록시

### 프로젝트 설정 (재생성 시 참고)

```
Framework Preset: Next.js  (자동 감지)
Root Directory:   frontend  ← 반드시 "frontend" (기본값 "/" 아님)
Build Command:    npm run build
Output Directory: .next
```

### 환경변수 — 현재 설정 기준

| 변수 | 현재 값 |
|------|---------|
| `BACKEND_URL` | `https://weeklysuggest-production.up.railway.app` |
| `NEXT_PUBLIC_API_URL` | `https://weeklysuggest-production.up.railway.app/api/v1` |

> `BACKEND_URL` 끝에 `/` 가 있으면 rewrite 경로 오작동 — 절대 붙이지 말 것.

### API 프록시 동작

```
일반 페이지 (SSR):
  Vercel 서버 → fetch → Railway API

Admin UI 쓰기 (CSR):
  브라우저 → Vercel /api/v1/* → Railway /api/v1/*
             (next.config.mjs rewrite)
```

---

## 6. GitHub Actions 설정 (D-1 자동화)

**파일**: `.github/workflows/biweekly_prepare.yml`

### 스케줄

```yaml
on:
  schedule:
    - cron: '0 15 * * 0'   # 매주 일요일 UTC 15:00 = KST 월요일 00:00
```

스케줄 변경 시 이 줄 수정. [crontab.guru](https://crontab.guru) 에서 검증.

### 핵심 동작

| 항목 | 내용 |
|------|------|
| 실행 위치 | **GitHub 클라우드 서버** |
| PC 전원 | **무관** — 운영자 PC가 꺼져 있어도 자동 실행됨 |
| 격주 필터 | 짝수 ISO 주만 실행 (홀수 주 변경: `== 0` → `== 1`) |
| 수동 실행 | GitHub → Actions 탭 → "Run workflow" |
| 실행 결과 | GitHub → Actions 탭 → Summary → 운영자 체크리스트 표시 |

### 자동 생성 브랜치

D-1 준비 완료 후 `prep/biweekly-YYYYMMDD` 브랜치에 staging 파일 push.
운영자는 D-0 (월요일)에 이 브랜치를 checkout 후 수동 발행.

---

## 7. 계정 연결 관계

```
GitHub 계정 (jinajana1228)
  └── weekly_suggest 레포지토리
        ├── Railway 연결 (GitHub App OAuth)
        │     └── main push → weeklysuggest-production.up.railway.app 자동 재배포
        ├── Vercel 연결 (GitHub App OAuth)
        │     └── main push → weekly-suggest.vercel.app 자동 빌드
        └── GitHub Actions (클라우드 실행)
              └── Secrets: FMP_API_KEY [직접 입력 필요]
```

---

## 8. 운영 중 채워야 할 정보

아래 항목은 실제 값을 안전한 곳(비밀번호 관리자 등)에 보관. 이 파일에는 기입 위치만 표시.

```
ADMIN_API_KEY 보관 위치:  [직접 입력 필요]
FMP_API_KEY 보관 위치:    [직접 입력 필요, 실데이터 전환 시]
ANTHROPIC_API_KEY 보관:   [직접 입력 필요, narrative 생성 시]
Railway Volume 설정 여부: [ ] 설정됨 / [ ] 미설정
배포 완료일:              2026-03-17
```

---

## 9. 장애 복구 참조

| 상황 | 확인 경로 |
|------|---------|
| 백엔드 응답 없음 | railway.app → 해당 서비스 → Deployments → 로그 확인 |
| 프론트엔드 빌드 실패 | vercel.com → 해당 프로젝트 → Deployments → 빌드 로그 |
| D-1 준비 실패 | github.com/jinajana1228/weekly_suggest → Actions 탭 → 실패 워크플로우 → 로그 |
| latest 이전 에디션 반환 | `edition_latest.json` 내용 확인 + `git log` 로 push 완료 여부 확인 |
| Admin 401/403 오류 | Railway Variables → `ADMIN_API_KEY` 설정 여부 확인 |
| CORS 오류 | Railway Variables → `CORS_ORIGINS` 값이 `https://weekly-suggest.vercel.app` 과 정확히 일치하는지 확인 |
| 차트 데이터 없음 | `data/mock/chart/{TICKER}_price_series.json` 존재 여부 확인 |

rollback 절차: `docs/deployment/AUTOMATION.md` §5 참조.
