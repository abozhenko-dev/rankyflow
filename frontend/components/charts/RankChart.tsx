"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// Domain → color mapping
const DOMAIN_COLORS = [
  "#818cf8", // brand indigo
  "#f97316", // orange
  "#22c55e", // green
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#eab308", // yellow
  "#a855f7", // purple
  "#ef4444", // red
];

interface RankDataPoint {
  date: string;
  [domain: string]: number | string | null;
}

interface RankChartProps {
  data: RankDataPoint[];
  domains: string[];
  ownDomain?: string;
  height?: number;
}

export default function RankChart({
  data,
  domains,
  ownDomain,
  height = 320,
}: RankChartProps) {
  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center bg-surface-100 border border-zinc-800/60 rounded-xl"
        style={{ height }}
      >
        <p className="text-sm text-zinc-600">No rank history data yet</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#27272a"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fill: "#71717a", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#27272a" }}
          />
          <YAxis
            reversed
            domain={[1, "auto"]}
            tick={{ fill: "#71717a", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            label={{
              value: "Position",
              angle: -90,
              position: "insideLeft",
              style: { fill: "#52525b", fontSize: 11 },
            }}
          />
          <Tooltip
            contentStyle={{
              background: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "10px",
              padding: "10px 14px",
              fontSize: 12,
            }}
            itemStyle={{ color: "#e4e4e7", padding: "2px 0" }}
            labelStyle={{ color: "#a1a1aa", marginBottom: 4, fontSize: 11 }}
            formatter={(value: any) =>
              value === null ? "100+" : `#${value}`
            }
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            iconType="circle"
            iconSize={8}
          />
          {domains.map((domain, i) => (
            <Line
              key={domain}
              type="monotone"
              dataKey={domain}
              name={domain}
              stroke={
                domain === ownDomain ? DOMAIN_COLORS[0] : DOMAIN_COLORS[(i % DOMAIN_COLORS.length)]
              }
              strokeWidth={domain === ownDomain ? 2.5 : 1.5}
              dot={false}
              activeDot={{
                r: 4,
                fill: domain === ownDomain ? DOMAIN_COLORS[0] : DOMAIN_COLORS[i % DOMAIN_COLORS.length],
                stroke: "#18181b",
                strokeWidth: 2,
              }}
              connectNulls={false}
              opacity={domain === ownDomain ? 1 : 0.7}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
