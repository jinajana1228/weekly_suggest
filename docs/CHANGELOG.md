# Weekly Suggest — 변경 이력 (CHANGELOG)

> 발행 이력은 `docs/deployment/OPERATIONS.md` §7 참조.
> 이 문서는 **코드·구조·인프라 변경**을 기록한다.

---

## 2026-03-18 — 2버킷 추천 로직 + selection_type + UI 개선 4건

### 수정 (버그 픽스)

- `backend/app/api/v1/chart.py` — `_transform_chart()` `interest_range_band` 방어 코드 추가
  - `lower_bound`/`upper_bound` 없으면 `low`/`high` 키로 폴백 처리
  - 이전: `irb_raw["lower_bound"]` → VOL.3 차트 JSON에서 KeyError → HTTP 500 → 상세 페이지 404
  - 이후: `.get("lower_bound", .get("low"))` 방식으로 양쪽 스키마 수용

- `data/mock/chart/{NXPW,BLFN,STRL,VCNX,DFTL}_price_series.json` — `interest_range_band` 스키마 표준화
  - `{low, high, color}` → `{lower_bound, upper_bound, label, color_hint}` 로 통일

### 추가 (신규 기능)

- `backend/app/services/screening/scorer.py` — 2버킷 스코어링 로직 전면 재작성
  - `compute_growth_beneficiary_score()`: 성장·모멘텀·EPS리비전·촉매·섹터테일윈드 기반
  - `compute_undervalued_score()`: 섹터할인·역사적저렴도·촉매·낙폭·재무품질 기반
  - `bucket_select_candidates()`: Bucket A 3개(GROWTH_BENEFICIARY) + Bucket B 2개(UNDERVALUED)

- `backend/app/services/screening/universe_filter.py` — VOL.3 MOCK_UNIVERSE 확장 필드
  - `revenue_growth_yoy_pct`, `eps_revision_trend`, `operating_margin_pct`, `roe_pct`
  - `price_1m_change_pct`, `price_3m_change_pct`, `drawdown_from_52w_high_pct`
  - `sector_tailwind_hint`, `historical_pct_rank` 추가

- `data/mock/reports/edition_latest.json` — stocks 각 항목에 `selection_type` 필드 추가

- `data/mock/reports/stock_{NXPW,BLFN,STRL,VCNX,DFTL}_003.json` — `selection_type` 필드 추가

- `frontend/src/types/enums.ts` — `SelectionType` 타입 추가 (`GROWTH_BENEFICIARY | UNDERVALUED`)

- `frontend/src/types/schema.ts` — `StockCard.selection_type?`, `ArchiveStockSummary.selection_type?` 추가

- `frontend/src/components/report/StockCard.tsx` — 성장·수혜/저평가 유형 배지 렌더링 추가

### UI 개선 (즉시 반영)

- `backend/app/api/v1/archive.py` — `/archive` 목록 API stocks에 `selection_type` 필드 포함
- `frontend/src/app/archive/page.tsx` — 아카이브 종목 요약 그리드에 선정 유형 배지 추가
- `frontend/src/components/chart/PriceChart.tsx` — 차트 legend에 관심 구간 실제 가격 범위 표시 (`$X — $Y`)
- `frontend/src/components/report/StockCard.tsx` — 시총 레이블 추가 (`시총 $1.2B` 형태)
- `frontend/src/app/report/[report_item_id]/page.tsx` — sticky nav에 차트 탭 추가 + 차트 div `id="chart"`

### 커밋 이력

| 커밋 | 내용 |
|------|------|
| `2aa486f` | VOL.3 차트 파일 5개 git 추가 (untracked 상태 수정) |
| `e240a16` | 차트 API 500 수정 (interest_range_band 스키마 + 방어 코드) |
| `ad01805` | 2버킷 스코어링 + selection_type 필드 + 메인 카드 배지 |
| `1a6c70f` | UI 개선 4건 (아카이브 배지·차트 범위·시총·차트 탭) |

---

## 2026-03-17 — VOL.3 차트 복구 + 자동화 문서 보강

### 추가
- `data/mock/chart/` 에 VOL.3 신규 5종목 차트 데이터 파일 생성
  - `NXPW_price_series.json`, `BLFN_price_series.json`, `STRL_price_series.json`
  - `VCNX_price_series.json`, `DFTL_price_series.json`
  - 각 52개 주간 OHLCV 바, 2025-03-17 ~ 2026-03-14
  - reference_lines (WEEK_52_HIGH/LOW), event_markers (분기 실적), interest_range_band 포함
- `scripts/_gen_chart_data.py` — 차트 JSON 생성기 (재사용 가능)
- `docs/INFRA_SETUP.md` — 인프라 연결 구조 문서 신규 작성
- `docs/PROJECT_CONTEXT.md` — 서비스 컨텍스트 종합 문서 신규 작성
- `docs/CHANGELOG.md` — 변경 이력 문서 신규 작성 (이 파일)
- `docs/INCIDENTS.md` — 이슈 이력 문서 신규 작성
- `docs/NOTION_WIKI.md` — Notion 운영 위키 신규 작성
- `CLAUDE.md` — Claude Code 세션 컨텍스트 가이드 신규 작성

### 변경
- `docs/deployment/AUTOMATION.md`
  - §4에 GitHub Actions 클라우드 실행 명시 (PC 전원 무관 설명 추가)
  - §4에 cron 표현식 변경 위치 명시 (주석 포함 예시)

---

## 2026-03-17 — D-1/D-0 격주 자동화 구조 구현

### 추가
- `scripts/biweekly_prep.py` — D-1 통합 준비 스크립트 (screen + narrate + preflight)
- `.github/workflows/biweekly_prepare.yml` — GitHub Actions 격주 자동화 workflow
  - 스케줄: 매주 일요일 UTC 15:00 (KST 월요일 00:00)
  - 짝수 ISO 주만 실행
  - workflow_dispatch 수동 트리거 지원 (provider, dry_run, context_note, force_run)
  - prep/biweekly-YYYYMMDD 브랜치에 staging 파일 push
  - GitHub Actions summary에 운영자 체크리스트 표시
- `docs/deployment/AUTOMATION.md` — 격주 자동화 설계 문서
  - A안(권장) vs B안 비교
  - 스케줄러 방식 비교 (GitHub Actions 권장)
  - 실패 처리 기준 + rollback 절차
  - 운영자 최소 체크포인트 8단계

### 변경
- `docs/deployment/OPERATIONS.md`
  - 헤더에 AUTOMATION.md 참조 추가
  - §3 격주 발행 정책에 D-1 자동 준비 흐름 박스 추가

---

## 2026-03-17 — 실데이터 Provider 연동 기반 구현

### 추가
- `backend/app/services/provider/fmp_provider.py`
  - `get_financials(ticker)` 메서드 추가 (`/v3/income-statement` + `/v3/key-metrics-ttm`)
  - `get_stock_snapshot()` 에 financials 임베딩
- `backend/app/services/provider/yfinance_provider.py`
  - `_YFINANCE_STATIC_UNIVERSE` (36개 미국 주요 종목)
  - `get_universe_candidates()` 정적 유니버스 필터링
- `backend/app/services/screening/pipeline.py`
  - `_enrich_candidate_for_scoring()` 함수 추가
  - 4개 스코어링 필드 실데이터 보완: `sector_discount_pct`, `catalyst_met_count`, `risk_level_max`, `week_52_position_pct`
- `backend/.env.example` — 환경변수 예시 파일

### 변경
- `scripts/publish_release.py`
  - FMP API 키 없을 때 `sys.exit` → 경고 + mock fallback
  - yfinance 미설치 시 경고 + mock fallback
  - 스코어링 필드 기본값 사용 시 경고 메시지 추가

---

## 초기 구현 (VOL.1 ~ VOL.3)

### 아키텍처 확정
- 발행형(publish-based) 서비스 구조
- `edition_latest.json` 교체 + git push = 발행 패턴
- SQLite `latest_pointer` 단일 진실 원칙
- Docker 재배포 시 state.db 초기화 → edition_latest.json fallback

### 스크리닝 파이프라인
- `UniverseFilter` (5개 필터) → `Scorer` (4개 영역) → Top-N
- `IDataProvider` 인터페이스로 mock/fmp/yfinance/hybrid 전환 가능

### 발행 파이프라인 CLI
- `scripts/publish_release.py` — screen/narrate/review/preflight/prepare/commit/verify
- `scripts/biweekly_prep.py` — D-1 통합 준비

### 분석 엔진
- `compute_valuation()` — 섹터 대비 밸류에이션 할인율
- `assess_catalysts()` — 리레이팅 촉매 3개 평가
- `assess_risks()` — 구조적/단기 리스크 분류
- `compute_interest_price_range()` — 관심 가격 구간

### 배포 구성
- Railway (FastAPI), Vercel (Next.js 14)
- `railway.toml` 루트 배치
- next.config.mjs BACKEND_URL rewrite

### Mock 데이터
- VOL.1 (5개 종목), VOL.2 (5개 종목, 차트 포함), VOL.3 (5개 종목, 차트 포함)
