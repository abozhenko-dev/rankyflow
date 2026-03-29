"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const PLATFORM_COLORS: Record<string, string> = {
  chatgpt:    "#22c55e",
  perplexity: "#3b82f6",
  claude:     "#f59e0b",
  gemini:     "#a855f7",
  deepseek:   "#06b6d4",
};

interface VisibilityDataPoint {
  date: string;
  [platform: string]: number | string;
}

interface VisibilityChartProps {
  data: VisibilityDataPoint[];
  platforms: string[];
  metric?: "mention_rate" | "citation_rate" | "share_of_voice";
  height?: number;
}

export default function VisibilityChart({
  data,
  platforms,
  metric = "mention_rate",
  height = 280,
}: VisibilityChartProps) {
  const metricLabels: Record<string, string> = {
    mention_rate: "Mention Rate",
    citation_rate: "Citation Rate",
    share_of_voice: "Share of Voice",
  };

  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center bg-surface-100 border border-zinc-800/60 rounded-xl"
        style={{ height }}
      >
        <p className="text-sm text-zinc-600">No visibility trend data yet</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5">
      <h3 className="text-xs uppercase tracking-[0.1em] text-zinc-500 font-semibold mb-4">
        {metricLabels[metric] || metric} — Weekly Trend
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <defs>
            {platforms.map((platform) => (
              <linearGradient
                key={platform}
                id={`grad-${platform}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="5%"
                  stopColor={PLATFORM_COLORS[platform] || "#6366f1"}
                  stopOpacity={0.2}
                />
                <stop
                  offset="95%"
                  stopColor={PLATFORM_COLORS[platform] || "#6366f1"}
                  stopOpacity={0}
                />
              </linearGradient>
            ))}
          </defs>
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
            tick={{ fill: "#71717a", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            domain={[0, "auto"]}
          />
          <Tooltip
            contentStyle={{
              background: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "10px",
              padding: "10px 14px",
              fontSize: 12,
            }}
            formatter={(value: any) => `${(value * 100).toFixed(1)}%`}
            labelStyle={{ color: "#a1a1aa", marginBottom: 4, fontSize: 11 }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            iconType="circle"
            iconSize={8}
          />
          {platforms.map((platform) => (
            <Area
              key={platform}
              type="monotone"
              dataKey={platform}
              name={platform}
              stroke={PLATFORM_COLORS[platform] || "#6366f1"}
              fill={`url(#grad-${platform})`}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                fill: PLATFORM_COLORS[platform] || "#6366f1",
                stroke: "#18181b",
                strokeWidth: 2,
              }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
