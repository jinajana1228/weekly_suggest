# Weekly Suggest — 운영 SOP (Standard Operating Procedure)

> **문서 기준**: VOL.3 발행 완료 / 2026-03-18 (추천 로직 최종 확정)
> **운영 구조**: JSON-only 발행 + Git push → Railway 자동 재배포
> **발행 자동화**: `scripts/publish_release.py` (screen / narrate / review / preflight / prepare / commit / verify)
> **격주 자동화**: `.github/workflows/biweekly_prepare.yml` + `scripts/biweekly_prep.py`
> **자동화 상세**: `docs/deployment/AUTOMATION.md` 참조
> **이 문서는 반복 운영에 직접 사용하는 절차서다.**

---

## 1. 운영 목적

Weekly Suggest는 격주로 발행되는 **정적 리포트 서비스**다.

- 사용자 접속 시 실시간 계산하지 않는다
- 사전에 준비된 JSON 발행본만 제공한다
- `latest`는 항상 최신 발행본 1개만 대표한다
- `archive`는 이전 발행본을 누적·영구 보관한다

---

## 2. 현재 운영 상태

| 항목 | 내용 |
|------|------|
| 최신 에디션 | VOL.3 (`re_20260317_003`) |
| 발행일 | 2026-03-17 |
| 종목 | NXPW, BLFN, STRL, VCNX, DFTL |
| 아카이브 | VOL.1, VOL.2 보관 중 |
| 백엔드 | Railway (Docker) |
| 프론트엔드 | Vercel |
| 데이터 소스 | `data/mock/reports/` JSON 파일 |

### 현재 파일 구조

```
data/mock/reports/
  edition_latest.json          ← 현재 latest (VOL.3)
  edition_002_archive.json     ← VOL.2 아카이브
  edition_001_archive.json     ← VOL.1 아카이브
  stock_NXPW_003.json          ← VOL.3 종목 상세
  stock_BLFN_003.json
  stock_STRL_003.json
  stock_VCNX_003.json
  stock_DFTL_003.json
  stock_MFGI_re002.json        ← VOL.2 종목 상세
  stock_RVNC_re002.json
  stock_HLTH_re002.json
  stock_CSTM_re002.json
  stock_ENXT_re002.json
```

### latest 반영 경로 (실제 동작)

```
GET /api/v1/reports/latest
  1. state_store.get_latest_pointer() → None  (state.db는 Docker 재배포마다 초기화)
  2. fallback: file_store.get_latest_edition()
  3. → edition_latest.json 반환
```

**결론**: `edition_latest.json` 교체 + git push = 발행 완료.

---

## 3. 격주 발행 정책

| 항목 | 기준 |
|------|------|
| 정기 발행 주기 | 격주 월요일 오전 |
| 발행 준비 시점 | D-1 (일요일 자정, GitHub Actions 자동 실행) |
| 에디션 번호 | 직전 VOL.N → VOL.N+1 순번 |
| 종목 수 | 5개 (정기 발행 기준) |
| 파일 네이밍 | 아래 규칙 참조 |

### D-1 자동 준비 흐름

```
[D-1 일요일 00:00 KST]  GitHub Actions 자동 트리거
  screen → narrate → preflight (기본)
  → staging 파일 → prep/biweekly-YYYYMMDD 브랜치 push
  → Actions summary 에 운영자 체크리스트 표시

[D-0 월요일]  운영자 수동 실행
  review --approve-all → preflight --strict → prepare → commit → verify
```

> 자동화 상세 설계: `docs/deployment/AUTOMATION.md`
> D-1 준비 스크립트: `scripts/biweekly_prep.py`
> GitHub Actions workflow: `.github/workflows/biweekly_prepare.yml`

### 파일 네이밍 규칙

| 파일 종류 | 패턴 | 예시 |
|-----------|------|------|
| 최신 에디션 | `edition_latest.json` | (고정명) |
| 아카이브 에디션 | `edition_{NNN}_archive.json` | `edition_003_archive.json` |
| 종목 상세 | `stock_{TICKER}_{NNN}.json` | `stock_NXPW_004.json` |

- `NNN` = 에디션 번호 3자리 zero-padding (예: 003, 004)
- `{NNN}`은 `report_id`의 마지막 세그먼트와 동일 (예: `re_20260331_004` → `004`)

---

## 4. VOL.N 발행 SOP

> **자동화 스크립트**: `scripts/publish_release.py`
> 전체 파이프라인: `screen → narrate → review → preflight → prepare → commit → verify`

### 발행 가능 상태 기준

| 상태 | 의미 | preflight 결과 |
|------|------|----------------|
| `analyst_style_summary.*.status = APPROVED` | 운영자 검토 완료 | `--strict` 통과 |
| `analyst_style_summary.*.status = DRAFT` | 자동 생성, 미검토 | 기본 모드 WARN / `--strict` 모드 ERROR |
| `analyst_style_summary.*.status = PLACEHOLDER` | 내용 없음 | 항상 ERROR (prepare 차단) |
| `reviewer_approved = true` | 모든 블록 APPROVED 상태 | Admin UI에 "검토완료" 표시 |
| `publication_meta.reviewed_by` 설정됨 | 검토자 기록 | Admin UI에 검토자 표시 |

**권장 발행 기준**: `review --approve-all` 완료 + `preflight --strict` 통과

---

### 운영자 역할 (수동 준비)

```
[ ] 신규 5개 종목 선정
    └─ GROWTH_TRAJECTORY (성장 추세) 3개 + UNDERVALUED (저평가) 2개 구성 확인
    └─ GROWTH_TRAJECTORY 3개는 섹터 분산 확인 (동일 섹터 최대 1개 원칙)
[ ] 각 종목 상세 JSON 작성 → data/staging/ 에 저장
    (파일명 자유, 예: TICK1.json / stock_TICK1_draft.json)
    └─ 각 JSON에 selection_type 필드 포함 필수 (GROWTH_TRAJECTORY 또는 UNDERVALUED)
    └─ GROWTH_BENEFICIARY 용어 사용 금지 (2026-03-18 이후 폐기)
[ ] MOCK_UNIVERSE에 신규 종목 추가 시 market_growth_hint + policy_tailwind_hint 필드 설정
    └─ 두 필드 모두 0.0–1.0 범위 직접 설정
[ ] 차트 JSON 5개 작성 → data/mock/chart/{TICKER}_price_series.json
    └─ interest_range_band 키: lower_bound / upper_bound 사용 (low/high 사용 금지)
    └─ git add 후 커밋 필수 (untracked 상태로 push 시 Railway에 파일 없음)
[ ] market_context_note 문구 준비 (이번 에디션 시황 요약)
```

---

### Step 0 — 드라이런 검증 (선택)

```cmd
cd C:\Users\MUSINSA\Desktop\Vibe Coding\weekly_suggest

python scripts\publish_release.py prepare ^
  --stocks-dir data\staging ^
  --dry-run
```

파일을 생성하지 않고 검증·체크리스트만 출력한다.

---

### Step 1-b — narrative 자동 초안 생성 (narrate)

스크리닝으로 생성된 `data/staging/` draft 파일에 `analyst_style_summary` 4개 블록을 자동 생성한다.
유료 LLM 없이 rule-based 템플릿으로 동작한다.

```cmd
python scripts\publish_release.py narrate
```

옵션:

| 옵션 | 설명 |
|------|------|
| `--stocks-dir PATH` | 대상 디렉토리 (기본: data/staging) |
| `--overwrite` | 기존 narrative 덮어쓰기 (기본: 기존 있으면 스킵) |
| `--dry-run` | 파일 변경 없이 출력만 |

생성 후 각 종목 파일의 `analyst_style_summary` 내용을 검토하고:
- 내용 수정이 필요하면 직접 편집
- 검토 완료된 블록은 `"status": "DRAFT"` → `"APPROVED"` 로 변경

**`--overwrite` 사용 기준:**
| 상황 | 권장 |
|------|------|
| 신규 draft 파일 (첫 narrate) | `--overwrite` 불필요 |
| screen 재실행 후 기존 draft 갱신 | `--overwrite` 사용 |
| 운영자 수정 후 재생성 불필요 | `--overwrite` 사용 안 함 (수정 보존) |
| VOL.N 발행 실패 후 재시도 | `--overwrite` 후 다시 review |

---

### Step 1-c — narrative 검토 (review)

`narrate`로 생성된 초안을 검토하고 승인한다.

```cmd
REM 현재 검토 상태 확인
python scripts\publish_release.py review --show

REM 전체 일괄 승인 (내용 확인 후)
python scripts\publish_release.py review --approve-all --reviewer "편집자명"

REM 특정 종목만 승인
python scripts\publish_release.py review --ticker MFGI,RVNC --reviewer "편집자명"
```

승인 시 자동으로:
- 각 블록 `status: "DRAFT"` → `"APPROVED"`
- `reviewer_approved: true`
- `publication_meta.reviewed_by` / `reviewed_at` 기록

> **Admin UI 대안**: `/admin` 페이지 접속 → 상단 "발행 준비 (Staging)" 패널 → 종목별 "narrative 승인" 버튼

---

### Step 1-d — 발행 전 사전 점검 (preflight)

prepare 실행 전에 누락·미완성 항목을 사전에 점검한다.

```cmd
REM 기본 모드 (DRAFT 블록은 경고, prepare 실행 가능)
python scripts\publish_release.py preflight ^
  --context-note "이번 에디션 시황 요약 문구"

REM strict 모드 (DRAFT 블록도 오류 — review --approve-all 완료 후 사용)
python scripts\publish_release.py preflight --strict ^
  --context-note "이번 에디션 시황 요약 문구"
```

4가지 항목을 검사한다:

| 점검 항목 | 기본 모드 | `--strict` 모드 |
|-----------|-----------|-----------------|
| market_context_note 미입력 | ERROR | ERROR |
| 필수 필드 누락 | ERROR | ERROR |
| narrative PLACEHOLDER/빈 값 | ERROR | ERROR |
| narrative DRAFT 상태 | WARN | ERROR |
| placeholder 마커 잔존 | WARN | WARN |

- **ERROR** (exit 1): prepare 실행 차단
- **WARN**: prepare 실행 허용, 검토 권장

---

### Step 2 — 발행 준비 (prepare)

스크립트가 아래 작업을 자동 수행한다:
- 현재 latest `edition_number` 읽기 → `next_num = N+1` 계산
- 직전 `edition_latest.json` → `edition_{N:03d}_archive.json` 복사 + status ARCHIVED
- staging 파일 → `stock_{TICKER}_{NNN}.json` 이름 변환 후 reports/ 에 저장
- `edition_latest.json` 신규 생성 (종목 요약 자동 추출)
- JSON 문법 검증 + 구조 일관성 검증

```cmd
python scripts\publish_release.py prepare ^
  --stocks-dir data\staging ^
  --context-note "이번 에디션 시황 요약 문구"
```

추가 옵션:

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--pub-date YYYYMMDD` | 발행일 지정 | 오늘 |
| `--data-as-of YYYY-MM-DD` | 데이터 기준일 | pub-date |
| `--issue-type` | REGULAR_BIWEEKLY / EARNINGS_TRIGGERED / SPECIAL_EVENT | REGULAR_BIWEEKLY |
| `--min-stocks N` | 최소 종목 수 | 5 |

prepare 완료 후 생성된 `edition_latest.json` 과 종목 파일 내용을 편집기에서 최종 확인한다.

---

### Step 3 — git commit + push (commit)

```cmd
python scripts\publish_release.py commit
```

- 변경 파일 목록 자동 계산 후 확인 프롬프트 출력
- `y` 입력 시 git add → commit → push 순서로 자동 실행
- 커밋 메시지 기본값: `publish: VOL.N re_YYYYMMDD_NNN 정기 발행`

커밋 메시지 직접 지정:
```cmd
python scripts\publish_release.py commit --message "publish: VOL.4 re_20260331_004 정기 발행"
```

push 없이 commit만:
```cmd
python scripts\publish_release.py commit --no-push
```

> push 후 Railway가 자동으로 Docker 이미지를 재빌드한다 (약 3~5분).

---

### Step 4 — 배포 후 검증 (verify)

Railway 재배포 완료 후 실행한다.

```cmd
python scripts\publish_release.py verify
```

6가지 항목을 자동 확인하고 통과/실패를 출력한다:

| 체크 | 기대 결과 |
|------|-----------|
| `/health` | 정상 응답, admin_key_set |
| `/reports/latest` | 신규 VOL.N, 5종목 일치 |
| `/archive` | 각 VOL 1건씩, 중복 없음 |
| `/archive/N-1` | ARCHIVED 상태 |
| `/stocks/{TICKER}` | 종목 상세 응답 |
| `/admin/review-tasks` | HTTP 403 |

> **추가 수동 검증 항목 (스크립트 미포함, 직접 curl 확인)**
>
> | 체크 | 기대 결과 |
> |------|-----------|
> | `/chart/{TICKER}?period_days=365` (5개 각각) | HTTP 200, `price_series.length > 0` |
> | `/reports/latest` → stocks[*].selection_type | `GROWTH_TRAJECTORY` 3개, `UNDERVALUED` 2개 |
> | Vercel 종목 상세 5페이지 | HTTP 200 (404 아닌지) |

API URL 직접 지정 (기본값과 다를 경우):
```cmd
python scripts\publish_release.py verify --api https://weeklysuggest-production.up.railway.app
```

---

### 수동 발행 (스크립트 없이)

스크립트 사용이 불가한 경우를 위한 fallback 절차:

```cmd
REM 1. 직전 latest → archive 복사
copy data\mock\reports\edition_latest.json data\mock\reports\edition_NNN_archive.json
REM → edition_NNN_archive.json 편집: "PUBLISHED" → "ARCHIVED"

REM 2. edition_latest.json → 신규 에디션 내용으로 교체

REM 3. stock_{TICKER}_{NNN}.json 5개 생성

REM 4. JSON 검증
python -c "import json,pathlib; [print('OK' if not print(f.name) else '', end='') for f in pathlib.Path('data/mock/reports').glob('*.json') if json.load(open(f,encoding='utf-8')) or True]"

REM 5. git commit + push
git add data\mock\reports\edition_latest.json
git add data\mock\reports\edition_NNN_archive.json
git add data\mock\reports\stock_TICK1_NNN.json ... (5개)
git commit -m "publish: VOL.N re_YYYYMMDD_NNN 정기 발행"
git push
```

---

## 5. 문제 발생 시 우선 확인 항목

### latest가 이전 에디션을 반환하는 경우

1. `edition_latest.json`의 `edition_number`, `report_id` 확인
2. git push가 정상적으로 완료됐는지 확인 (`git log --oneline -3`)
3. Railway 재배포가 완료됐는지 확인 (Railway 대시보드 → Deployments)
4. `/health` 응답의 `build` 필드로 최신 코드가 배포됐는지 확인

### archive에 같은 에디션이 2번 나오는 경우

`edition_latest.json`과 동일한 내용의 `edition_{NNN}_archive.json`이 동시에 존재하는 경우다.

```cmd
REM 해당 archive 파일 삭제
del data\mock\reports\edition_NNN_archive.json

git add data\mock\reports\edition_NNN_archive.json
git commit -m "fix: edition_NNN_archive.json 중복 제거"
git push
```

### /archive/N 이 잘못된 에디션을 반환하는 경우

`file_store.get_edition_by_number()` 로직 확인:
- `edition_{NNN}_archive.json` 파일명과 내부 `edition_number` 필드가 일치하는지 확인
- `edition_latest.json`의 `edition_number` 필드가 올바른지 확인

### 종목 상세(`/reports/{report_id}/stocks/{ticker}`)가 404인 경우

파일명 규칙 확인:
- `stock_{TICKER}_{NNN}.json` — `NNN`은 `report_id.split("_")[-1]` 결과와 동일해야 함
- 예: `re_20260331_004` → `stock_TICK1_004.json`
- 파일명 대소문자 확인 (TICKER는 대문자)

### admin 403이 아닌 200을 반환하는 경우

Railway Variables에서 `ADMIN_API_KEY` 설정 여부 확인:
```cmd
curl -s %API%/health
REM "diag_admin_key_set": true 여부 확인
```
`false`이면 Railway 대시보드 → Variables → `ADMIN_API_KEY` 값 확인·재설정.

---

## 6. 공개 URL 구조

| URL | 내용 | 접근 |
|-----|------|------|
| `https://weekly-suggest.vercel.app/` | 최신 발행 에디션 | 외부 공개 |
| `https://weekly-suggest.vercel.app/archive` | 발행 이력 전체 | 외부 공개 |
| `https://weekly-suggest.vercel.app/archive/N` | VOL.N 에디션 상세 | 외부 공개 |
| `https://weekly-suggest.vercel.app/report/[id]` | 종목 상세 리포트 | 외부 공개 |
| `https://weekly-suggest.vercel.app/disclaimer` | 면책 고지 | 외부 공개 |
| `/admin` | 검토 관리 UI | 내부 접근 전용 |
| `/api/v1/admin/*` | Admin API | X-Admin-Key 필요 |

---

## 7. 발행 이력

| VOL | report_id | 발행일 | 종목 | 상태 |
|-----|-----------|--------|------|------|
| 3 | re_20260317_003 | 2026-03-17 | NXPW, BLFN, STRL, VCNX, DFTL | PUBLISHED |
| 2 | re_20250317_002 | 2025-03-17 | MFGI, RVNC, HLTH, CSTM, ENXT | ARCHIVED |
| 1 | re_20250303_001 | 2025-03-03 | (VOL.1 종목) | ARCHIVED |

> 신규 발행 시 위 표에 행을 추가한다.
