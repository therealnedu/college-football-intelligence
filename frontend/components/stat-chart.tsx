"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartPoint } from "@/lib/stats";

export function StatChart({ points }: { points: ChartPoint[] }) {
  if (points.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl border border-dashed border-border px-6 text-center text-sm text-muted-foreground">
        No chartable yardage stats were stored for this team and season. Missing
        stats are left off the chart rather than drawn as zero.
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 640, height: 256 }}
      >
        <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#3d5248" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#b7c7bc", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#b7c7bc", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip
            cursor={{ fill: "color-mix(in oklch, var(--primary) 12%, transparent)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0].payload as ChartPoint;
              return (
                <div className="rounded-lg border border-border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-sm">
                  <div className="font-medium">{point.label}</div>
                  <div className="text-muted-foreground">Stored token: {point.valueText}</div>
                </div>
              );
            }}
          />
          <Bar dataKey="value" fill="#e2b15a" radius={[6, 6, 0, 0]} maxBarSize={72} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
