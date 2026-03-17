# Weekly Suggest — 서비스 아키텍처 설계 문서

> 이 문서는 마지막 단계에서 PDF 산출물을 만들기 위한 기반 문서다.
> 종목 제안 로직, 데이터 수집 방식, 전체 아키텍처를 구조화하여 기술한다.

---

## 1. 서비스 개요

**Weekly Suggest**는 미국 상장 중대형주 대상 구조적 저평가 분석 리포트를 격주 발행하는 웹서비스다.

### 핵심 원칙

- **발행형(Publish-based)**: 사용자 접속 시 실시간 계산 없음. 사전 검토된 결과만 노출.
- **편집자 게이트**: 자동 스크리닝 이후 편집자 검토 + Publish Guard를 통과한 종목만 발행.
- **투명한 불확실성 표현**: 모든 수치에 DataStatus(CONFIRMED/UNVERIFIED/UNAVAILABLE) 부여.
- **AI 보조, 판단은 인간**: Claude API로 서술 생성, 편집자 검토 후 발행.

### 대상 종목 기준

- 미국 상장 중대형주 (시가총액 $2B 이상)
- 일평균 거래량 1,000만 달러 이상
- 영업이익 흑자
- ADR 제외, 파산/구조조정 중 제외

---

## 2. 종목 제안 로직

### 2.1 스크리닝 파이프라인

```
UniverseFilter → Scorer → Top-N 선정
```

**UniverseFilter** — 5개 필터 순차 적용:

| 필터 | 조건 |
|------|------|
| 시가총액 | >= $2B |
| 유동성 | 일평균 거래량 >= $10M |
| 수익성 | 영업이익 > 0 |
| 상장 구조 | ADR 제외 |
| 재무 건전성 | 파산/구조조정 중 제외 |

**Scorer** — 4개 영역 복합 점수 (100점 만점):

| 영역 | 가중치 | 산출 기준 |
|------|--------|---------|
| 저평가 신호 | 40% | 섹터 대비 밸류에이션 할인율 |
| 촉매 평가 | 30% | 리레이팅 촉매 3개 충족 여부 |
| 리스크 조정 | 20% | 구조적/단기 리스크 레벨 |
| 드로우다운 | 10% | 52주 고점 대비 낙폭 |

**선정 기준**: 점수 상위 5개 (정기 발행 기준)

### 2.2 밸류에이션 분석

**사용 지표** (primary_metric으로 종목별 1개 지정):

| 지표 | 설명 | 적용 섹터 |
|------|------|---------|
| Fwd PER | 선행 주가수익비율 | Industrials, Technology |
| EV/EBITDA | 기업가치/EBITDA | Energy, Industrials |
| P/B | 주가순자산비율 | Financials |
| P/S | 주가매출비율 | Healthcare (적자 기업) |
| P/FCF | 주가잉여현금흐름비율 | Consumer Staples |
| Trailing PER | 실적 기반 PER | 범용 |

**섹터 할인 계산**:
```
discount_pct = (sector_median - stock_value) / sector_median × 100
```
양수이면 섹터 대비 저평가.

**히스토리 위치**:
3년 자사 밸류에이션 범위 내 현재 위치를 percentile로 표시.
하위 30th 이하면 "역사적 저점 수준"으로 판단.

### 2.3 촉매 평가

종목당 3개의 리레이팅 촉매(A/B/C)를 정의하고 각각의 충족 여부를 평가:

| 상태 | 설명 |
|------|------|
| MET | 촉매 조건 확인됨 |
| NOT_MET | 조건 미충족 |
| UNVERIFIABLE | 데이터 부족으로 판단 불가 |
| NOT_ASSESSED | 평가 미실시 |

### 2.4 리스크 분류

**구조적 리스크** (중장기 펀더멘털):
- 경쟁 환경 (COMPETITIVE)
- 재무 건전성 (FINANCIAL_HEALTH)
- 운영 리스크 (OPERATIONAL)
- 규제 리스크 (REGULATORY)

**단기 리스크** (3개월 내 촉발 가능):
- 거시 민감도 (MACRO_SENSITIVITY)
- 실적 리스크 (EARNINGS_RISK)
- 유동성 (LIQUIDITY)
- 지배구조 (GOVERNANCE)

각 리스크는 HIGH / MEDIUM / LOW로 심각도 분류.

### 2.5 관심 가격 구간

현재가 기준 밸류에이션 멀티플 수렴 시 이론적 가격 범위:
- 낙관 시나리오: 섹터 중앙값 × 1.1 수렴 가정
- 기본 시나리오: 섹터 중앙값 수렴 가정
- 조건부 서술: "X 촉매가 실현될 경우 Y 구간이 합리적 범위"

> **중요**: 이 구간은 목표주가(Target Price)가 아니다.

---

## 3. 데이터 수집 방식

### 3.1 데이터 제공자 계층

```
IDataProvider (추상 인터페이스)
├── MockDataProvider     — JSON 파일 (개발/테스트용)
├── FMPDataProvider      — Financial Modeling Prep REST API
├── YFinanceDataProvider — yfinance (가격 전용, 무료)
└── HybridDataProvider   — yfinance(가격) + FMP(펀더멘털)
```

환경변수 `DATA_PROVIDER_MODE`로 선택:

| 모드 | 사용처 | 비용 |
|------|--------|------|
| `mock` | 로컬 개발, UI 확인 | 무료 |
| `fmp` | 프로덕션 전체 | FMP 구독 필요 |
| `yfinance` | 가격 전용 테스트 | 무료 (제한 있음) |
| `hybrid` | 비용 최적화 | FMP 부분 구독 |

### 3.2 수집 데이터 목록

**가격 데이터** (yfinance 또는 FMP):
- 현재가, 52주 고/저점
- 1개월/3개월/6개월/YTD 수익률
- 주간 OHLCV 52포인트 (차트용)

**펀더멘털** (FMP):
- Fwd PER, Trailing PER, EV/EBITDA, P/B, P/S, P/FCF
- 시가총액, 매출, 영업이익, 순이익, FCF
- EPS 컨센서스 추정치, 가격 컨센서스

**섹터 데이터** (FMP 또는 산출):
- 섹터 중앙값 밸류에이션
- 비교 유니버스 종목 수

### 3.3 데이터 신선도

- 수집 후 72시간 이내 데이터만 CONFIRMED
- 이후: STALE 상태로 표시
- 수집 불가: UNAVAILABLE
- 수동 보정: MANUAL_OVERRIDE_APPLIED

---

## 4. 서비스 아키텍처

### 4.1 전체 구성

```
┌──────────────────────────────────────────────────────────┐
│                    PUBLIC LAYER                           │
│                                                          │
│  Next.js 14 (Vercel)                                     │
│  ├── /                  메인 (latest edition)            │
│  ├── /archive           발행 이력                         │
│  ├── /archive/[n]       에디션 상세                       │
│  ├── /report/[id]       종목 상세                         │
│  └── /disclaimer        면책 고지                         │
│                                                          │
│  SSR: Server Components → 5분 revalidate                 │
│  CSR: Admin 쓰기 작업만 → /api/v1 rewrite               │
└─────────────────────┬────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼────────────────────────────────────┐
│                   API LAYER                              │
│                                                          │
│  FastAPI (Railway)                                       │
│  ├── GET  /api/v1/reports/latest    최신 에디션          │
│  ├── GET  /api/v1/reports/{id}/stocks/{ticker}           │
│  ├── GET  /api/v1/archive           이력 목록            │
│  ├── GET  /api/v1/archive/{n}       에디션 상세          │
│  ├── GET  /api/v1/chart/{ticker}    가격 차트             │
│  └── /api/v1/admin/*                [X-Admin-Key 필요]   │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│                 STORAGE LAYER                            │
│                                                          │
│  FileStore (JSON)         StateStore (SQLite)            │
│  ├── edition_latest.json  ├── latest_pointer             │
│  ├── edition_00N.json     ├── editions                   │
│  ├── stock_{T}_{N}.json   ├── review_tasks               │
│  └── chart/{T}.json       └── review_items               │
│                                                          │
│  Railway Persistent Disk: /app/data/                     │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│               PUBLISH LAYER (내부 운영)                   │
│                                                          │
│  scripts/create_edition.py                               │
│  → UniverseFilter → Scorer → Top-N                      │
│  → review_task 생성 → SQLite + JSON 저장                 │
│                                                          │
│  scripts/generate_narratives.py                          │
│  → Claude API → 4 NarrativeBlock → JSON 반영            │
│                                                          │
│  scripts/publish_edition.py                              │
│  → Publish Guard (5조건) → PUBLISHED                    │
│  → latest_pointer 갱신 → 이전 에디션 ARCHIVED            │
└──────────────────────────────────────────────────────────┘
```

### 4.2 데이터 흐름 — 사용자 접속 시

```
브라우저 → Vercel (SSR)
  └─ fetch /api/v1/reports/latest (revalidate: 300)
       └─ FastAPI
            └─ state_store.get_latest_pointer()
                 └─ SQLite: latest_pointer → report_id
            └─ file_store.get_edition_by_id(report_id)
                 └─ JSON 파일 읽기
            └─ {"data": {...}} 반환
       └─ HTML 렌더링 → 브라우저
```

실시간 계산 없음. 파일 I/O만 발생.

### 4.3 상태 머신

```
에디션 상태:
DRAFT → PENDING_REVIEW → APPROVED → PUBLISHED → ARCHIVED
                                        ↑
                              latest_pointer 가 가리키는 상태

규칙:
- PUBLISHED 상태가 아닌 에디션은 메인 페이지에 노출되지 않는다.
- latest_pointer 는 항상 PUBLISHED 에디션 1개만 가리킨다.
- 신규 에디션이 PUBLISHED되면 이전 에디션은 자동 ARCHIVED.
```

### 4.4 NarrativeBlock 구조

Claude API로 생성하는 4개 분석 서술:

| 블록 | 내용 |
|------|------|
| `why_discounted` | 시장이 이 종목을 할인하는 구조적 이유 |
| `why_worth_revisiting` | 지금 다시 볼 만한 리레이팅 근거 |
| `key_risks_narrative` | 핵심 리스크 종합 요약 |
| `investment_context` | 투자 맥락 종합 (시장 환경 + 종목 특성) |

제약:
- 목표주가 제시 금지
- 매수/매도 권고 금지
- 수익률 보장 표현 금지
- 제공된 구조화 데이터의 수치만 참조

---

## 5. 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Storage | SQLite (상태), JSON 파일 (리포트) |
| AI | Anthropic Claude API (claude-sonnet-4-6) |
| 데이터 소스 | FMP API, yfinance |
| 배포 (권장) | Vercel + Railway |

---

## 6. 보안 고려사항

| 항목 | 현재 구현 | 추후 강화 가능 |
|------|---------|-------------|
| Admin API | X-Admin-Key 헤더 | JWT / OAuth |
| Admin UI | URL 비공개 운영 | 로그인 폼 추가 |
| API 문서 | 프로덕션 비활성화 | N/A |
| CORS | 허용 오리진 명시 | N/A |
| 데이터 | 읽기 전용 API | Rate limiting |
| 시크릿 | 환경변수 분리 | Secret Manager |

---

## 7. PDF 산출물 구성 계획

마지막 단계에서 만들 PDF 문서 구조:

```
weekly_suggest_architecture.pdf

  1. 서비스 소개 (1p)
     - 목적, 핵심 원칙, 대상 사용자

  2. 종목 제안 로직 (3p)
     - 스크리닝 파이프라인
     - 복합 점수 산출 방식
     - 밸류에이션 / 촉매 / 리스크 / 관심구간

  3. 데이터 수집 방식 (2p)
     - 제공자 계층 구조
     - 수집 데이터 목록
     - 신선도 정책

  4. 서비스 아키텍처 (2p)
     - 전체 구성 다이어그램
     - 데이터 흐름
     - 상태 머신

  5. 발행 운영 흐름 (1p)
     - 정기 발행 시나리오
     - 임시 발행 시나리오

  6. 기술 스택 및 보안 (1p)
```

PDF 생성 시 이 `ARCHITECTURE.md` 파일을 소스로 사용한다.
Pandoc, Markdown-to-PDF, 또는 별도 디자인 툴로 변환.
