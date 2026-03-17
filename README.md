# Weekly Suggest

미국 상장 중대형주를 대상으로 저평가 가능성이 있는 종목을 자동 선별하고,
애널리스트 수준의 구조적 분석 리포트를 **발행(publish) 기반**으로 제공하는 웹서비스입니다.

> **핵심 원칙**: 사용자가 접속할 때마다 스크리닝/리포트 생성을 다시 수행하지 않습니다.
> 스크리닝 → 검토 → 발행 흐름을 통해 사전에 확정된 에디션만 최신 리포트로 노출됩니다.

---

## 배포 (Vercel + Railway)

> 로컬 개발이 아닌 실제 배포 방법은 [`docs/deployment/DEPLOYMENT.md`](docs/deployment/DEPLOYMENT.md) 참조.

| 구성 요소 | 플랫폼 | 역할 |
|---------|--------|------|
| Frontend | Vercel | Next.js SSR, 5분 캐시 |
| Backend  | Railway | FastAPI + SQLite + JSON |
| 발행 흐름 | 로컬 스크립트 → git push | 격주 에디션 생성 → 배포 |

**배포 요약 (3단계):**
```bash
# 1. Railway: 레포 연결 + 환경변수 설정 (CORS_ORIGINS, ADMIN_API_KEY 등)
# 2. Vercel: frontend/ 디렉터리 연결 + BACKEND_URL, NEXT_PUBLIC_API_URL 설정
# 3. 확인: curl https://<railway-url>/health
```

**격주 발행 흐름:**
```bash
python scripts/create_edition.py          # 스크리닝
python scripts/generate_narratives.py ... # (선택) AI 서술
python scripts/publish_edition.py ...     # 발행 + latest 교체
git add data/mock/reports/ && git push    # Railway 자동 재배포
```

---

## 발행 운영 구조

### 발행 흐름

```
[스크리닝 실행]
  python scripts/create_edition.py
        ↓
[review_task 생성 → SQLite 저장]
  state.db: review_tasks, review_items
        ↓
[Admin 검토 (http://localhost:3000/admin)]
  종목별: PENDING → APPROVED / FLAGGED / REJECTED
        ↓
[Publish Guard 검사]
  - 종목 수 >= MIN_PUBLISH_STOCKS (기본 5)
  - 모든 종목 APPROVED
  - data_quality_flag_count <= MAX_DATA_QUALITY_FLAGS
  - 이미 PUBLISHED 상태이면 재발행 차단
        ↓
[발행 실행]
  python scripts/publish_edition.py --report-id ... --task-id ...
        ↓
[SQLite latest_pointer 갱신]
  state.db: latest_pointer.report_id = 새 에디션
        ↓
[메인 페이지(/) 에서 새 에디션 노출]
  GET /api/v1/reports/latest → latest_pointer → FileStore JSON
```

### 발행 일정

| 유형 | `issue_type` | 주기 |
|------|-------------|------|
| 격주 정기 | `REGULAR_BIWEEKLY` | 격주 월요일 오전 8시 |
| 실적 트리거 | `EARNINGS_TRIGGERED` | 주요 실적 발표 직후 |
| 특별 발행 | `SPECIAL_EVENT` | 시장 이벤트 발생 시 |

### 상태 머신

```
DRAFT → PENDING_REVIEW → APPROVED → PUBLISHED → ARCHIVED
```

- PUBLISHED 이전 상태는 메인 페이지에 **절대 노출되지 않음**
- `latest_pointer` 테이블이 현재 노출 에디션을 단일 행으로 관리

---

## 폴더 구조

```
weekly_suggest/
├── frontend/          # Next.js 14 프론트엔드
├── backend/           # FastAPI 백엔드
│   └── app/
│       ├── api/v1/    # REST 엔드포인트
│       ├── services/
│       │   ├── provider/     # IDataProvider 인터페이스
│       │   │   ├── base.py           # 추상 인터페이스
│       │   │   ├── mock_provider.py  # Mock (JSON 파일)
│       │   │   ├── fmp_provider.py   # FMP REST API
│       │   │   ├── yfinance_provider.py  # yfinance (가격 전용)
│       │   │   ├── hybrid_provider.py    # yfinance + FMP 결합
│       │   │   └── factory.py        # DATA_PROVIDER_MODE 기반 팩토리
│       │   ├── screening/    # universe_filter, scorer, pipeline
│       │   ├── analysis/     # valuation, catalyst, risk, interest_range
│       │   ├── publication/  # publish_guard.py
│       │   └── report_builder.py
│       └── storage/
│           ├── file_store.py   # JSON 파일 읽기 (정적 mock)
│           └── state_store.py  # SQLite 상태 (review / publish / latest_pointer)
├── data/
│   ├── mock/          # Mock 데이터 (JSON)
│   │   ├── reports/   # 에디션 & 종목 리포트
│   │   └── chart/     # 가격 시계열 (5개 종목)
│   └── state.db       # SQLite 상태 DB (자동 생성)
└── scripts/           # 수동 실행 스크립트
    ├── run_screening.py       # 스크리닝 1회 실행
    ├── create_edition.py      # 에디션 생성 (스크리닝 + task 등록)
    ├── publish_edition.py     # 발행 실행 (guard 검사 + latest_pointer 갱신)
    ├── create_review_task.py  # review task만 생성
    └── publish_flow.py        # 전체 흐름 샘플 (레거시)
```

---

## 빠른 시작 (Quick Start)

> Mock 모드로 30초 안에 전체 UI를 확인할 수 있습니다.

### 1단계 — 백엔드 실행

```bash
cd weekly_suggest/backend

# [최초 1회] 가상환경 생성 + 의존성 설치
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

pip install -r requirements.txt
cp .env.example .env           # DATA_PROVIDER_MODE=mock 기본값

# 서버 시작
uvicorn app.main:app --reload --port 8000
```

백엔드가 정상 실행되면:
- API: `http://localhost:8000/api/v1/reports/latest` → JSON 응답 확인
- Swagger: `http://localhost:8000/docs`

### 2단계 — 프론트엔드 실행 (새 터미널)

```bash
cd weekly_suggest/frontend

npm install   # 최초 1회
npm run dev
```

> 기본 포트 3000이 사용 중이면 자동으로 3001로 이동합니다.
> 터미널 출력에서 `Local: http://localhost:300X` 확인 후 해당 URL로 접속하세요.

**반드시 백엔드(8000)를 먼저 실행한 뒤 프론트엔드를 시작하세요.**

---

## 실행 방법 (상세)

---

## Mock 모드에서 확인 가능한 화면

`.env`의 `DATA_PROVIDER_MODE=mock`이면 실제 API 연동 없이 모든 화면 확인 가능합니다.

> 아래 `PORT`는 터미널 출력에 표시된 실제 포트(보통 3000, 사용 중이면 3001)로 대체하세요.

| URL | 설명 |
|-----|------|
| `http://localhost:PORT/` | 메인 — 최신 PUBLISHED 에디션 (VOL.2, 5개 종목) |
| `http://localhost:PORT/report/ri_20250317_002_MFGI` | MFGI — Industrials, 촉매 3/3 MET, 차트 있음 |
| `http://localhost:PORT/report/ri_20250317_002_RVNC` | RVNC — Financials, P/B 기준, 차트 있음 |
| `http://localhost:PORT/report/ri_20250317_002_HLTH` | HLTH — Healthcare, Catalyst B 미확인, 차트 있음 |
| `http://localhost:PORT/report/ri_20250317_002_CSTM` | CSTM — Consumer Staples, 저리스크, 차트 있음 |
| `http://localhost:PORT/report/ri_20250317_002_ENXT` | ENXT — Energy, 고리스크, 41% 할인, 차트 있음 |
| `http://localhost:PORT/archive` | 발행 이력 목록 (VOL.1 + VOL.2) |
| `http://localhost:PORT/archive/1` | VOL.1 — 과거 에디션 상세 |
| `http://localhost:PORT/admin` | 검토 관리 — 종목 상태 변경 + 발행 결정 인터랙션 |
| `http://localhost:PORT/disclaimer` | 면책 고지 전문 |

---

## Scripts — 수동 실행

모든 스크립트는 `weekly_suggest/` 루트 디렉터리에서 실행합니다.

### Narrative 자동 생성

```bash
cd weekly_suggest

# 드라이런 (API 호출 없이 대상 확인)
python scripts/generate_narratives.py --dry-run

# 실제 생성 (ANTHROPIC_API_KEY 필요)
python scripts/generate_narratives.py --report-id re_20250317_002

# 이미 생성된 narrative 재생성
python scripts/generate_narratives.py --report-id re_20250317_002 --overwrite
```

생성 조건:
- `ANTHROPIC_API_KEY`가 `.env`에 설정되어 있어야 합니다.
- API 키 미설정 또는 호출 실패 시 `PLACEHOLDER` 상태로 graceful fallback 합니다.
- narrative가 없어도 publish는 가능합니다 (`NARRATIVE_REQUIRE_FOR_PUBLISH=False` 기본값).
- publish 시 narrative를 필수화하려면 `.env`에서 `NARRATIVE_REQUIRE_FOR_PUBLISH=True` 설정.

생성되는 4개 블록:
| 블록 | 설명 |
|------|------|
| `why_discounted` | 시장 할인 원인 분석 |
| `why_worth_revisiting` | 리레이팅 근거 |
| `key_risks_narrative` | 핵심 리스크 종합 |
| `investment_context` | 투자 맥락 요약 |

> **제약**: 목표주가, 매수/매도 권고, 수익 보장 표현은 절대 생성하지 않습니다.
> 제공된 구조화 데이터의 수치만 참조합니다.

---

### 에디션 생성 (스크리닝 + task 등록)

```bash
cd weekly_suggest
python scripts/create_edition.py

# 발행 유형 지정
python scripts/create_edition.py --issue-type EARNINGS_TRIGGERED

# 드라이런 (DB 변경 없음)
python scripts/create_edition.py --dry-run
```

출력 예시:
```
[1/4] 스크리닝 실행 중...
      후보 12개 -> 선정 5개
        MFGI   score=97.2  discount=33.3%  risk=LOW
...
[4/4] 생성 결과:
      Edition number : VOL.3
      issue type     : REGULAR_BIWEEKLY
다음 단계: python scripts/publish_edition.py --report-id re_20260317_003 --task-id task_...
```

### 에디션 발행 (guard 검사 + latest_pointer 갱신)

```bash
python scripts/publish_edition.py \
  --report-id re_20250317_002 \
  --task-id task_20250315_001

# 드라이런
python scripts/publish_edition.py \
  --report-id re_20250317_002 \
  --task-id task_20250315_001 \
  --dry-run
```

### mock screening 1회 실행

```bash
python scripts/run_screening.py

# 옵션
python scripts/run_screening.py --top-n 3 --min-cap 3.0 --verbose
```

### 전체 publish flow 샘플 (레거시)

```bash
# 드라이런
python scripts/publish_flow.py --dry-run

# 실제 실행
python scripts/publish_flow.py
```

> **주의**: 스크립트 실행 시 backend 가상환경의 python을 사용해야 합니다.
> Windows: `backend\venv\Scripts\python.exe scripts/create_edition.py`

---

## Mock 데이터 구성

**에디션 2 (최신, 2025-03-17)** — 5개 종목, 차트 데이터 포함

| 티커 | 기업명 | 섹터 | 특이사항 |
|------|--------|------|---------|
| MFGI | Meridian Fastening Group | Industrials | 촉매 3/3, STRONG_SIGNAL, 33% 할인 |
| RVNC | Ravencroft Bancorp | Financials | P/B 기준, 금리 리스크 |
| HLTH | HealthCore Systems | Health Care | Catalyst B UNVERIFIABLE (WARNING 2건) |
| CSTM | Creston Consumer Brands | Consumer Staples | 저리스크, 방어주 |
| ENXT | EnerNext Resources | Energy | 고리스크 HIGH, 41% 최대 할인 |

**에디션 1 (아카이브, 2025-03-03)**
- DXPC (Healthcare), LGSV (Industrials), MRVX (IT), WTRX (Utilities), BXMT (Materials)

**Mock 유니버스 (스크리닝 후보 12개)**

| 티커 | 필터 결과 | 선정 여부 | 제외 이유 |
|------|----------|----------|---------|
| MFGI | 통과 | 선정 | — |
| RVNC | 통과 | 선정 | — |
| HLTH | 통과 | 선정 | — |
| CSTM | 통과 | 선정 | — |
| ENXT | 통과 | 선정 | — |
| NXST | 통과 | 미선정 | insufficient_composite_score |
| ATHN | 통과 | 미선정 | insufficient_composite_score |
| PLXS | 제외 | — | market_cap_below_2B |
| MTRX | 제외 | — | avg_daily_volume_below_threshold |
| BCRX | 제외 | — | no_operating_income |
| LVMUY | 제외 | — | adr_excluded |
| CLNE | 제외 | — | bankruptcy_risk |

---

## API 엔드포인트 목록

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/reports/latest` | 최신 PUBLISHED 에디션 (latest_pointer 기반) |
| GET | `/api/v1/reports/{report_id}/stocks/{ticker}` | 종목 상세 리포트 |
| GET | `/api/v1/archive` | 아카이브 목록 |
| GET | `/api/v1/archive/{edition_number}` | 특정 에디션 |
| GET | `/api/v1/chart/{ticker}` | 차트 데이터 |
| GET | `/api/v1/admin/review-tasks` | 검토 태스크 목록 |
| PATCH | `/api/v1/admin/review-tasks/{task_id}/items/{item_id}` | 리뷰 아이템 상태 변경 |
| POST | `/api/v1/admin/review-tasks/{task_id}/decision` | 발행 결정 (APPROVE/REJECT/HOLD) → APPROVE 시 latest_pointer 갱신 |
| POST | `/api/v1/screening/run` | 스크리닝 파이프라인 실행 |
| GET | `/api/v1/screening/universe` | Mock 유니버스 전체 후보 |

---

## 실데이터 연동

### Provider 전환

`.env`에서 `DATA_PROVIDER_MODE` 값만 변경하면 코드 수정 없이 provider가 교체됩니다.

```bash
# Mock (기본값, 개발/테스트)
DATA_PROVIDER_MODE=mock

# FMP API (프로덕션)
DATA_PROVIDER_MODE=fmp
FMP_API_KEY=your_actual_key

# yfinance (가격 데이터 전용, 무료)
DATA_PROVIDER_MODE=yfinance

# Hybrid: yfinance(가격) + FMP(컨센서스/어닝) — 권장 프로덕션 구성
DATA_PROVIDER_MODE=hybrid
FMP_API_KEY=your_actual_key
```

| Mode | 유니버스 | 가격 | 컨센서스 | 어닝 | 비용 |
|------|---------|------|---------|------|------|
| mock | JSON | JSON | JSON | JSON | 무료 |
| fmp | FMP screener | FMP | FMP | FMP | 유료 |
| yfinance | 미지원 | yfinance | yfinance(낮음) | yfinance | 무료 |
| hybrid | FMP | yfinance | FMP | FMP | FMP만 유료 |

### LLM 서술 생성 연동

```bash
ANTHROPIC_API_KEY=your_key
```

`backend/app/services/narrative/generator.py`에서 Claude API를 호출하여
`analyst_style_summary`의 4개 NarrativeBlock을 자동 생성합니다.

---

## SQLite 스키마 (state.db)

| 테이블 | 용도 |
|--------|------|
| `review_tasks` | 에디션별 검토 태스크 |
| `review_items` | 종목별 검토 상태 (PENDING/APPROVED/FLAGGED/REJECTED) |
| `edition_status` | 에디션 발행 상태 (DRAFT/PUBLISHED 등) |
| `editions` | 에디션 메타 (번호, 유형, 데이터 기준일) |
| `latest_pointer` | 현재 노출 에디션 포인터 (항상 단일 행) |

`latest_pointer` 갱신 시점:
- `POST /api/v1/admin/review-tasks/{task_id}/decision` → APPROVE
- `python scripts/publish_edition.py` 실행 후 guard 통과 시

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| 차트 | Recharts (다크모드 커스텀) |
| 백엔드 | FastAPI + Python 3.11+ + Pydantic v2 |
| 상태 저장 | JSON 파일 (리포트 정적) + SQLite (review/publish 상태) |
| Mock 데이터 | JSON 파일 (`data/mock/`) |
| LLM | Claude (Anthropic) — 향후 연동 |
| 데이터 소스 | FMP + yfinance — 향후 연동 |

---

## 설계 원칙

1. **발행 기반 서비스**: 페이지 접속 시 스크리닝/리포트 재계산 없음. 사전 발행된 에디션만 노출.
2. **latest_pointer 단일 진실**: 현재 최신 에디션은 SQLite `latest_pointer` 테이블이 결정. PUBLISHED 상태 에디션만 포인터 가능.
3. **목표주가 없음**: `interest_price_range`는 섹터 중앙값 역산 조건부 참고치
4. **리스크 필수**: `structural_risks`, `short_term_risks`, `bear_case_points`는 항상 표시
5. **데이터 상태 투명**: `DataStatus` enum으로 모든 데이터 신뢰도 명시
6. **Mock → Real 전환**: `IDataProvider` 인터페이스로 provider 교체 가능 (코드 무변경)
7. **발행 게이트**: 자동 생성 리포트는 반드시 사람 검토(SQLite 상태) 후 발행
