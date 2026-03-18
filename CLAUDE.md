# Weekly Suggest — Claude Code 컨텍스트 가이드

> 새로운 Claude Code 세션이 시작될 때 가장 먼저 읽어야 하는 파일이다.
> 이 문서를 읽으면 프로젝트 전체 상태를 5분 안에 파악할 수 있다.

---

## 1. 서비스 한 줄 요약

미국 상장 중대형주 대상 저평가 분석 리포트를 **격주 발행(publish)** 방식으로 제공하는 웹서비스.
사용자 접속 시 실시간 계산 없음 — 사전 발행된 에디션 JSON만 제공한다.

---

## 2. 절대 원칙 (변경 금지)

| 원칙 | 설명 |
|------|------|
| **발행형 서비스** | 사용자 요청 시 재계산/재스크리닝 없음 |
| **latest = 1개** | `edition_latest.json` 이 항상 현재 노출 에디션 |
| **archive 누적** | 이전 에디션은 삭제하지 않음, `/archive` 에서 접근 가능 |
| **편집자 게이트** | 자동 스크리닝 결과는 반드시 검토·승인 후 발행 |
| **목표주가 없음** | `interest_price_range` 는 조건부 참고 구간, 목표가 아님 |
| **승인형 발행** | 완전 자동 발행 아님 — 운영자가 review/prepare/commit을 수동 실행 |

---

## 3. 현재 운영 상태 (2026-03-18 기준)

| 항목 | 값 |
|------|----|
| 최신 에디션 | VOL.3 (`re_20260317_003`) |
| 발행일 | 2026-03-17 |
| 종목 | NXPW, BLFN, STRL, VCNX, DFTL |
| 아카이브 | VOL.1 (2025-03-03), VOL.2 (2025-03-17) |
| 데이터 소스 | `data/mock/` JSON 파일 (mock 모드) |
| 차트 데이터 | `data/mock/chart/` — 10개 파일 (VOL.2 5개 + VOL.3 5개 ✅ 복구 완료) |

---

## 4. 인프라 구조 (실제 URL)

```
GitHub Repository
  https://github.com/jinajana1228/weekly_suggest
  ├── main push → Railway 자동 재배포
  ├── GitHub Actions → D-1 격주 자동 준비 (일요일 UTC 15:00, 클라우드 실행)
  └── Vercel 연결 → 프론트엔드 자동 빌드

Railway (백엔드)
  https://weeklysuggest-production.up.railway.app
  └── GET /api/v1/reports/latest → edition_latest.json 반환
  └── Health: https://weeklysuggest-production.up.railway.app/health

Vercel (프론트엔드)
  https://weekly-suggest.vercel.app
  └── SSR, 5분 revalidate
  └── BACKEND_URL = https://weeklysuggest-production.up.railway.app
```

---

## 5. 발행 파이프라인

```
screen → narrate → review → preflight → prepare → commit → verify
```

| 단계 | 자동/수동 | 설명 |
|------|---------|------|
| screen | D-1 자동 | 후보 스크리닝 → staging 생성 |
| narrate | D-1 자동 | rule-based narrative 초안 |
| review | **수동** | 운영자 내용 검토·승인 필수 |
| preflight | 기본 자동 / `--strict` 수동 | 품질 사전 점검 |
| prepare | **수동** | 발행 파일 생성 |
| commit | **수동** | git push → 즉시 프로덕션 반영 |
| verify | 수동 (commit 후) | 배포 후 API 검증 |

- 스크립트: `scripts/publish_release.py <subcommand>`
- D-1 통합: `scripts/biweekly_prep.py`
- **GitHub Actions는 GitHub 클라우드에서 실행 → 운영자 PC가 꺼져 있어도 D-1 자동 준비 완료됨**

---

## 6. 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `data/mock/reports/edition_latest.json` | 현재 latest 에디션 (교체 = 발행) |
| `data/mock/reports/edition_00N_archive.json` | 아카이브 에디션 |
| `data/mock/reports/stock_{TICKER}_{NNN}.json` | 종목 상세 리포트 |
| `data/mock/chart/{TICKER}_price_series.json` | 차트 시계열 데이터 (10개) |
| `scripts/publish_release.py` | 발행 파이프라인 CLI |
| `scripts/biweekly_prep.py` | D-1 통합 준비 스크립트 |
| `.github/workflows/biweekly_prepare.yml` | GitHub Actions 자동화 (cron 9번째 줄) |
| `backend/app/api/v1/` | FastAPI 엔드포인트 |
| `backend/app/services/screening/scorer.py` | 2버킷 스코어링 로직 |
| `backend/app/services/` | 스크리닝/분석/발행 비즈니스 로직 |
| `backend/app/storage/` | FileStore (JSON) + StateStore (SQLite) |

---

## 6-a. 2버킷 추천 로직 (2026-03-18 도입)

5개 종목을 **Bucket A (성장·수혜) 3개 + Bucket B (저평가) 2개**로 분리해 선정한다.

| 버킷 | selection_type | 선정 기준 | 핵심 스코어 구성 |
|------|---------------|-----------|-----------------|
| A | `GROWTH_TRAJECTORY` | 섹터 분산 고려 상위 3개 | 성장추세 35% + 시장확장성 20% + 정책우호도 15% + 상승여지 15% + 촉매 10% − 리스크패널티 |
| B | `UNDERVALUED` | 할인율≥10% & 촉매≥1 충족 후 상위 2개 | 할인율 35% + 역사적저렴도 20% + 촉매 20% + 낙폭 15% + 재무품질 10% − 리스크패널티 |

- 스코어링 함수: `backend/app/services/screening/scorer.py`
  - `compute_growth_trajectory_score(c)` → Bucket A 점수 (구 `compute_growth_beneficiary_score`는 래퍼로 유지)
  - `compute_undervalued_score(c)` → Bucket B 점수
  - `bucket_select_candidates(passed, bucket_a_count=3, bucket_b_count=2)`
  - `_select_with_sector_diversity()` → Bucket A 섹터 분산 (동일 섹터 최대 1개)
- `market_growth_hint`: MOCK_UNIVERSE에 0.0~1.0 수동 설정 (AI반도체=0.95, 에너지전환=0.80, 자산운용=0.65 등)
- `policy_tailwind_hint`: MOCK_UNIVERSE에 0.0~1.0 수동 설정 (AI인프라=0.85, 청정에너지=0.75, 금융규제완화=0.55 등)
- **`selection_type` 필드**: `GROWTH_TRAJECTORY` 3개, `UNDERVALUED` 2개 구조 유지 (`GROWTH_BENEFICIARY` 사용 금지)

---

## 7. 환경변수 요약

### Railway (백엔드) — https://weeklysuggest-production.up.railway.app

| 변수 | 현재 설정값 | 설명 |
|------|------------|------|
| `APP_ENV` | `production` | 필수 |
| `ADMIN_API_KEY` | (별도 보관) | 64자리 hex, Admin UI 접근 키 |
| `CORS_ORIGINS` | `https://weekly-suggest.vercel.app` | Vercel URL |
| `DATA_PROVIDER_MODE` | `mock` | 현재 mock 모드 운영 중 |
| `FMP_API_KEY` | (미설정, 실데이터 전환 시 필요) | FMP API 키 |
| `ANTHROPIC_API_KEY` | (미설정, narrative 생성 시 필요) | Claude API 키 |

### Vercel (프론트엔드) — https://weekly-suggest.vercel.app

| 변수 | 현재 설정값 |
|------|------------|
| `BACKEND_URL` | `https://weeklysuggest-production.up.railway.app` |
| `NEXT_PUBLIC_API_URL` | `https://weeklysuggest-production.up.railway.app/api/v1` |

> 실제 키 값은 이 문서에 없다. Railway/Vercel 대시보드 → Variables 에서 확인.

---

## 8. 로컬 개발 시작

```bash
# 백엔드
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (새 터미널)
cd frontend
npm install && npm run dev
```

접속: `http://localhost:3000` / API: `http://localhost:8000/api/v1/reports/latest`

---

## 9. 중요 문서 읽기 순서

1. 이 파일 (`CLAUDE.md`) — 지금 읽는 중
2. `docs/PROJECT_CONTEXT.md` — 서비스 목적, 운영 구조 전체
3. `docs/deployment/OPERATIONS.md` — 발행 SOP (반복 운영 절차)
4. `docs/deployment/AUTOMATION.md` — D-1/D-0 자동화 설계
5. `docs/ARCHITECTURE.md` — 기술 아키텍처 상세
6. `docs/INFRA_SETUP.md` — 인프라 연결 구조 (계정/URL/Secret)
7. `docs/CHANGELOG.md` — 주요 변경 이력
8. `docs/INCIDENTS.md` — 이슈 발생 및 해결 이력

---

## 10. 자주 하는 실수 방지

- `edition_latest.json` 을 직접 편집하지 말 것 → `prepare` 커맨드로만 생성
- `data/mock/reports/` 의 archive 파일을 삭제하지 말 것
- `commit` 커맨드 실행 = git push = 즉시 Railway 재배포 = 프로덕션 즉시 반영
- `preflight --strict` 에서 ERROR 나면 `prepare` 실행 불가 (의도된 게이트)
- 차트 데이터 파일명: `{TICKER}_price_series.json` (대문자 ticker, 언더스코어)
- Railway Redeploy ≠ 데이터 변경. 데이터는 JSON 파일 + git push로만 변경됨
- `BACKEND_URL` 끝에 `/` 붙이면 Vercel rewrite 오작동
- **차트 JSON `interest_range_band`**: 반드시 `lower_bound` / `upper_bound` 키 사용. `low` / `high` 사용하면 `_transform_chart()` KeyError → API 500 → 상세 페이지 404 발생 (2026-03-18 인시던트)
- **새 에디션 차트 파일**: `git add` 후 커밋할 것. untracked 상태로 push하면 Railway Docker 빌드 시 파일이 없어 차트 API가 빈 배열 반환
- **`selection_type` 필드**: `edition_latest.json`의 각 stocks 항목과 `stock_{TICKER}_{NNN}.json`에 반드시 포함. `GROWTH_TRAJECTORY` 3개, `UNDERVALUED` 2개 구조 유지 (`GROWTH_BENEFICIARY` 사용 금지)
- **발행 후 verify**: 차트 API 5개 HTTP 200 + price_series.length > 0 확인 필수
