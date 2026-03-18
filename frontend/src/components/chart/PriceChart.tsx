"use client";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import type { ChartDataPackage } from "@/types/schema";
import { formatPrice, formatDate } from "@/lib/formatters";

interface PriceChartProps {
  chartData: ChartDataPackage;
  height?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-bg-overlay border border-border-default rounded-lg p-3 text-xs shadow-lg">
        <p className="text-text-muted mb-1">{label}</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          <span className="text-text-muted">종가</span>
          <span className="font-mono text-text-primary">{formatPrice(data.close)}</span>
          <span className="text-text-muted">고가</span>
          <span className="font-mono text-text-primary">{formatPrice(data.high)}</span>
          <span className="text-text-muted">저가</span>
          <span className="font-mono text-text-primary">{formatPrice(data.low)}</span>
          <span className="text-text-muted">거래량</span>
          <span className="font-mono text-text-secondary">
            {data.volume ? (data.volume / 1000000).toFixed(1) + "M" : "—"}
          </span>
        </div>
      </div>
    );
  }
  return null;
};

export function PriceChart({ chartData, height = 280 }: PriceChartProps) {
  const { price_series, event_markers, reference_lines, interest_range_band } = chartData;

  if (!price_series || price_series.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center bg-bg-surface rounded-lg border border-border-default"
      >
        <p className="text-text-muted text-sm">차트 데이터 없음</p>
      </div>
    );
  }

  // 이벤트 마커를 날짜 맵으로 변환
  const eventMap: Record<string, string> = {};
  event_markers.forEach((m) => {
    eventMap[m.date] = m.label;
  });

  // reference lines 분류
  const w52High = reference_lines.find((l) => l.line_type === "WEEK_52_HIGH");
  const w52Low = reference_lines.find((l) => l.line_type === "WEEK_52_LOW");

  // Y축 범위
  const allPrices = price_series.flatMap((p) => [p.high, p.low]);
  const minPrice = Math.min(...allPrices) * 0.97;
  const maxPrice = Math.max(...allPrices) * 1.02;

  // X축 레이블 (매 30포인트)
  const tickDates = price_series
    .filter((_, i) => i % 25 === 0 || i === price_series.length - 1)
    .map((p) => p.date);

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={price_series}
          margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="2 4" stroke="#27272A" vertical={false} />

          <XAxis
            dataKey="date"
            ticks={tickDates}
            tick={{ fill: "#71717A", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val) => {
              const d = new Date(val);
              return `${d.getFullYear().toString().slice(2)}/${String(d.getMonth() + 1).padStart(2, "0")}`;
            }}
          />

          <YAxis
            domain={[minPrice, maxPrice]}
            tick={{ fill: "#71717A", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${v.toFixed(0)}`}
            width={48}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* 관심 가격 구간 밴드 */}
          {interest_range_band && (
            <ReferenceArea
              y1={interest_range_band.lower_bound}
              y2={interest_range_band.upper_bound}
              fill="#F59E0B"
              fillOpacity={0.06}
              strokeOpacity={0}
            />
          )}

          {/* 52주 고점 */}
          {w52High && (
            <ReferenceLine
              y={w52High.value}
              stroke="#22C55E"
              strokeDasharray="4 2"
              strokeOpacity={0.5}
              label={{
                value: `52W H $${w52High.value}`,
                position: "insideTopRight",
                fill: "#22C55E",
                fontSize: 9,
                opacity: 0.7,
              }}
            />
          )}

          {/* 52주 저점 */}
          {w52Low && (
            <ReferenceLine
              y={w52Low.value}
              stroke="#EF4444"
              strokeDasharray="4 2"
              strokeOpacity={0.5}
              label={{
                value: `52W L $${w52Low.value}`,
                position: "insideBottomRight",
                fill: "#EF4444",
                fontSize: 9,
                opacity: 0.7,
              }}
            />
          )}

          {/* 어닝 이벤트 마커 */}
          {event_markers
            .filter((m) => m.event_type === "EARNINGS_RELEASE")
            .map((m) => (
              <ReferenceLine
                key={m.marker_id}
                x={m.date}
                stroke="#3B82F6"
                strokeOpacity={0.4}
                strokeDasharray="2 3"
              />
            ))}

          {/* 가격 라인 */}
          <Line
            type="monotone"
            dataKey="close"
            stroke="#3B82F6"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: "#3B82F6", strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* 범례 */}
      <div className="flex items-center gap-4 mt-2 px-12">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-px bg-accent-blue" />
          <span className="text-[10px] text-text-muted">종가</span>
        </div>
        {w52High && (
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-px bg-accent-green opacity-50" style={{ backgroundImage: "repeating-linear-gradient(90deg, #22C55E 0px, #22C55E 4px, transparent 4px, transparent 6px)" }} />
            <span className="text-[10px] text-text-muted">52주 고점</span>
          </div>
        )}
        {w52Low && (
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-px bg-accent-red opacity-50" />
            <span className="text-[10px] text-text-muted">52주 저점</span>
          </div>
        )}
        {interest_range_band && (
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-3 bg-accent-gold opacity-15 rounded-sm" />
            <span className="text-[10px] text-text-muted">
              관심 구간{" "}
              <span className="font-mono text-accent-gold opacity-80">
                ${interest_range_band.lower_bound} — ${interest_range_band.upper_bound}
              </span>
            </span>
          </div>
        )}
        {event_markers.some((m) => m.event_type === "EARNINGS_RELEASE") && (
          <div className="flex items-center gap-1.5">
            <div className="w-px h-3 bg-accent-blue opacity-40" />
            <span className="text-[10px] text-text-muted">실적 발표</span>
          </div>
        )}
      </div>
    </div>
  );
}
