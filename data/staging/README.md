# data/staging — 발행 준비 디렉토리

## 용도
`publish_release.py prepare` 실행 전, 신규 에디션의 종목 상세 JSON 파일을 여기에 넣는다.

## 파일 준비 규칙

1. 파일명: 자유롭게 작성 (예: `NXPW.json`, `stock_NXPW_draft.json`)
2. 파일 수: 최소 5개 (정기 발행 기준)
3. 파일 내용: 종목 상세 JSON (하단 필수 필드 참고)
4. `report_id`, `report_item_id`, `publication_meta` 는 스크립트가 자동 갱신하므로 임시값 OK

## 필수 필드 (최소 요건)

```json
{
  "ticker": "TICK1",
  "company_name": "...",
  "exchange": "NYSE",
  "sector": "...",
  "industry": "...",
  "stock_info": { "market_cap_usd_b": 5.0, ... },
  "current_price": { "value": 45.0, "currency": "USD", "as_of": "..." },
  "valuation": {
    "valuation_discount_vs_sector": { "discount_pct": 25.0 },
    ...
  },
  "financials": { ... },
  "undervaluation_judgment": {
    "combined_signal": "MODERATE_SIGNAL",
    "discount_narrative": { "content": "할인 원인 서술..." }
  },
  "catalyst_assessment": {
    "catalyst_a": { "status": "MET", ... },
    "catalyst_b": { "status": "NOT_MET", ... },
    "catalyst_c": { "status": "MET", ... }
  },
  "structural_risks": [ { "severity": "MEDIUM", ... } ],
  "short_term_risks":  [ { "severity": "HIGH",   ... } ],
  "data_quality_flags": [],
  "publication_meta": { "status": "PUBLISHED" }
}
```

## 권장 추가 필드

```json
{
  "one_line_thesis": "한 줄 투자 테제 (없으면 스크립트가 discount_narrative에서 자동 추출)"
}
```

## 발행 실행 순서

```cmd
cd C:\Users\MUSINSA\Desktop\Vibe Coding\weekly_suggest

REM 1. 드라이런으로 검증
python scripts\publish_release.py prepare --stocks-dir data\staging --dry-run

REM 2. 실제 발행 준비 (파일 생성)
python scripts\publish_release.py prepare --stocks-dir data\staging ^
  --context-note "이번 에디션 시황 요약 텍스트"

REM 3. 생성된 edition_latest.json 내용 확인 후
python scripts\publish_release.py commit

REM 4. 배포 완료 후 (약 3~5분)
python scripts\publish_release.py verify
```

## 주의
- 이 디렉토리의 *.json 파일은 .gitignore 에 의해 git 추적에서 제외됨
- 발행 완료 후 이 디렉토리의 파일은 수동으로 정리하거나 그대로 두어도 무방
