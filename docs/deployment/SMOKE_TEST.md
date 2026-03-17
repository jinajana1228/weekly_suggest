# Weekly Suggest — 배포 후 Smoke Test

배포 직후 아래 체크리스트를 순서대로 확인한다.
`BASE_URL`을 실제 배포 URL로 교체해서 실행한다.

```bash
BASE_URL=https://weekly-suggest.vercel.app
API_URL=https://weekly-suggest-api.railway.app
```

---

## 1. Backend Health Check

```bash
curl -s "$API_URL/health" | python3 -m json.tool
```

**예상 응답:**
```json
{
  "status": "ok",
  "env": "production",
  "provider_mode": "fmp",
  "version": "0.2.0"
}
```

- `status`: `ok` 확인
- `env`: `production` 확인 (development이면 APP_ENV 환경변수 확인)
- `provider_mode`: 설정한 모드 확인

---

## 2. Latest Report API

```bash
curl -s "$API_URL/api/v1/reports/latest" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print('report_id:', d.get('report_id'))
print('edition_number:', d.get('edition_number'))
print('status:', d.get('status'))
print('stocks:', len(d.get('stocks', [])), '개')
"
```

**확인 항목:**
- `status`: `PUBLISHED`
- `stocks`: 5개 (또는 설정한 MIN_PUBLISH_STOCKS 이상)
- `report_id`: 최신 에디션 ID

---

## 3. Archive API

```bash
curl -s "$API_URL/api/v1/archive" | python3 -c "
import sys, json
arr = json.load(sys.stdin)['data']
print('에디션 수:', len(arr))
for e in arr:
    print(f'  VOL.{e[\"edition_number\"]}  {e[\"status\"]}  {e[\"report_id\"]}')
"
```

**확인 항목:**
- 에디션 목록 1개 이상
- 최신 에디션 `PUBLISHED`, 이전 에디션 `ARCHIVED`

---

## 4. Stock Report API

```bash
# 최신 에디션의 첫 번째 종목
REPORT_ID=$(curl -s "$API_URL/api/v1/reports/latest" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['report_id'])")
TICKER=$(curl -s "$API_URL/api/v1/reports/latest" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['stocks'][0]['ticker'])")

curl -s "$API_URL/api/v1/reports/$REPORT_ID/stocks/$TICKER" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print('ticker:', d.get('ticker'))
print('current_price:', d.get('current_price', {}).get('value'))
print('narrative status:', d.get('analyst_style_summary', {}).get('why_discounted', {}).get('status'))
"
```

---

## 5. Chart API

```bash
curl -s "$API_URL/api/v1/chart/$TICKER" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print('ticker:', d.get('ticker'))
print('price_series points:', len(d.get('price_series', [])))
"
```

**확인 항목:** price_series 50포인트 이상

---

## 6. Admin API (키 보호 확인)

```bash
# 키 없이 → 403 반환 확인
curl -s -w "\nHTTP: %{http_code}" "$API_URL/api/v1/admin/review-tasks"

# 키 포함 → 200 반환 확인
curl -s -w "\nHTTP: %{http_code}" \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  "$API_URL/api/v1/admin/review-tasks"
```

**확인 항목:**
- 키 없음 → `HTTP: 403`
- 키 포함 → `HTTP: 200`

---

## 7. Frontend 페이지 확인

```bash
for path in "/" "/archive" "/disclaimer"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$path")
  echo "$code  $BASE_URL$path"
done
```

**확인 항목:** 모두 `200`

---

## 8. Frontend → Backend 연결 확인

브라우저에서 접속하거나 curl로 확인:

```bash
# 프론트엔드를 통한 API rewrite 확인
curl -s "$BASE_URL/api/v1/reports/latest" | head -c 100
```

응답이 있으면 rewrite 정상 동작.

---

## 9. 전체 체크리스트

| 항목 | 확인 방법 | 기대 결과 |
|------|---------|---------|
| Backend health | `GET /health` | `{"status":"ok","env":"production"}` |
| Latest report | `GET /api/v1/reports/latest` | PUBLISHED edition, 5개 종목 |
| Archive | `GET /api/v1/archive` | 에디션 목록 |
| Stock report | `GET /api/v1/reports/{id}/stocks/{ticker}` | 종목 상세 |
| Chart | `GET /api/v1/chart/{ticker}` | 50+ price points |
| Admin 보호 | 키 없이 `GET /api/v1/admin/*` | HTTP 403 |
| Frontend main | `GET /` | HTTP 200 |
| Frontend archive | `GET /archive` | HTTP 200 |
| API rewrite | `GET BASE_URL/api/v1/reports/latest` | 응답 있음 |
| CORS | 브라우저 콘솔 오류 없음 | 오류 없음 |

---

## 10. 장애 대응

### 메인 페이지가 빈 화면

```bash
# latest_pointer 확인
curl -s "$API_URL/api/v1/reports/latest"
# → 404이면 JSON 파일 미배포 또는 latest_pointer 미설정
# → 운영자가 publish_edition.py 실행 또는 edition_latest.json 확인
```

### Admin API가 403

```bash
# ADMIN_API_KEY 환경변수 확인
# Railway 대시보드 → Variables → ADMIN_API_KEY 값 확인
```

### CORS 오류 (브라우저 콘솔)

```bash
# CORS_ORIGINS에 프론트엔드 도메인 추가
# Railway Variables: CORS_ORIGINS=https://weekly-suggest.vercel.app
```
