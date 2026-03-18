#!/usr/bin/env python3
"""Generate mock chart JSON files for VOL.3 tickers."""
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "mock" / "chart"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)


def make_dates(start: date, end: date):
    """Weekly trading dates with 5-day steps."""
    dates = []
    d = start
    while d <= end:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    return dates


def lerp_path(anchors: list, dates: list) -> list:
    """Interpolate prices between anchor (date_str, price) points."""
    anchor_dates = [date.fromisoformat(a[0]) for a in anchors]
    anchor_prices = [a[1] for a in anchors]
    closes = []
    for d_str in dates:
        d = date.fromisoformat(d_str)
        if d <= anchor_dates[0]:
            closes.append(anchor_prices[0])
            continue
        if d >= anchor_dates[-1]:
            closes.append(anchor_prices[-1])
            continue
        for i in range(len(anchor_dates) - 1):
            if anchor_dates[i] <= d <= anchor_dates[i + 1]:
                span = (anchor_dates[i + 1] - anchor_dates[i]).days
                elapsed = (d - anchor_dates[i]).days
                t = elapsed / span if span > 0 else 0
                price = anchor_prices[i] + t * (anchor_prices[i + 1] - anchor_prices[i])
                closes.append(round(price, 2))
                break
    return closes


def gen_ohlcv(dates: list, closes: list) -> list:
    """Generate OHLCV bars from close prices with realistic noise."""
    result = []
    prev_close = closes[0]
    for i, (d, close) in enumerate(zip(dates, closes)):
        vol_base = close * 0.02
        high = round(close + abs(random.gauss(0, vol_base * 1.2)), 2)
        low  = round(close - abs(random.gauss(0, vol_base * 1.2)), 2)
        open_p = round(prev_close + random.gauss(0, vol_base * 0.5), 2)
        high = max(high, open_p, close)
        low  = min(low, open_p, close)
        volume = int(random.uniform(500_000, 3_000_000))
        result.append({
            "date": d,
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })
        prev_close = close
    return result


def build(ticker, anchors, interest_low, interest_high, week52_high, week52_low, earnings_dates):
    start = date(2025, 3, 17)
    end   = date(2026, 3, 14)
    dates  = make_dates(start, end)
    closes = lerp_path(anchors, dates)
    ohlcv  = gen_ohlcv(dates, closes)

    reference_lines = [
        {"label": "WEEK_52_HIGH", "value": week52_high, "color": "#ef4444"},
        {"label": "WEEK_52_LOW",  "value": week52_low,  "color": "#22c55e"},
    ]

    event_markers = []
    for ed in earnings_dates:
        # find closest date in our series
        ed_date = date.fromisoformat(ed)
        closest = min(dates, key=lambda x: abs(date.fromisoformat(x) - ed_date))
        # find price at that date
        idx = dates.index(closest)
        event_markers.append({
            "date": closest,
            "type": "earnings",
            "label": "Earnings",
            "price": closes[idx],
        })

    return {
        "ticker": ticker,
        "interval": "1wk",
        "data": ohlcv,
        "reference_lines": reference_lines,
        "event_markers": event_markers,
        "interest_range_band": {
            "lower_bound": interest_low,
            "upper_bound": interest_high,
            "label":       "관심 가격 구간",
            "color_hint":  "rgba(59,130,246,0.12)",
        },
    }


TICKERS = [
    dict(
        ticker="NXPW",
        anchors=[
            ("2025-03-17", 50.80),
            ("2025-04-14", 54.60),
            ("2025-09-01", 51.10),
            ("2025-12-01", 47.70),
            ("2026-02-02", 37.62),
            ("2026-03-02", 31.40),
            ("2026-03-14", 34.20),
        ],
        interest_low=33.00, interest_high=37.50,
        week52_high=54.60, week52_low=31.40,
        earnings_dates=["2025-05-07", "2025-08-06", "2025-11-05", "2026-02-04", "2026-05-06"],
    ),
    dict(
        ticker="BLFN",
        anchors=[
            ("2025-03-17", 68.50),
            ("2025-05-05", 71.40),
            ("2025-09-01", 68.40),
            ("2025-12-01", 65.50),
            ("2026-02-02", 56.35),
            ("2026-03-03", 48.20),
            ("2026-03-14", 52.80),
        ],
        interest_low=50.50, interest_high=58.00,
        week52_high=71.40, week52_low=48.20,
        earnings_dates=["2025-04-22", "2025-07-22", "2025-10-21", "2026-01-27", "2026-04-22"],
    ),
    dict(
        ticker="STRL",
        anchors=[
            ("2025-03-17", 38.80),
            ("2025-04-07", 41.20),
            ("2025-09-01", 39.10),
            ("2025-12-01", 37.70),
            ("2026-02-02", 32.00),
            ("2026-03-02", 25.80),
            ("2026-03-14", 28.45),
        ],
        interest_low=27.00, interest_high=31.50,
        week52_high=41.20, week52_low=25.80,
        earnings_dates=["2025-05-12", "2025-08-11", "2025-11-10", "2026-02-09"],
    ),
    dict(
        ticker="VCNX",
        anchors=[
            ("2025-03-17", 93.50),
            ("2025-06-02", 118.40),
            ("2025-09-01", 107.00),
            ("2025-12-01", 111.90),
            ("2026-01-05", 96.00),
            ("2026-02-02", 88.90),
            ("2026-03-02", 68.50),
            ("2026-03-14", 76.30),
        ],
        interest_low=73.00, interest_high=84.00,
        week52_high=118.40, week52_low=68.50,
        earnings_dates=["2025-05-19", "2025-08-18", "2025-11-17", "2026-02-16"],
    ),
    dict(
        ticker="DFTL",
        anchors=[
            ("2025-03-17", 55.50),
            ("2025-05-05", 58.40),
            ("2025-09-01", 57.30),
            ("2025-12-01", 54.80),
            ("2026-02-02", 46.75),
            ("2026-03-02", 39.20),
            ("2026-03-14", 43.10),
        ],
        interest_low=41.50, interest_high=47.00,
        week52_high=58.40, week52_low=39.20,
        earnings_dates=["2025-05-06", "2025-08-05", "2025-11-04", "2026-02-03"],
    ),
]

for t in TICKERS:
    data = build(
        ticker=t["ticker"],
        anchors=t["anchors"],
        interest_low=t["interest_low"],
        interest_high=t["interest_high"],
        week52_high=t["week52_high"],
        week52_low=t["week52_low"],
        earnings_dates=t["earnings_dates"],
    )
    out = OUTPUT_DIR / f"{t['ticker']}_price_series.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  created: {out.name}  ({len(data['data'])} bars)")

print("done.")
