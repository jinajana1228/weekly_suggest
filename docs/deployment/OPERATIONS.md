# Weekly Suggest — 운영 런북 (Operations Runbook)

## 외부 사용자가 보는 URL

| URL | 내용 |
|-----|------|
| `https://weekly-suggest.vercel.app/` | 최신 발행 에디션 (latest) |
| `https://weekly-suggest.vercel.app/archive` | 발행 이력 전체 |
| `https://weekly-suggest.vercel.app/archive/N` | VOL.N 에디션 상세 |
| `https://weekly-suggest.vercel.app/report/[id]` | 종목 상세 리포트 |
| `https://weekly-suggest.vercel.app/disclaimer` | 면책 고지 |

> Admin(`/admin`)은 외부에 공유하지 않는다. API 키 없으면 데이터 변경 불가.

---

## 배포 환경 기준 격주 발행 절차 (빠른 참조)

```bash
# 1. 로컬에서 스크리닝 실행
cd weekly_suggest
python scripts/create_edition.py
# → report_id, task_id 출력값 기록

# 2. (선택) Narrative 생성
python scripts/generate_narratives.py --report-id <report_id>

# 3. Admin 검토 — 로컬 admin UI 또는 직접 API 호출
#    모든 종목 APPROVED 확인

# 4. 발행 실행
python scripts/publish_edition.py --report-id <report_id> --task-id <task_id>
# → edition_latest.json 갱신 + state.db latest_pointer 설정

# 5. Git 커밋 + Push
git add data/mock/reports/
git commit -m "publish: VOL.N $(date +%Y-%m-%d) 정기 발행"
git push origin main
# → Railway 자동 재배포 → 외부 사용자에게 새 에디션 표시

# 6. 확인
curl -s https://weekly-suggest-api.railway.app/api/v1/reports/latest | head -c 200
```

---

## 기본 운영 정책

| 항목 | 내용 |
|------|------|
| 정기 발행 주기 | 격주 월요일 오전 8시 |
| 추가 발행 조건 | 주요 어닝 시즌 / 시장 이벤트 발생 |
| 최신 리포트 | 항상 latest published edition 표시 |
| 이전 리포트 | archive에 누적, 영구 보관 |
| 발행 게이트 | 스크리닝 → 검토 → Publish Guard 통과 필수 |
| 접속 시 재계산 | 없음 — 발행 완료된 결과만 제공 |

---

## 발행 흐름 전체 다이어그램

```
[격주 월요일 D-1 ~ D-0]

  ① 스크리닝 실행
     python scripts/create_edition.py
     → 후보 종목 필터링 + 점수 계산
     → review_task 생성 → SQLite 저장
     → data/mock/reports/ 에 JSON 파일 생성

  ② (선택) Narrative 자동 생성
     python scripts/generate_narratives.py --report-id <id>
     → Claude API 호출 → 4개 NarrativeBlock 생성
     → JSON 파일에 반영

  ③ Admin 검토
     http://localhost:PORT/admin (또는 배포 URL, 내부 접근)
     → 종목별 PENDING → APPROVED / FLAGGED / REJECTED
     → 5개 전원 APPROVED 확인

  ④ 발행 실행
     python scripts/publish_edition.py \
       --report-id <id> --task-id <task_id>
     → Publish Guard 5개 조건 검사
     → state.db: edition status → PUBLISHED
     → state.db: latest_pointer → 새 edition

  ⑤ 외부 사용자 접근
     https://weekly-suggest.vercel.app/
     → GET /api/v1/reports/latest
     → latest_pointer → JSON 파일 → 화면 표시

  ⑥ 이전 에디션 아카이브
     자동: latest_pointer 갱신 시 이전 edition → ARCHIVED
     아카이브 확인: https://weekly-suggest.vercel.app/archive
```

---

## 시나리오 1 — 격주 정기 발행

**타이밍**: 격주 일요일 오후 작업 → 월요일 오전 8시 발행

### Step 1: 스크리닝 실행 (일요일 오후)

```bash
cd weekly_suggest

# 기본 실행 (격주 정기)
python scripts/create_edition.py

# 확인 후 이상 없으면 진행 (dry-run 으로 먼저 확인)
python scripts/create_edition.py --dry-run
python scripts/create_edition.py --issue-type REGULAR_BIWEEKLY
```

출력 예:
```
[1/4] 스크리닝 실행 중...
      후보 14개 -> 선정 5개
        MFGI   score=94.1  discount=28.4%  risk=LOW
        ...
[4/4] Edition VOL.3 생성 완료
      report_id : re_20260317_003
      task_id   : task_20260315_002
다음 단계: python scripts/publish_edition.py --report-id re_20260317_003 --task-id task_20260315_002
```

### Step 2: Narrative 생성 (선택, 일요일 오후)

```bash
python scripts/generate_narratives.py --report-id re_20260317_003

# 이미 생성된 항목 재생성 시
python scripts/generate_narratives.py --report-id re_20260317_003 --overwrite
```

### Step 3: Admin 검토 (일요일 저녁)

1. `/admin` 접속 (또는 curl로 API 직접 호출)
2. 종목별 수치/서술 확인
3. 각 종목 → APPROVED (또는 FLAGGED)
4. 전원 APPROVED 확인

### Step 4: 발행 (월요일 오전 8시 직전)

```bash
python scripts/publish_edition.py \
  --report-id re_20260317_003 \
  --task-id task_20260315_002

# dry-run 으로 게이트 조건 먼저 확인
python scripts/publish_edition.py \
  --report-id re_20260317_003 \
  --task-id task_20260315_002 \
  --dry-run
```

Publish Guard 통과 조건:
- 종목 수 >= 5
- 모든 종목 APPROVED
- 종목당 data_quality_flag_count <= 3
- 해당 에디션 미발행 상태
- (선택) narrative 생성 완료

### Step 5: 발행 확인

```bash
# API 응답 확인
curl https://weekly-suggest-api.railway.app/api/v1/reports/latest | head -c 200

# 또는 브라우저에서 메인 페이지 접속
# https://weekly-suggest.vercel.app/
```

---

## 시나리오 2 — 어닝/이벤트 임시 발행

어닝 서프라이즈, 급락, 섹터 이벤트 발생 시 정기 발행 외 임시 발행.

### Step 1: 임시 에디션 생성

```bash
python scripts/create_edition.py \
  --issue-type EARNINGS_TRIGGERED \
  --top-n 3      # 임시 발행은 3개 종목도 가능
```

`--top-n 3`이면 Publish Guard의 `MIN_PUBLISH_STOCKS` 조건을 조정해야 한다:

```bash
python scripts/publish_edition.py \
  --report-id <id> \
  --task-id <task_id> \
  --min-stocks 3
```

또는 `.env`에서 `MIN_PUBLISH_STOCKS=3`으로 일시 변경 후 복구.

### Step 2-4

정기 발행과 동일 (검토 → 발행 → 확인).

**발행 후 admin에서 이전 에디션이 자동 ARCHIVED됨** — archive 페이지에서 확인.

---

## latest 교체 메커니즘

```
발행 전:
  latest_pointer → re_20250317_002 (VOL.2)
  edition: re_20250317_002 → PUBLISHED
  edition: re_20250303_001 → ARCHIVED

publish_edition.py 실행 후:
  latest_pointer → re_20260317_003 (VOL.3)  ← 교체
  edition: re_20260317_003 → PUBLISHED       ← 신규
  edition: re_20250317_002 → ARCHIVED        ← 자동 아카이브
  edition: re_20250303_001 → ARCHIVED        ← 유지

사용자 접속:
  GET /api/v1/reports/latest
  → state_store.get_latest_pointer() → re_20260317_003
  → file_store.get_edition_by_id(re_20260317_003)
  → data/mock/reports/edition_latest.json (또는 re003.json)
  → 화면 표시
```

---

## 배포 환경에서 발행 실행

배포된 Railway 서버에서 스크립트 실행:

```bash
# Railway CLI로 원격 쉘 접속
railway run bash

# 또는 로컬에서 Railway 환경변수 로드 후 실행
railway run python scripts/create_edition.py
railway run python scripts/publish_edition.py --report-id <id> --task-id <task_id>
```

또는 Railway의 Cron Job 기능 활용:
```yaml
# railway.toml
[[cron]]
command = "python scripts/create_edition.py --dry-run"
schedule = "0 6 * * 1"   # 격주 월요일 오전 6시 (스크리닝 준비)
```

---

## 공개 URL 구조

| URL | 설명 | 접근 주체 |
|-----|------|---------|
| `/` | 최신 발행 에디션 (latest published) | 외부 공개 |
| `/archive` | 발행 이력 전체 목록 | 외부 공개 |
| `/archive/[n]` | 특정 에디션 상세 (VOL.n) | 외부 공개 |
| `/report/[id]` | 종목 상세 리포트 | 외부 공개 |
| `/disclaimer` | 면책 고지 | 외부 공개 |
| `/admin` | 검토 관리 UI | **내부 접근 전용** |
| `/api/v1/admin/*` | Admin API | **X-Admin-Key 필요** |
| `/api/v1/reports/*` | 리포트 API | 외부 공개 (읽기 전용) |

### Admin 내부 접근 방법

배포 후 Admin 페이지는 URL 자체는 공개되지만 API 키 없이는 데이터 변경 불가.
추가 보호가 필요하면:
1. Vercel에서 Admin 경로에 Password Protection 설정 (Vercel Pro)
2. 또는 Admin을 별도 내부 URL로 운영 (추후 구현)

---

## 모니터링

| 체크 항목 | URL / 명령 | 주기 |
|---------|-----------|------|
| 백엔드 헬스 | `GET /health` | 격주 발행일 |
| 최신 리포트 응답 | `GET /api/v1/reports/latest` | 발행 직후 |
| 아카이브 목록 | `GET /api/v1/archive` | 발행 직후 |
| 5개 종목 차트 | `GET /api/v1/chart/{ticker}` | 격주 발행일 |

---

## 이전 에디션 수동 아카이브

특정 에디션을 수동으로 ARCHIVED 처리하려면:

```python
from backend.app.storage.state_store import state_store
state_store.update_edition_status("re_20250317_002", "ARCHIVED")
```

또는 다음 에디션 발행 시 자동 처리됨.
