# Weekly Suggest — 격주 발행 자동화 구조

> **최종 업데이트**: 2026-03-17
> **구조 원칙**: 운영자 검토/승인 후 발행 (완전 무인 발행 아님)
> **자동화 범위**: D-1 준비 단계까지 (screen + narrate + preflight)
> **발행 확정**: 운영자가 review → prepare → commit 을 수동 실행

---

## 1. 격주 발행 자동화 목표 구조

```
[D-1, 일요일 00:00 KST]
  GitHub Actions 자동 트리거
  └── scripts/biweekly_prep.py
        1. screen   -- 실데이터/mock 스크리닝 → data/staging/ 생성
        2. narrate  -- rule-based narrative 자동 초안
        3. preflight (기본 모드) -- 품질 점검 리포트
        └── staging 파일 → prep/biweekly-YYYYMMDD 브랜치 push
              └── Actions summary 에 운영자 체크리스트 표시

[D-0, 월요일]
  운영자 수동 실행
  1. git checkout prep/biweekly-YYYYMMDD
  2. review --show          → staging 내용 확인
  3. review --approve-all   → narrative 승인
  4. preflight --strict     → APPROVED 상태 게이팅
  5. prepare                → 발행 파일 생성
  6. commit                 → git push → Railway 재배포
  7. verify                 → smoke test
```

---

## 2. 단계별 자동/수동 구분

| 단계 | 자동 | 근거 |
|------|------|------|
| `screen` | ✅ 자동 | 결정론적 API 호출, mock fallback 보장 |
| `narrate` | ✅ 자동 | rule-based, LLM 없음, 재현 가능 |
| `preflight` (기본) | ✅ 자동 | 읽기 전용 검사, 차단하지 않음 |
| `review --show` | ✅ 자동 | 읽기 전용 상태 표시 |
| **`review --approve-all`** | ❌ 수동 | **내용 검토 없는 자동 승인 불가** |
| **`preflight --strict`** | ❌ 수동 | approve 완료 후 운영자가 게이팅 확인 |
| **`prepare`** | ❌ 수동 | 파일 생성 -- 되돌리기 어려움 |
| **`commit`** | ❌ 수동 | git push = 프로덕션 즉시 반영, 비가역 |
| `verify` | ✅ (commit 후) | 배포 완료 후 자동 확인 가능 |

> **핵심 원칙**: `prepare` 와 `commit` 은 반드시 운영자가 직접 실행.
> 자동화 시스템이 프로덕션에 push 하지 않는다.

---

## 3. 운영안 비교: A안 vs B안

### A안 (권장) — D-1 자동 준비 + D-0 운영자 승인

```
D-1 일요일:  [Auto] screen + narrate + preflight → staging 준비
D-0 월요일:  [수동] review + prepare + commit + verify
```

| 항목 | 평가 |
|------|------|
| 검토 시간 | 운영자에게 최대 24시간 여유 |
| 실패 복구 | D-0 전날 실패 발견 → 재시도 여유 |
| API 비용 | D-1 시점 데이터 사용 (D-0 기준 1일 전) |
| 운영 복잡도 | 2단계 (자동 준비 + 수동 발행) |
| 리스크 | 낮음 -- 운영자 검토 항상 보장 |

### B안 — 발행 당일 full pipeline + 운영자 최종 승인

```
D-0 월요일 08:00:  [Auto] screen + narrate + prepare (자동)
D-0 월요일:        [수동] 운영자 검토 → 승인 버튼 → commit
```

| 항목 | 평가 |
|------|------|
| 데이터 신선도 | 발행 당일 최신 데이터 |
| 실패 복구 | 당일 실패 시 시간 압박 |
| 운영 복잡도 | 1단계처럼 보이지만 당일 리스크 집중 |
| 리스크 | 중간 -- 발행일 당일 장애 시 발행 지연 |

**권장: A안**

발행형 리포트 서비스는 내용 신뢰성이 핵심이다.
운영자가 하루 전부터 검토할 수 있는 A안이 현재 구조에 더 적합하다.
완전 무인 발행은 데이터 품질 자동 검증 체계가 성숙한 이후에 검토한다.

---

## 4. 스케줄러 방식 비교

| 방식 | 장점 | 단점 | 판정 |
|------|------|------|------|
| **GitHub Actions** | git 통합, Secrets 관리, 무료, workflow_dispatch | runner 콜드 스타트 2~3분 | **권장** |
| Railway Cron | 인프라 통합 | git push 권한 설정 복잡, 순환 재배포 위험 | 보조 |
| 외부 스케줄러 (Cron-job.org) | 간단한 HTTP 호출 | pipeline 전체를 API로 구현 필요 | 부적합 |
| 로컬 Task Scheduler | 직접 제어 | 운영자 PC 항상 켜져 있어야 함 | 개발 전용 |

### GitHub Actions 설정 위치

```
.github/workflows/biweekly_prepare.yml
```

- **스케줄**: 매주 일요일 UTC 15:00 (KST 월요일 00:00)
- **격주 필터**: 짝수 ISO 주만 실행 (홀수 주는 skip summary 출력)
- **수동 실행**: `workflow_dispatch` → Actions 탭 → "Run workflow"
- **Secrets**: `FMP_API_KEY` → GitHub repo → Settings → Secrets and variables → Actions

> **중요**: GitHub Actions 는 GitHub 클라우드 서버에서 실행된다.
> 운영자 PC 전원이 꺼져 있어도 격주 준비가 자동으로 실행된다.
> PC 종료 상태와 무관하게 D-1 준비 단계는 항상 보장된다.

### 스케줄 변경 위치

발행 요일/시각을 바꾸려면 `biweekly_prepare.yml` 상단의 cron 표현식을 수정한다:

```yaml
# .github/workflows/biweekly_prepare.yml
on:
  schedule:
    - cron: '0 15 * * 0'   # ← 이 줄 수정
    #         분 시 일 월 요일(0=일요일)
    # 예) 토요일 UTC 15:00 으로 변경: '0 15 * * 6'
```

cron 표현식 참고: [crontab.guru](https://crontab.guru)

### 발행 주 기준 설정 방법

기본값은 짝수 ISO 주 (2, 4, 6, …주). 홀수 주로 바꾸려면:

```yaml
# biweekly_prepare.yml 의 week_check step 수정
elif (( 10#$WEEK % 2 == 1 )); then   # 1 로 변경
```

또는 `force_run: true` 로 workflow_dispatch 수동 실행.

---

## 5. 실패 처리 기준

| 실패 단계 | 처리 | 운영자 대응 |
|-----------|------|-------------|
| `screen` 실패 | 파이프라인 중단 (exit 1) | API 키 확인, mock fallback 으로 재실행 |
| `narrate` 실패 | 경고만, 계속 진행 | preflight WARN 확인 후 수동 narrate |
| `preflight` ERROR | 경고만 (D-1 기본 모드) | 운영자가 strict 실행 전 항목 수정 |
| `preflight --strict` ERROR | prepare 차단 | 해당 항목 수동 수정 후 재실행 |
| `prepare` 실패 | 파일 미생성, 중단 | 오류 메시지 확인, staging 파일 점검 |
| `commit` 실패 | push 안 됨 | git 상태 확인, 충돌 해결 후 재실행 |
| `verify` 실패 | 배포는 됐지만 API 이상 | Railway 로그 확인, rollback 고려 |

### rollback 절차

commit 후 이상 발견 시:

```cmd
REM 직전 commit 되돌리기 (push 전)
git reset HEAD~1

REM 이미 push 된 경우
REM 1. edition_latest.json 을 이전 archive 내용으로 복구
REM 2. git commit -m "revert: VOL.N 발행 롤백"
REM 3. git push
```

---

## 6. 알림 방식 (선택 옵션)

현재 구조에서 알림은 **GitHub Actions summary** 로 대체된다.

| 방식 | 구현 난이도 | 상태 |
|------|-------------|------|
| GitHub Actions summary | 없음 (자동) | ✅ 구현됨 |
| 이메일 (Gmail via SMTP) | 낮음 | 선택 사항 |
| Slack webhook | 낮음 | 선택 사항 |
| GitHub 이메일 알림 | 없음 (자동) | ✅ job 실패 시 자동 발송 |

### Slack 알림 추가 방법 (선택)

```yaml
# biweekly_prepare.yml 마지막 step 에 추가
- name: Notify Slack
  if: steps.week_check.outputs.skip != 'true'
  uses: rtCamp/action-slack-notify@v2
  env:
    SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
    SLACK_MESSAGE: "D-1 준비 완료: ${{ steps.prep.outcome }} -- review 후 발행 실행"
    SLACK_COLOR: ${{ steps.prep.outcome == 'success' && 'good' || 'warning' }}
```

---

## 7. 준비 스크립트

```
scripts/biweekly_prep.py
```

screen + narrate + preflight 를 한 번에 실행하는 통합 스크립트.
GitHub Actions 에서 호출하거나 로컬에서 직접 실행 가능.

```cmd
REM 기본 실행 (mock 모드)
python scripts\biweekly_prep.py

REM FMP 실데이터 모드
python scripts\biweekly_prep.py --provider fmp

REM dry-run (파일 변경 없이 검증만)
python scripts\biweekly_prep.py --dry-run

REM 기존 staging 재사용 (screen 건너뜀)
python scripts\biweekly_prep.py --skip-screen --context-note "3월 4주차 시황"
```

실행 결과는 `data/prep_report_YYYYMMDD_HHMMSS.json` 에 저장된다.

---

## 8. 운영자 최소 체크포인트

D-0 발행일에 운영자가 확인해야 하는 항목:

```
[ ] 1. GitHub Actions summary 확인 (D-1 준비 결과)
        → Actions 탭 → 최근 'Biweekly Publish Preparation' 실행

[ ] 2. staging 파일 내용 검토
        → python scripts\publish_release.py review --show
        → 각 종목의 narrative 내용이 적절한지 확인

[ ] 3. 필요 시 narrative 직접 수정
        → data/staging/stock_TICKER_draft.json 편집
        → 또는 Admin UI /admin → Staging 패널

[ ] 4. 전체 승인
        → python scripts\publish_release.py review --approve-all --reviewer 편집자명
        → 또는 Admin UI 에서 종목별 승인 버튼

[ ] 5. strict preflight 통과 확인
        → python scripts\publish_release.py preflight --strict
             --context-note "이번 에디션 시황 요약 문구"
        → ERROR 없을 때만 prepare 진행

[ ] 6. 발행 준비
        → python scripts\publish_release.py prepare
             --stocks-dir data\staging
             --context-note "시황 요약 문구"
        → 생성된 edition_latest.json 내용 최종 확인

[ ] 7. 발행 확정 (git push)
        → python scripts\publish_release.py commit
        → Railway 재배포 3~5분 대기

[ ] 8. 배포 검증
        → python scripts\publish_release.py verify
        → 모든 체크 통과 확인
```

---

## 9. 완전 자동화 로드맵 (미래)

현재는 `prepare` + `commit` 을 수동으로 유지한다.
아래 조건이 충족되면 단계적으로 자동화 범위를 확장할 수 있다:

| 조건 | 확장 가능 단계 |
|------|----------------|
| narrative 품질 자동 평가 기준 확립 | `review --approve-all` 자동화 |
| FMP 데이터 품질 모니터링 구축 | `preflight --strict` 자동화 |
| staging → reports 파일 검증 자동화 완성 | `prepare` 자동화 |
| GitHub Actions PAT + 보호 브랜치 규칙 설정 | `commit` 자동화 |
| 위 모두 완성 | **완전 무인 발행** |
