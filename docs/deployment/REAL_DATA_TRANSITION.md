# 실데이터 전환 가이드 (mock → fmp/hybrid)

현재 배포 환경은 `DATA_PROVIDER_MODE=mock`으로 운영 중이다.
이 문서는 FMP 실데이터로 전환하는 절차를 단계별로 설명한다.

---

## 전환 전 체크리스트

- [ ] FMP API 키 발급 (https://financialmodelingprep.com)
- [ ] FMP 요금제 확인 (무료 플랜은 일부 엔드포인트 제한)
- [ ] Railway Volume 마운트 여부 결정 (SQLite 지속성)

---

## FMP 무료 플랜 사용 가능 엔드포인트

| 엔드포인트 | 무료 | 사용 위치 |
|-----------|------|----------|
| `/v3/stock-screener` | ✓ | `get_universe_candidates()` |
| `/v3/profile/{ticker}` | ✓ | `get_stock_snapshot()` |
| `/v3/ratios-ttm/{ticker}` | ✓ | `get_stock_snapshot()` 멀티플 |
| `/v3/historical-price-full/{ticker}` | ✓ | `get_price_series()` |
| `/v4/price-target-consensus` | ✗ 유료 | `get_consensus_data()` |
| `/v3/earning_calendar` | ✓ 제한적 | `get_earnings_calendar()` |

> 무료 플랜에서 `/v4/price-target-consensus`가 실패하면 컨센서스 데이터는 `null`로 처리된다.
> 촉매(Catalyst) 분석의 일부 항목이 `UNVERIFIABLE` 상태가 될 수 있다.

**권장: hybrid 모드**
- 가격 시계열: yfinance (무료, 안정적)
- 컨센서스/어닝: FMP (유료 플랜 시)
- 유니버스/스냅샷: FMP

---

## 전환 절차

### 1단계 — FMP API 키 Railway에 추가

Railway 대시보드 → Variables 탭:
```
FMP_API_KEY = <your-fmp-key>
```

### 2단계 — 로컬에서 먼저 검증

```bash
cd weekly_suggest/backend

# .env에 임시 설정
echo "DATA_PROVIDER_MODE=fmp" >> .env
echo "FMP_API_KEY=<your-key>" >> .env

# 서버 시작
uvicorn app.main:app --reload

# 단일 종목 스냅샷 테스트
curl http://localhost:8000/api/v1/admin/run-screening
# 또는 스크리닝 없이 단일 종목 확인:
python -c "
from app.services.provider.factory import get_provider
p = get_provider()
print(p.get_stock_snapshot('AAPL'))
"
```

기대 결과:
- `fwd_per`, `pb`, `ev_ebitda` 중 최소 1개 이상 `None`이 아닌 값
- `current_price` 값 존재
- `company_name`, `sector` 값 존재

### 3단계 — 스크리닝 파이프라인 테스트

```bash
python -c "
from app.services.provider.factory import get_provider
from app.services.screening.pipeline import run_screening

provider = get_provider()
result = run_screening(provider, use_mock_universe=False, top_n=5)
print(f'후보: {result[\"total_candidates\"]}개')
print(f'선정: {result[\"selected_count\"]}개')
for s in result['selected']:
    print(f'  {s[\"ticker\"]} | {s[\"sector\"]} | score={s[\"score\"]:.2f}')
"
```

### 4단계 — Railway 환경변수 전환

Railway Variables 업데이트:
```
DATA_PROVIDER_MODE = fmp       ← mock에서 변경
FMP_API_KEY        = <your-key>  ← 새로 추가
```

> Railway가 자동 재배포된다. 재배포 완료 후 Railway 로그에서 확인:
> ```
> Weekly Suggest API starting | env=production | provider=fmp
> ```

### 5단계 — 실데이터 기준 스크리닝 실행

Railway 재배포 완료 후 Admin UI에서:
1. `/admin` 접속 → 키 입력
2. **"스크리닝 실행"** 버튼 클릭
3. 결과 확인 — mock 데이터 대신 실시간 종목이 나타남

---

## 알려진 필드 매핑 이슈

### `financials` 필드 (UNAVAILABLE 상태)

FMP `profile` + `ratios-ttm`에는 재무제표 상세(`revenue_ttm_b`, `operating_income_ttm_b` 등)가 없다.
`financials` 섹션은 실데이터 전환 후에도 `UNAVAILABLE` 상태로 표시된다.

완전한 financials를 채우려면 추가 엔드포인트가 필요하다:
```
/v3/income-statement/{ticker}?limit=1  → revenue, operating_income, net_income
/v3/cash-flow-statement/{ticker}?limit=1  → fcf
/v3/balance-sheet-statement/{ticker}?limit=1  → net_debt
/v3/key-metrics-ttm/{ticker}  → roe, eps_ttm
```

현재는 스캐폴드(UNAVAILABLE) 상태로 운영하고, FMP Starter 플랜($25/월) 이상에서 확장 가능.

### `52w_high` / `52w_low` 파싱

FMP `profile.range` 필드는 `"52.00-128.00"` 형식의 문자열이다.
`fmp_provider.get_stock_snapshot()`에서 `split("-")` 파싱으로 처리하지만,
음수 범위(예: `"-5.00-12.00"`)에서 오파싱될 수 있다.

실제 배포 후 종목별로 `52w_high` / `52w_low` 값이 이상하면:
```python
# fmp_provider.py get_stock_snapshot() 마지막 부분
"52w_high": profile.get("fiftyTwoWeekHigh"),  # 직접 필드로 대체
"52w_low": profile.get("fiftyTwoWeekLow"),
```
yfinance의 경우 `info["fiftyTwoWeekHigh"]`를 직접 사용하므로 더 안전하다.
→ 52w 데이터가 중요하면 **hybrid 모드** 사용 권장 (yfinance가 52w 직접 제공).

### `price_context` 계산

`build_report()`가 자동으로 `get_price_series(ticker, period_days=365)`를 호출하여
52w 위치, 고점 대비 하락, 1/3/6개월 수익률을 계산한다.

FMP 가격 시계열 엔드포인트가 실패하면 모든 항목이 `UNAVAILABLE` 상태가 된다.
yfinance는 이 데이터에 더 안정적이므로 hybrid 모드에서는 yfinance가 대신 호출된다.

---

## hybrid 모드 설정 (권장)

FMP Starter 이상 플랜 + yfinance 무료 조합:

```
DATA_PROVIDER_MODE = hybrid
FMP_API_KEY        = <your-key>
```

| 데이터 | 소스 | 비고 |
|--------|------|------|
| 유니버스 스크리닝 | FMP screener | 실시간 필터 |
| 종목 스냅샷 (멀티플) | FMP profile + ratios-ttm | |
| 가격 시계열 | yfinance (FMP fallback) | 무료 + 안정적 |
| 컨센서스 / 목표가 | FMP → yfinance fallback | |
| 어닝 캘린더 | FMP → yfinance fallback | |

---

## 전환 후 운영 노트

- 실데이터 스크리닝은 **API 호출 시간**으로 인해 mock보다 느리다 (종목당 2-4초).
- Railway 무료 플랜은 인스턴스가 슬립 상태가 될 수 있다. Starter 플랜($5/월) 권장.
- FMP 무료 플랜은 분당 300 요청 제한. 스크리닝 시 종목 수에 따라 rate limit 주의.
- 스크리닝 결과는 `state.db`에 저장된다. Railway Volume 없이 배포하면 재시작 시 초기화된다.
  → `STATE_DB_PATH=/data/state.db` + Railway Volume 마운트로 영속성 확보 가능.
