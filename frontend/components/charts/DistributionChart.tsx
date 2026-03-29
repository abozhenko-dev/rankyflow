"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const BAR_COLORS = [
  "#818cf8", "#22c55e", "#f97316", "#06b6d4",
  "#ec4899", "#eab308", "#a855f7", "#ef4444",
];

interface DistributionEntry {
  name: string;
  value: number;
  isOwn?: boolean;
}

interface DistributionChartProps {
  data: DistributionEntry[];
  height?: number;
  label?: string;
  formatValue?: (v: number) => string;
}

export default function DistributionChart({
  data,
  height = 220,
  label = "Share of Voice",
  formatValue = (v) => `${(v * 100).toFixed(1)}%`,
}: DistributionChartProps) {
  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center bg-surface-100 border border-zinc-800/60 rounded-xl"
        style={{ height }}
      >
        <p className="text-sm text-zinc-600">No data</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5">
      <h3 className="text-xs uppercase tracking-[0.1em] text-zinc-500 font-semibold mb-4">
        {label}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={32}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#27272a"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={{ fill: "#71717a", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#27272a" }}
          />
          <YAxis
            tick={{ fill: "#71717a", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip
            contentStyle={{
              background: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "10px",
              padding: "10px 14px",
              fontSize: 12,
            }}
            formatter={(value: any) => formatValue(value)}
            labelStyle={{ color: "#a1a1aa", marginBottom: 4, fontSize: 11 }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={entry.name}
                fill={entry.isOwn ? "#818cf8" : BAR_COLORS[i % BAR_COLORS.length]}
                opacity={entry.isOwn ? 1 : 0.65}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
