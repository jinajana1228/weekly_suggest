# Weekly Suggest — 운영 위키

> Notion에 붙여넣기 쉽도록 구성된 운영 위키입니다.
> 각 `##` 섹션이 Notion 페이지 1개에 대응합니다.
> ⚠️ 실제 API 키·비밀번호는 이 문서에 절대 기입하지 마세요.

---

## 서비스 개요

**Weekly Suggest**는 미국 상장 중대형주 중 구조적으로 저평가된 종목을 자동 선별하고, 애널리스트 수준의 분석 리포트를 **격주(2주에 1회)** 발행하는 웹서비스입니다.

### 이 서비스는 어떻게 동작하나요?

일반적인 웹서비스와 다르게, Weekly Suggest는 **발행형(publish-based)** 구조입니다.

- 사용자가 접속해도 그 순간 분석을 새로 실행하지 않습니다.
- 운영자가 미리 준비·검토·승인한 리포트만 화면에 보여줍니다.
- 새 에디션을 발행하면 메인 페이지가 바뀝니다. 그 전까지는 이전 에디션이 유지됩니다.
- 이전 에디션은 삭제되지 않고 `/archive` 에서 항상 볼 수 있습니다.

### 핵심 원칙 한 줄 요약

| 원칙 | 내용 |
|------|------|
| 발행형 서비스 | 접속할 때마다 재계산하지 않음 |
| latest = 항상 최신 1개 | 메인은 가장 최근 발행본 1개만 표시 |
| archive 영구 보관 | 이전 발행본은 /archive 에서 계속 접근 가능 |
| 승인형 발행 | 자동으로 발행되지 않음 — 운영자가 검토 후 직접 확정 |
| 목표주가 없음 | 제시하는 관심 구간은 참고치이며 목표가 아님 |

### 서비스 URL (현재 운영 중)

| 역할 | URL |
|------|-----|
| 메인 (최신 에디션) | https://weekly-suggest.vercel.app |
| 발행 이력 전체 | https://weekly-suggest.vercel.app/archive |
| 운영자 Admin | https://weekly-suggest.vercel.app/admin |
| Backend API 상태 | https://weeklysuggest-production.up.railway.app/health |

---

## 운영 프로세스 한눈에 보기

> 기술적인 용어를 최소화하고, "무슨 일이 언제 일어나는가"를 중심으로 설명합니다.

### 이 서비스의 한 발행 주기 (2주마다 반복)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 1   일요일 자정 — 시스템이 알아서 준비
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  GitHub 서버(클라우드)에서 자동으로 실행됩니다.
  내 컴퓨터가 꺼져 있어도, 자고 있어도 상관없습니다.

  ① 미국 상장 주식 데이터를 수집합니다
  ② 정해진 기준(시총, 수익성, 저평가도 등)으로 후보를 걸러냅니다
  ③ 상위 5개 종목을 선정하고 분석 초안 텍스트를 자동 생성합니다
  ④ 결과물을 GitHub(코드 저장소)의 임시 공간에 저장합니다
  ⑤ 운영자에게 "준비 완료" 결과 요약을 보여줍니다

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 2   월요일 오전 — 운영자가 내용 검토
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  자동으로 만들어진 내용을 사람이 직접 확인합니다.
  이 단계 없이는 발행이 되지 않습니다. (의도된 안전장치)

  ① GitHub에서 준비 결과 확인
      → 어떤 5개 종목이 선정됐는지 확인
      → 각 종목의 분석 텍스트가 적절한지 읽어봄
  ② 내용 수정이 필요하면 직접 편집
      → 분석 텍스트(narrative)를 수정하거나 보완
  ③ 내용이 좋으면 "승인" 처리
      → 모든 항목에 APPROVED 도장을 찍는 것

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 3   월요일 오전 — 발행 확정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  승인이 완료된 내용을 실제로 발행합니다.

  ① 발행 전 자동 검증 (누락 항목 없는지, 오류 없는지 확인)
  ② 발행 파일 생성 (최신 에디션 파일이 새로 만들어짐)
  ③ GitHub에 올리기 (= 발행 확정, 되돌리기 어려움)
  ④ 서버가 자동으로 3~5분 안에 재시작됨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STEP 4   발행 직후 — 사용자가 새 에디션을 봄
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ① 서버 재시작 완료 (3~5분 소요)
  ② https://weekly-suggest.vercel.app 접속 시
     새로운 VOL.N 에디션이 메인 페이지에 표시됨
  ③ 이전 에디션은 /archive 에서 계속 볼 수 있음

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 2주 후 → STEP 1 부터 다시 반복
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 서비스를 구성하는 3가지 부품

| 부품 | 역할 | 비유 |
|------|------|------|
| **GitHub** | 모든 코드와 데이터를 보관하는 창고 | 원고 보관 서랍 |
| **Railway** | 데이터를 요청하면 꺼내주는 서버 | 창고 관리인 |
| **Vercel** | 사용자가 보는 웹페이지 | 전시관 |

코드나 데이터가 GitHub에 저장되면 → Railway와 Vercel이 자동으로 새 내용을 반영합니다.

### 사용자가 페이지를 열면 실제로 무슨 일이?

```
사용자가 weekly-suggest.vercel.app 접속

  ↓ Vercel이 서버에 요청

  ↓ Railway 서버가 "최신 파일"을 꺼내줌
    (edition_latest.json 이라는 파일 1개)

  ↓ 그 파일 내용을 화면에 예쁘게 그려줌

  → 사용자 화면에 최신 에디션 표시됨
```

새로 스크리닝하거나 계산하는 일은 없습니다. 미리 만들어둔 파일을 그대로 보여주는 구조입니다.

---

## 현재 상태

**최종 업데이트: 2026-03-18**

### 발행 이력

| 번호 | 발행일 | 종목 | 상태 |
|------|--------|------|------|
| **VOL.3** (최신) | 2026-03-17 | NXPW(성장), BLFN(성장), STRL(저평가), VCNX(성장), DFTL(저평가) | 🟢 PUBLISHED |
| VOL.2 | 2025-03-17 | MFGI, RVNC, HLTH, CSTM, ENXT | 🔵 ARCHIVED |
| VOL.1 | 2025-03-03 | DXPC, LGSV, MRVX, WTRX, BXMT | 🔵 ARCHIVED |

### 현재 설정 상태

| 항목 | 상태 |
|------|------|
| 데이터 모드 | `mock` (JSON 파일 기반, 실데이터 미연동) |
| 차트 데이터 | VOL.2 + VOL.3 전체 10개 파일 ✅ 정상 |
| Narrative 생성 | rule-based 자동 초안 (Claude API 미연동) |
| GitHub Actions | 활성화 (격주 일요일 자정 자동 실행) |
| 추천 로직 | 2버킷 구조 (성장·수혜 3개 + 저평가 2개) |

### 종목 선정 유형 안내

| 유형 | 배지 색상 | 의미 |
|------|-----------|------|
| **성장·수혜** | 파란색 | 성장률·모멘텀·정책 수혜 기준 상위 3개 |
| **저평가** | 황금색 | 섹터 대비 할인율 ≥ 10% + 촉매 ≥ 1개 충족 후 가치 기준 상위 2개 |

두 유형 모두 목표주가 없음. 관심 구간은 섹터 중앙값 기반 조건부 참고치.

### 진행 중인 개선 과제

| 과제 | 우선순위 |
|------|---------|
| 상세 페이지 섹션 읽기 순서 개선 (스토리 흐름 재배치) | 높음 |
| selection_type 배지 툴팁/설명 추가 | 중간 |
| Admin 대시보드 완료 Task 분리 (COMPLETED 이력 접이식) | 중간 |
| Admin UI에서 narrative 텍스트 직접 수정 기능 | 중간 |
| 실데이터(FMP API) 연동 안정화 | 낮음 |
| 장기적으로 완전 자동 발행 고도화 | 낮음 |

---

## 전체 아키텍처

### 서비스 구성 한눈에 보기

```
사용자 브라우저
    ↓ 접속
Vercel — https://weekly-suggest.vercel.app
  프론트엔드 (Next.js 14)
  5분마다 최신 데이터 갱신
    ↓ API 요청
Railway — https://weeklysuggest-production.up.railway.app
  백엔드 (Python FastAPI)
  JSON 파일 데이터 서빙
    ↑ git push 시 자동 재배포
GitHub — https://github.com/jinajana1228/weekly_suggest
  코드 + 데이터 저장소
    ↑
GitHub Actions (자동화)
  격주 일요일 자정에 자동 준비 실행
  ※ 내 컴퓨터가 꺼져 있어도 GitHub 클라우드에서 실행됨
```

### 발행이 이루어지는 과정

```
① 일요일 자정 — GitHub Actions 자동 실행
   → 종목 스크리닝 + narrative 초안 생성
   → 결과를 GitHub prep 브랜치에 저장

② 월요일 — 운영자 수동 확인 및 발행
   → 준비된 내용 검토
   → 내용 승인
   → 최종 발행 명령 실행
   → git push → Railway 재배포 (3~5분)
   → 메인 페이지에 새 에디션 노출
```

### 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | Next.js 14, TypeScript, Tailwind CSS |
| 차트 | Recharts |
| 백엔드 | Python 3.11, FastAPI |
| 데이터 저장 | JSON 파일 (리포트) + SQLite (발행 상태) |
| AI (선택) | Anthropic Claude API (narrative 생성 시) |
| 데이터 소스 | FMP API, yfinance (실데이터 전환 시) |

---

## 계정 및 서비스 연결 정보

> ⚠️ 이 섹션에 실제 비밀번호/API 키를 직접 입력하지 마세요.
> 값은 비밀번호 관리자에 보관하고, 이 문서에는 보관 위치만 적으세요.
> Notion 페이지 공유 시 이 섹션은 접근 권한을 제한하세요.

### GitHub

| 항목 | 값 |
|------|-----|
| Repository URL | https://github.com/jinajana1228/weekly_suggest |
| 계정 (이메일) | [직접 입력 필요] |
| 기본 브랜치 | main |
| Actions Secret: FMP_API_KEY | [비밀번호 관리자에 보관] |

### Railway (백엔드)

| 항목 | 값 |
|------|-----|
| Backend URL | https://weeklysuggest-production.up.railway.app |
| 계정 (이메일) | [직접 입력 필요] |
| APP_ENV | production |
| DATA_PROVIDER_MODE | mock |
| CORS_ORIGINS | https://weekly-suggest.vercel.app |
| ADMIN_API_KEY | [비밀번호 관리자에 보관] |
| FMP_API_KEY | [미설정 — 실데이터 전환 시 필요] |
| ANTHROPIC_API_KEY | [미설정 — narrative Claude 생성 시 필요] |
| Volume(/data) 설정 | [ ] 설정됨 / [x] 미설정 |

### Vercel (프론트엔드)

| 항목 | 값 |
|------|-----|
| Frontend URL | https://weekly-suggest.vercel.app |
| 계정 (이메일) | [직접 입력 필요] |
| Root Directory | frontend |
| BACKEND_URL | https://weeklysuggest-production.up.railway.app |
| NEXT_PUBLIC_API_URL | https://weeklysuggest-production.up.railway.app/api/v1 |

### API 키 발급처 (필요 시)

| 키 | 발급 방법 |
|----|---------|
| FMP_API_KEY | financialmodelingprep.com → 가입 → API 키 |
| ANTHROPIC_API_KEY | console.anthropic.com → API Keys |
| ADMIN_API_KEY | 코드 저장소에서 `python scripts/generate_admin_key.py` 실행 |

---

## 발행 운영 절차

### 이 서비스의 발행 구조는?

> 완전 자동 발행이 **아닙니다**.
> "일요일에 자동으로 준비 → 월요일에 운영자가 검토 후 직접 발행"하는 구조입니다.
> 운영자가 내용을 확인하고 승인한 후에만 실제 발행이 이루어집니다.

---

### 시나리오 A — 정규 격주 발행 (가장 일반적)

#### 일요일 자정 (자동, 아무것도 안 해도 됨)

GitHub Actions가 자동으로 아래 작업을 실행합니다:
- 종목 스크리닝
- narrative 초안 자동 생성
- 품질 사전 점검
- 결과를 `prep/biweekly-YYYYMMDD` 브랜치에 저장

**내 컴퓨터가 꺼져 있어도 됩니다.** GitHub 클라우드에서 실행됩니다.

실행 결과 확인 방법:
```
https://github.com/jinajana1228/weekly_suggest
→ Actions 탭 → 'Biweekly Publish Preparation (D-1)' 최근 실행
→ Summary 탭에서 준비 결과 + 운영자 체크리스트 확인
```

---

#### 월요일 오전 (운영자 수동 실행)

**① GitHub Actions 결과 먼저 확인**

```
https://github.com/jinajana1228/weekly_suggest/actions
→ 최근 실행 → Summary 탭
```

준비 성공이면 다음 단계로 진행. 실패면 원인 확인 후 재시도.

**② 준비된 내용 가져오기**

```cmd
git pull
git checkout prep/biweekly-YYYYMMDD
```

**③ 준비된 종목 내용 확인**

```cmd
python scripts\publish_release.py review --show
```

각 종목의 narrative(분석 서술) 내용이 적절한지 확인합니다.
수정이 필요하면 `data/staging/stock_{TICKER}_draft.json` 파일을 직접 편집하거나
Admin UI(`/admin`)의 Staging 패널에서 수정합니다.

**④ 내용 승인**

검토 후 문제없으면:
```cmd
python scripts\publish_release.py review --approve-all --reviewer "이름"
```

**⑤ 발행 전 최종 점검**

`--context-note` 에 이번 에디션 시황 요약 문구를 입력합니다:
```cmd
python scripts\publish_release.py preflight --strict --context-note "3월 4주차, 금리 인하 기대감 속 가치주 재부각"
```

ERROR가 있으면 해결 후 재실행. WARN만 있으면 계속 진행 가능.

**⑥ 발행 파일 생성**

```cmd
python scripts\publish_release.py prepare --stocks-dir data\staging --context-note "3월 4주차, 금리 인하 기대감 속 가치주 재부각"
```

생성된 `data/mock/reports/edition_latest.json` 내용을 최종 확인합니다.

**⑦ 발행 확정 (git push = 프로덕션 즉시 반영)**

```cmd
python scripts\publish_release.py commit
```

`y` 입력 → git push → Railway 재배포 시작 (3~5분 대기)

**⑧ 배포 확인**

Railway 재배포 완료 후:
```cmd
python scripts\publish_release.py verify
```

모든 체크 통과 시 발행 완료. 브라우저에서 https://weekly-suggest.vercel.app 접속해 확인.

---

### 시나리오 B — 임시 발행 (긴급, 실적 발표 등)

정규 스케줄 외 발행이 필요할 때:

```cmd
python scripts\publish_release.py screen --provider mock
python scripts\publish_release.py narrate
python scripts\publish_release.py review --approve-all --reviewer "이름"
python scripts\publish_release.py preflight --strict --context-note "긴급 발행 사유"
python scripts\publish_release.py prepare --stocks-dir data\staging --context-note "긴급 발행 사유" --issue-type EARNINGS_TRIGGERED
python scripts\publish_release.py commit
python scripts\publish_release.py verify
```

---

### 발행 전 반드시 확인할 항목

| 체크 | 확인 방법 |
|------|---------|
| D-1 준비 성공 여부 | GitHub Actions Summary |
| staging 종목 내용이 적절한가 | `review --show` 또는 Admin UI |
| narrative가 모두 APPROVED인가 | `review --show` 결과 확인 |
| preflight --strict ERROR 없는가 | `preflight --strict` 출력 확인 |
| context-note(시황 요약)가 작성됐는가 | preflight/prepare 실행 시 입력 |

---

### 시나리오 C — 이슈 발생 시

**상황: latest가 이전 에디션을 보여줌**
1. `git log --oneline -3` → 최근 커밋 확인
2. Railway 대시보드 → Deployments → 재배포 완료 여부 확인
3. `https://weeklysuggest-production.up.railway.app/health` 에서 응답 확인

**상황: 차트가 안 보임**
1. `data/mock/chart/{TICKER}_price_series.json` 파일 존재 여부 확인
2. 없으면 `scripts/_gen_chart_data.py` 참고해서 생성

**상황: Admin 접근 안 됨 (403)**
1. Railway Variables → `ADMIN_API_KEY` 설정 여부 확인
2. Admin UI 접속 시 키 재입력

**상황: 발행 후 문제 발견 → rollback**
```cmd
REM push 전이라면:
git reset HEAD~1

REM 이미 push 된 경우:
REM 1. edition_latest.json 을 이전 archive 내용으로 복구
REM 2. git commit -m "revert: VOL.N 발행 롤백"
REM 3. git push
```

---

## 자동화 현황

### GitHub Actions — D-1 자동 준비

| 항목 | 내용 |
|------|------|
| 실행 시각 | 매주 일요일 UTC 15:00 (= KST 월요일 00:00) |
| 실행 주기 | 격주 (짝수 ISO 주만 실행) |
| 실행 위치 | **GitHub 클라우드** — 내 컴퓨터 꺼져 있어도 됨 |
| 수동 실행 | GitHub → Actions → "Run workflow" 버튼 |
| 결과 확인 | GitHub → Actions → Summary 탭 |
| 파일 위치 | `.github/workflows/biweekly_prepare.yml` |

### 자동으로 되는 것 vs 수동으로 해야 하는 것

| 작업 | 자동/수동 | 이유 |
|------|---------|------|
| 종목 스크리닝 | ✅ 자동 | 로직이 결정론적 |
| narrative 초안 생성 | ✅ 자동 | rule-based, 재현 가능 |
| 품질 사전 점검 (기본) | ✅ 자동 | 읽기 전용 |
| **내용 검토·승인** | ❌ 수동 | 내용 확인 없는 자동 승인 불가 |
| **strict 점검** | ❌ 수동 | 승인 완료 후 운영자 직접 확인 |
| **발행 파일 생성** | ❌ 수동 | 되돌리기 어려운 작업 |
| **git push (발행 확정)** | ❌ 수동 | **즉시 프로덕션 반영** |

### 스케줄 변경이 필요하다면

`.github/workflows/biweekly_prepare.yml` 파일 9번째 줄:
```yaml
- cron: '0 15 * * 0'   # 0=일요일
```
숫자 의미: `분 시 일 월 요일(0=일요일, 6=토요일)`

격주 기준(짝수/홀수)을 바꾸려면 같은 파일의 `week_check` step 수정.

---

## 이슈 로그

| 날짜 | 이슈 | 심각도 | 상태 |
|------|------|--------|------|
| 2026-03-17 | VOL.3 신규 5종목 차트 데이터 없음 | 중간 | ✅ 해결 |
| 2026-03-17 | GitHub Actions workflow 파일 작성 오류 | 낮음 | ✅ 해결 |
| 2026-03-17 | biweekly_prep.py SyntaxWarning | 낮음 | ✅ 해결 |

> 상세 원인·해결 내용: 코드 저장소 `docs/INCIDENTS.md` 참조

---

## 향후 개선 과제

### 단기 (다음 발행 이전)

- [ ] **Admin UI narrative 직접 편집**
  - 현재: JSON 파일을 텍스트 에디터로 직접 편집해야 함
  - 목표: `/admin` 페이지에서 텍스트박스로 수정 + 저장 가능
  - 이유: 비개발자도 운영 가능하게

### 중기

- [ ] **실데이터 provider 검증**
  - FMP API 키 발급 후 전체 스크리닝 파이프라인 테스트
  - 현재 mock 모드에서 real 모드로 전환하기 위한 사전 검증
- [ ] **preflight에 차트 파일 존재 여부 체크 추가**
  - 신규 종목 추가 시 차트 누락 방지

### 장기

- [ ] **완전 무인 발행** (단계적으로)
  - narrative 품질 자동 평가 기준 확립 후 → review 자동화
  - 데이터 품질 모니터링 구축 후 → prepare/commit 자동화
- [ ] **Admin UI 로그인 폼**
  - 현재 URL 비공개 + Admin Key 방식에서 로그인 폼 추가

---

## Claude Code 사용 가이드

> 이 프로젝트에 수정·이슈가 생겼을 때, AI 코드 어시스턴트(Claude Code)에게 어떻게 요청하면 좋은지 정리합니다.
> Claude Code는 프로젝트 코드를 직접 읽고 수정할 수 있는 AI 도구입니다.

### Claude Code에게 요청하기 전에

매번 새 대화(세션)를 시작할 때 Claude Code는 이전 작업 내용을 기억하지 못합니다.
아래 문서들을 먼저 읽게 해주면 빠르게 맥락을 파악할 수 있습니다.

**필수 — 항상 이 순서로 읽게 해주세요:**

```
1. CLAUDE.md                          ← 프로젝트 전체 요약 (가장 중요)
2. docs/PROJECT_CONTEXT.md            ← 서비스 목적과 운영 구조
3. docs/deployment/OPERATIONS.md      ← 발행 절차 상세
```

**상황에 따라 추가로:**

```
배포/인프라 문제 시:  docs/INFRA_SETUP.md
이슈 해결 시:        docs/INCIDENTS.md
자동화 설정 시:      docs/deployment/AUTOMATION.md
```

---

### 요청 프롬프트 예시

아래 예시들을 복사해서 상황에 맞게 수정해 사용하세요.

---

#### 예시 1 — 기능 수정 요청

```
Weekly Suggest 프로젝트야.
먼저 CLAUDE.md, docs/PROJECT_CONTEXT.md, docs/deployment/OPERATIONS.md 를 읽어줘.

읽은 후, 아래 작업을 진행해줘:
[원하는 기능 설명]

예: Admin UI에서 narrative 텍스트를 직접 편집할 수 있는 텍스트박스를 추가해줘.
현재는 JSON 파일을 직접 수정해야 하는데, /admin 페이지에서 클릭 후 수정할 수 있게 해줘.
```

---

#### 예시 2 — 배포/인프라 이슈

```
Weekly Suggest 프로젝트야.
먼저 CLAUDE.md, docs/INFRA_SETUP.md 를 읽어줘.

현재 아래 문제가 발생했어:
[문제 상황 설명]

예: Railway 백엔드에 접속이 안 돼.
https://weeklysuggest-production.up.railway.app/health 응답이 없는 상태야.
Railway 대시보드 로그에서 아래 오류가 나와:
[오류 내용 붙여넣기]

원인이 뭔지 분석하고, 해결 방법 알려줘.
```

---

#### 예시 3 — 발행 운영 이슈

```
Weekly Suggest 프로젝트야.
먼저 CLAUDE.md, docs/deployment/OPERATIONS.md, docs/INCIDENTS.md 를 읽어줘.

발행 도중 아래 문제가 생겼어:
[문제 상황 설명]

예: preflight --strict 를 실행했는데 아래 ERROR가 나고 있어.
prepare 단계로 넘어가지 못하는 상태야.
[오류 메시지 붙여넣기]

어떻게 해결해야 할지 알려줘.
```

---

#### 예시 4 — 차트/데이터 누락 이슈

```
Weekly Suggest 프로젝트야.
먼저 CLAUDE.md, docs/PROJECT_CONTEXT.md 를 읽어줘.

현재 아래 종목 상세 페이지에서 차트가 안 보여:
[티커 목록, 예: ABCD, EFGH, IJKL]

차트 데이터 파일이 없는 건지, API 연결 문제인지 확인하고,
없으면 차트 데이터 파일을 생성해줘.
해당 종목의 stock_{TICKER}_NNN.json 파일에서 52주 고저점과 현재가를 참고해줘.
```

---

#### 예시 5 — 새 에디션 발행 준비 도움 요청

```
Weekly Suggest 프로젝트야.
먼저 CLAUDE.md, docs/deployment/OPERATIONS.md 를 읽어줘.

VOL.4 발행을 준비하려고 해.
현재 data/staging/ 에 아래 5개 종목 파일이 있어:
[파일 목록]

발행 전에 뭘 확인해야 하는지, 어떤 명령어를 순서대로 실행하면 되는지 안내해줘.
이번 에디션 시황 노트: "[시황 요약 문구]"
```

---

### 더 좋은 결과를 위한 팁

| 상황 | 팁 |
|------|-----|
| 오류가 났을 때 | 오류 메시지 전문을 그대로 붙여넣기 |
| 코드 수정 요청 | 어떤 파일의 어떤 기능인지 구체적으로 설명 |
| 배포 관련 | Railway 또는 Vercel 대시보드 로그도 함께 첨부 |
| 이전 대화 이어받기 | "지난번에 ~ 작업했던 걸 이어서 진행해줘" 라고 시작 |
| 큰 작업 전 | 먼저 "어떻게 할 건지 계획만 설명해줘"로 시작해 검토 후 진행 |

### 자주 쓰는 시작 문장

```
# 기본 (매 세션 시작 시)
"Weekly Suggest 프로젝트야. CLAUDE.md 먼저 읽고 시작해줘."

# 빠른 이슈 전달
"Weekly Suggest 프로젝트야. CLAUDE.md 읽고,
 [문제 요약] 을 해결해줘. 오류 내용: [붙여넣기]"

# 새 기능 개발
"Weekly Suggest 프로젝트야.
 CLAUDE.md + docs/PROJECT_CONTEXT.md 읽고,
 [기능 설명] 구현해줘."
```

---

## 참고 문서 (코드 저장소)

| 문서 | 경로 | 설명 |
|------|------|------|
| AI 컨텍스트 가이드 | `CLAUDE.md` | Claude Code 세션용 빠른 참조 |
| 프로젝트 종합 컨텍스트 | `docs/PROJECT_CONTEXT.md` | 서비스 목적·구조 전체 |
| 인프라 연결 구조 | `docs/INFRA_SETUP.md` | GitHub/Railway/Vercel 상세 설정 |
| 기술 아키텍처 | `docs/ARCHITECTURE.md` | 시스템 설계 상세 |
| 운영 절차서 | `docs/deployment/OPERATIONS.md` | 발행 SOP |
| 자동화 설계 | `docs/deployment/AUTOMATION.md` | D-1/D-0 자동화 |
| 배포 가이드 | `docs/deployment/DEPLOYMENT.md` | Railway/Vercel 배포 |
| 변경 이력 | `docs/CHANGELOG.md` | 코드·인프라 변경 이력 |
| 이슈 이력 | `docs/INCIDENTS.md` | 장애 발생 및 해결 내용 |
