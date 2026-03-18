# Weekly Suggest — 이슈 이력 (INCIDENTS)

> 발생한 문제, 원인, 해결 방법을 기록한다.
> 운영 중 장애나 이슈가 발생하면 이 파일에 추가한다.

---

## 템플릿

```markdown
## YYYY-MM-DD — 이슈 제목

**심각도**: 높음 / 중간 / 낮음
**영향 범위**: 사용자 노출 / 운영 기능 / 개발 환경
**상태**: 해결 완료 / 해결 중 / 모니터링

### 현상
어떤 문제가 발생했는지 설명.

### 원인
무엇이 원인이었는지 설명.

### 해결
어떻게 해결했는지 설명. 변경된 파일/설정 포함.

### 재발 방지
이후 같은 문제가 생기지 않도록 한 조치.
```

---

## 2026-03-18 — selection_type 전환 후 Vercel 배지 일시 미표시

**심각도**: 낮음
**영향 범위**: 사용자 노출 (메인 페이지 배지 일시적 미표시)
**상태**: 해결 완료 (자동 해소 — Vercel 재빌드 후)

### 현상

`GROWTH_BENEFICIARY` → `GROWTH_TRAJECTORY` 전환 커밋(`cabcad5`) 직후,
Vercel 메인 페이지에서 NXPW·BLFN·VCNX 카드의 배지(파란색)가 표시되지 않았다.
(HTML에 `"$undefined"` 렌더링)

### 원인

두 가지 타이밍 불일치 동시 발생:

1. **Railway 배포 완료**: API가 즉시 `GROWTH_TRAJECTORY` 반환 시작
2. **Vercel 빌드 진행 중**: 프론트엔드 코드는 아직 구 버전 (`GROWTH_BENEFICIARY` 키만 인식)
   → `SELECTION_TYPE_CONFIG["GROWTH_TRAJECTORY"]` = undefined → 배지 미렌더링

또한, Vercel SSR 5분 캐시로 인해 새 코드 빌드 완료 후에도 즉각 반영되지 않았다.

### 해결

Vercel 빌드 완료(약 2분) + SSR 캐시 만료(5분) 후 자동 해소.
추가 조치 불필요.

### 재발 방지

- `selection_type` enum 값 변경 시 반드시 3곳 동시 변경:
  1. `frontend/src/types/enums.ts`
  2. `frontend/src/components/report/StockCard.tsx` (SELECTION_TYPE_CONFIG 키)
  3. `frontend/src/app/archive/page.tsx` (조건 분기)
- 변경 후 Vercel 빌드 완료(약 2분) + 캐시 만료(5분) 후 재확인 필요
- `verify` 스크립트에 selection_type 카운트 체크 추가 고려

---

## 2026-03-18 — VOL.3 종목 상세 페이지 전체 404

**심각도**: 높음
**영향 범위**: 사용자 노출 (VOL.3 종목 상세 페이지 5개 전체 접근 불가)
**상태**: 해결 완료

### 현상

메인 페이지 종목 카드 클릭 시 `/report/ri_20260317_003_BLFN?report_id=re_20260317_003` 등
VOL.3 5개 종목 상세 페이지가 모두 404를 반환함.
백엔드 API(`/reports/{id}/stocks/{ticker}`)는 200 정상이었으나, 차트 API가 500을 반환.

### 원인

다단계 원인 연결:

1. VOL.3 차트 JSON(`BLFN_price_series.json` 등)의 `interest_range_band` 키가
   `{low, high, color}` 형태로 작성됨
2. `backend/app/api/v1/chart.py`의 `_transform_chart()`에서 `irb_raw["lower_bound"]`로
   직접 접근 → `KeyError` 발생 → HTTP 500
3. 프론트엔드 상세 페이지(`app/report/[report_item_id]/page.tsx`)가
   `Promise.all([getStockReport, getChartData])`에서 차트 API 500을 받으면
   `catch(e) { notFound() }` 로 분기 → Next.js 404 페이지 반환

### 해결

1. `_transform_chart()` 방어 코드 적용 (`2026-03-18`, 커밋 `e240a16`)
   ```python
   lower = irb_raw.get("lower_bound", irb_raw.get("low"))
   upper = irb_raw.get("upper_bound", irb_raw.get("high"))
   ```
2. VOL.3 차트 JSON 5개 `interest_range_band` 스키마 표준화
   - `{low, high, color}` → `{lower_bound, upper_bound, label, color_hint}`

### 재발 방지

- 새 에디션 차트 JSON 작성 시 `interest_range_band`는 반드시 `lower_bound`/`upper_bound` 키 사용
- `CLAUDE.md` §10 자주 하는 실수 방지 항목에 주의 사항 추가
- `OPERATIONS.md` 운영자 역할 체크리스트에 차트 JSON 스키마 검증 항목 추가
- 발행 후 verify 단계에서 차트 API 5개 별도 확인 (HTTP 200 + price_series.length > 0)

---

## 2026-03-17 — VOL.3 신규 종목 5개 차트 데이터 없음

**심각도**: 중간
**영향 범위**: 사용자 노출 (종목 상세 페이지 차트 영역)
**상태**: 해결 완료

### 현상
VOL.3 발행 후 NXPW, BLFN, STRL, VCNX, DFTL 종목 상세 페이지에서
차트 영역이 모두 "차트 데이터 없음" 으로 표시됨.

### 원인
차트 API (`GET /api/v1/chart/{ticker}`)는
`data/mock/chart/{TICKER}_price_series.json` 파일을 읽어서 반환하는데,
VOL.3 5개 종목의 파일이 존재하지 않았다.
VOL.2 종목 5개(MFGI, RVNC, HLTH, CSTM, ENXT)의 파일만 있었음.

차트 API는 파일 없을 때 `_EMPTY_CHART` (빈 price_series) 를 반환하고,
프론트엔드는 이를 "차트 데이터 없음" 으로 렌더링.

### 해결
- `scripts/_gen_chart_data.py` 작성 후 실행
- 5개 파일 생성: `data/mock/chart/` 디렉토리에
  - `NXPW_price_series.json` (52개 주간 바)
  - `BLFN_price_series.json`
  - `STRL_price_series.json`
  - `VCNX_price_series.json`
  - `DFTL_price_series.json`
- 각 파일: 2025-03-17 ~ 2026-03-14 주간 OHLCV 52포인트,
  reference_lines(52주 고점/저점), event_markers(분기 실적), interest_range_band 포함
- 주가 흐름은 stock_{TICKER}_003.json 의 52w_high/low + current_price 기준으로 설계

### 재발 방지
- 새 에디션 종목 추가 시 차트 파일 존재 여부를 preflight 에서 체크하는 항목 추가 고려
- `scripts/_gen_chart_data.py` 재사용 가능 (VOL.4 신규 종목 추가 시 참고)
- 발행 후 verify 단계에서 차트 API 응답도 확인 권장

---

## 2026-03-17 — biweekly_prepare.yml heredoc 작성 실패

**심각도**: 낮음 (개발 환경)
**영향 범위**: 개발 프로세스
**상태**: 해결 완료

### 현상
`biweekly_prepare.yml` 을 Bash heredoc (`<< 'YMLEOF'`) 으로 작성 시도 시
"unexpected EOF while looking for matching `'`" 오류 발생.

### 원인
YAML 파일 내부에 bash heredoc (`<< 'PY'`) 이 포함되어 있어
외부 heredoc 이 내부 `'PY'` 종료 문자에 조기 종료됨.

### 해결
Write 도구를 직접 사용하여 파일 내용을 문자 그대로 저장.

### 재발 방지
중첩 quote 또는 중첩 heredoc 이 포함된 파일은 Bash heredoc 대신
Write 도구(Claude Code) 또는 파이썬 스크립트로 생성.

---

## 2026-03-17 — biweekly_prep.py SyntaxWarning: invalid escape sequence

**심각도**: 낮음 (경고, 기능 영향 없음)
**영향 범위**: 개발 환경 (Python 경고 출력)
**상태**: 해결 완료

### 현상
`scripts/biweekly_prep.py` 실행 시:
```
SyntaxWarning: invalid escape sequence '\p'
SyntaxWarning: invalid escape sequence '\s'
```

### 원인
Python print() 문자열 내에 Windows 경로 (`scripts\publish_release.py`)가
포함되어 `\p` 가 유효하지 않은 이스케이프 시퀀스로 해석됨.

### 해결
백슬래시가 포함된 print() 문자열을 raw string (`r"..."`) 으로 변경.

### 재발 방지
Windows 경로 문자열은 raw string 또는 forward slash 사용.

---

## 이슈 로그 추가 방법

운영 중 새 이슈 발생 시 이 파일 맨 위 템플릿을 복사해서 추가한다.
날짜 역순(최신이 위)으로 정렬 유지.
