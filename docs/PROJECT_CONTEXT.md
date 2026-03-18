# Weekly Suggest — 프로젝트 컨텍스트

> **최종 업데이트**: 2026-03-18
> **문서 목적**: 서비스 목적, 운영 구조, 설계 원칙을 한 곳에서 파악하기 위한 종합 컨텍스트

---

## 1. 서비스 목적

**Weekly Suggest**는 미국 상장 중대형주(시가총액 $2B 이상)를 대상으로
구조적 저평가 가능성이 있는 종목을 자동 선별하고,
애널리스트 수준의 분석 리포트를 **격주 발행 방식**으로 제공하는 웹서비스다.

### 핵심 설계 원칙

| 원칙 | 내용 |
|------|------|
| **발행형(Publish-based)** | 사용자 접속 시 실시간 스크리닝/계산 없음. 사전 검토·발행된 에디션만 노출 |
| **latest = 항상 1개** | 메인 페이지는 항상 최신 발행본 1개만 대표 |
| **archive 누적** | 이전 발행본은 삭제 없이 `/archive` 에서 영구 접근 가능 |
| **승인형 발행** | 완전 무인 발행 아님 — 운영자가 검토·승인 후 수동으로 발행 확정 |
| **편집자 게이트** | 자동 스크리닝 결과는 반드시 사람이 검토·승인 후에만 발행 |
| **투명한 불확실성** | 모든 수치에 DataStatus (CONFIRMED / UNVERIFIED / UNAVAILABLE) 부여 |
| **목표주가 없음** | `interest_price_range` 는 섹터 중앙값 역산 조건부 참고 구간 |

---

## 2. 현재 운영 상태 (2026-03-17 기준)

### 서비스 URL

| 역할 | URL |
|------|-----|
| 메인 (최신 에디션) | https://weekly-suggest.vercel.app |
| 발행 이력 | https://weekly-suggest.vercel.app/archive |
| 종목 상세 | https://weekly-suggest.vercel.app/report/[id] |
| 운영자 Admin | https://weekly-suggest.vercel.app/admin |
| Backend API | https://weeklysuggest-production.up.railway.app |
| GitHub | https://github.com/jinajana1228/weekly_suggest |

### 발행 이력

| VOL | report_id | 발행일 | 종목 | 상태 |
|-----|-----------|--------|------|------|
| **3** | re_20260317_003 | 2026-03-17 | NXPW, BLFN, STRL, VCNX, DFTL | **PUBLISHED** |
| 2 | re_20250317_002 | 2025-03-17 | MFGI, RVNC, HLTH, CSTM, ENXT | ARCHIVED |
| 1 | re_20250303_001 | 2025-03-03 | DXPC, LGSV, MRVX, WTRX, BXMT | ARCHIVED |

### 데이터 파일 현황

```
data/mock/reports/
  edition_latest.json        ← 현재 latest (VOL.3, re_20260317_003)
  edition_002_archive.json   ← VOL.2 아카이브
  edition_001_archive.json   ← VOL.1 아카이브
  stock_NXPW_003.json        ← VOL.3 종목 상세 (5개)
  stock_BLFN_003.json
  stock_STRL_003.json
  stock_VCNX_003.json
  stock_DFTL_003.json
  stock_MFGI_re002.json      ← VOL.2 종목 상세 (5개)
  stock_RVNC_re002.json
  stock_HLTH_re002.json
  stock_CSTM_re002.json
  stock_ENXT_re002.json

data/mock/chart/             ← 10개 전체 (VOL.3 차트 복구 완료 ✅)
  NXPW_price_series.json     ← VOL.3 신규 (2026-03-17 생성)
  BLFN_price_series.json
  STRL_price_series.json
  VCNX_price_series.json
  DFTL_price_series.json
  MFGI_price_series.json     ← VOL.2 기존
  RVNC_price_series.json
  HLTH_price_series.json
  CSTM_price_series.json
  ENXT_price_series.json
```

---

## 3. 전체 아키텍처 요약

```
사용자 브라우저
    │
    ▼
Vercel (Next.js 14, SSR)   https://weekly-suggest.vercel.app
  ├── / → GET /api/v1/reports/latest (5분 캐시)
  ├── /archive → GET /api/v1/archive
  ├── /report/[id] → GET /api/v1/reports/{id}/stocks/{ticker}
  └── /admin → Admin UI (X-Admin-Key 인증)
    │
    ▼ HTTPS
Railway (FastAPI)   https://weeklysuggest-production.up.railway.app
  ├── FileStore → data/mock/reports/*.json (리포트 데이터)
  ├── FileStore → data/mock/chart/*.json (차트 데이터)
  └── StateStore → data/state.db (SQLite: 발행 상태)
    │
    ▼ git push 트리거
GitHub Repository   https://github.com/jinajana1228/weekly_suggest
  └── .github/workflows/biweekly_prepare.yml (D-1 자동 준비)
```

### 데이터 흐름 (사용자 접속)

```
브라우저 → Vercel SSR
  → GET /api/v1/reports/latest (revalidate: 300s)
  → FastAPI
    → state_store.get_latest_pointer()
      → 없으면 file_store.get_latest_edition()
    → edition_latest.json 반환
  → HTML 렌더링
```

**실시간 계산 없음. 파일 I/O만 발생.**

### latest / archive 실제 동작 예시

```
현재 상태:
  edition_latest.json       → VOL.3 (PUBLISHED, 메인 페이지 노출)
  edition_002_archive.json  → VOL.2 (ARCHIVED, /archive/2 에서 접근)
  edition_001_archive.json  → VOL.1 (ARCHIVED, /archive/1 에서 접근)

VOL.4 발행 시:
  edition_003_archive.json  ← edition_latest.json 복사 (VOL.3 아카이브)
  edition_latest.json       ← 신규 VOL.4 내용으로 교체
  git push → Railway 재배포 → 메인 페이지에 VOL.4 노출
```

---

## 4. 발행 파이프라인

### 전체 단계

```
screen → narrate → review → preflight → prepare → commit → verify
```

| 단계 | 스크립트 | 설명 | 자동/수동 |
|------|---------|------|---------|
| `screen` | `publish_release.py screen` | 후보 스크리닝 → staging 생성 | **D-1 자동** |
| `narrate` | `publish_release.py narrate` | Rule-based narrative 초안 | **D-1 자동** |
| `review` | `publish_release.py review` | 운영자 내용 검토·승인 | **수동 필수** |
| `preflight` | `publish_release.py preflight` | 발행 품질 사전 점검 | 기본: D-1 자동 / `--strict`: 수동 |
| `prepare` | `publish_release.py prepare` | 발행 파일 생성 | **수동 필수** |
| `commit` | `publish_release.py commit` | git push → Railway 재배포 | **수동 필수** |
| `verify` | `publish_release.py verify` | 배포 후 API 검증 | 수동 (commit 후) |

### D-1 / D-0 운영 구조

```
[D-1 일요일 00:00 KST] ← GitHub Actions 자동 트리거
  실행 위치: GitHub 클라우드 서버 (운영자 PC 꺼져 있어도 실행됨)
  작업: screen + narrate + preflight(기본)
  결과: data/staging/ 파일 생성
        prep/biweekly-YYYYMMDD 브랜치 push
        GitHub Actions summary에 운영자 체크리스트 표시

[D-0 월요일] ← 운영자 수동 실행
  ① GitHub Actions summary 확인
  ② git checkout prep/biweekly-YYYYMMDD
  ③ review --show → narrative 검토
  ④ review --approve-all → 승인
  ⑤ preflight --strict → ERROR 없을 때만 다음 단계
  ⑥ prepare → edition_latest.json 생성
  ⑦ commit → git push → Railway 재배포 (3~5분)
  ⑧ verify → 배포 확인
```

> **현재 구조는 "승인형 발행"이다.**
> 자동화는 D-1 준비(screen+narrate+preflight)까지만.
> review, prepare, commit은 반드시 운영자가 직접 실행.

---

## 5. 스크리닝 로직

### 파이프라인

```
UniverseFilter → 2버킷 Scorer → Bucket A 3개 + Bucket B 2개 선발
```

### UniverseFilter — 5개 필터

| 필터 | 조건 |
|------|------|
| 시가총액 | $2B 이상 |
| 유동성 | 일평균 거래량 $10M 이상 |
| 수익성 | 영업이익 > 0 |
| 상장 구조 | ADR 제외 |
| 재무 건전성 | 파산/구조조정 중 제외 |

### 2버킷 선정 구조 (2026-03-18 최종 확정)

| 버킷 | selection_type | 종목 수 | 선정 기준 |
|------|---------------|---------|---------|
| A | `GROWTH_TRAJECTORY` | 3개 | 성장 추세 스코어 상위 + 섹터 분산 (동일 섹터 최대 1개) |
| B | `UNDERVALUED` | 2개 | 섹터할인 ≥10% & 촉매 ≥1 충족 후 저평가 스코어 상위 |

### Bucket A — 성장 추세 스코어 구성

| 구성요소 | 가중치 | 내용 |
|---------|--------|------|
| 현재 성장 추세 (`growth_trend_score`) | ×0.35 | 매출성장 40% + EPS리비전 30% + 영업마진 15% + ROE 15% |
| 시장 구조 성장 여지 (`market_expansion_score`) | ×0.20 | `market_growth_hint` 직접 설정 (0.0–1.0) |
| 정책 방향성 우호도 (`policy_alignment_score`) | ×0.15 | `policy_tailwind_hint` 직접 설정 (0.0–1.0) |
| 추가 상승 여지 (`upside_remaining_score`) | ×0.15 | 52주 하단 기준, 30%+ 프리미엄 시 최대 50% 감점 |
| 촉매 (`catalyst_score`) | ×0.10 | 촉매 충족 개수 / 3 |
| 리스크 패널티 | −0.20 | HIGH=0.8, MEDIUM=0.5, LOW=0.2 |

### Bucket B — 저평가 스코어 구성

| 구성요소 | 가중치 | 내용 |
|---------|--------|------|
| 섹터 할인율 | ×0.35 | 40% 할인 → 만점 |
| 역사적 저렴함 | ×0.20 | 3년 밸류에이션 백분위 (낮을수록 높은 점수) |
| 촉매 | ×0.20 | Value trap 방어 |
| 낙폭 | ×0.15 | 52주 고점 대비 낙폭 |
| 재무 품질 | ×0.10 | 영업마진 기반 |
| 리스크 패널티 | −0.20 | 동일 |

---

## 6. 데이터 제공자

| 모드 | 설명 | 현재 운영 | 비용 |
|------|------|---------|------|
| `mock` | JSON 파일 (개발·테스트) | **현재 운영 중** | 무료 |
| `fmp` | Financial Modeling Prep REST API | 미전환 | FMP 구독 필요 |
| `yfinance` | 가격 데이터 전용 | 미전환 | 무료 |
| `hybrid` | yfinance(가격) + FMP(펀더멘털) | 미전환 | FMP 부분 구독 |

환경변수 `DATA_PROVIDER_MODE` 으로 선택. 코드 변경 없이 전환 가능.

---

## 7. 차트 데이터 구조

파일 위치: `data/mock/chart/{TICKER}_price_series.json`

```json
{
  "ticker": "NXPW",
  "interval": "1wk",
  "data": [
    { "date": "2025-03-17", "open": 50.80, "high": 51.10, "low": 50.20, "close": 50.80, "volume": 1200000 }
  ],
  "reference_lines": [
    { "label": "WEEK_52_HIGH", "value": 54.60, "color": "#ef4444" },
    { "label": "WEEK_52_LOW",  "value": 31.40, "color": "#22c55e" }
  ],
  "event_markers": [
    { "date": "2025-05-07", "type": "earnings", "label": "Earnings", "price": 52.10 }
  ],
  "interest_range_band": {
    "low": 33.00, "high": 37.50, "color": "rgba(59,130,246,0.12)"
  }
}
```

API: `GET /api/v1/chart/{ticker}`
transform: `data[]` → `price_series[]`, `reference_lines[].label` → `line_type`

**현재 상태**: VOL.3 신규 5종목(NXPW, BLFN, STRL, VCNX, DFTL) 차트 파일 복구 완료 (2026-03-17)

---

## 8. 에디션 상태 머신

```
DRAFT → PENDING_REVIEW → APPROVED → PUBLISHED → ARCHIVED
                                         ↑
                               latest_pointer 가 가리키는 상태
```

- PUBLISHED 이전 상태는 메인 페이지에 절대 노출되지 않는다.
- `latest_pointer` (SQLite) → 없으면 `edition_latest.json` 직접 읽기 (fallback)
- 신규 에디션 PUBLISHED 시 이전 에디션 자동 ARCHIVED

---

## 9. 수동 작업으로 남아 있는 항목

매 발행 시 운영자가 직접 해야 하는 작업:

| 작업 | 이유 |
|------|------|
| `market_context_note` 작성 | 이번 에디션 시황 요약 (사람 판단 필요) |
| narrative 초안 검토·수정 | 자동 생성된 텍스트 품질 검증 |
| `review --approve-all` 실행 | 내용 확인 없는 자동 승인 불가 |
| `preflight --strict` 확인 | ERROR 없는 상태에서만 prepare 진행 |
| `prepare` 실행 | 발행 파일 생성 (되돌리기 어려운 작업) |
| `commit` 실행 | git push = 즉시 프로덕션 반영 |

---

## 10. 남은 주요 과제

| 과제 | 우선순위 | 설명 |
|------|---------|------|
| UI narrative 직접 수정 | 높음 | Admin UI 에서 narrative 텍스트 직접 편집 기능 |
| 실데이터 provider 안정화 | 중간 | FMP/yfinance 모드 실환경 검증 |
| 스케줄 발행 고도화 | 낮음 | 완전 무인 발행 (품질 자동 평가 기준 확립 후) |
| PDF 산출물 생성 | 낮음 | `docs/ARCHITECTURE.md` 기반 아키텍처 문서 PDF |
