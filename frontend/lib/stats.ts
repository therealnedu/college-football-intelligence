import type { StatItem } from "@/lib/types";

/** Yardage names the chart will plot when the stored row has a numeric value.

The list is a display choice. Missing names are omitted. They are not drawn as zero.
*/
export const YARDAGE_CHART_STATS = ["totalYards", "netPassingYards", "rushingYards"] as const;

export type ChartPoint = {
  name: string;
  label: string;
  value: number;
  valueText: string;
};

export type StatGroup = {
  label: string;
  stats: StatItem[];
};

export function labelForStat(name: string): string {
  const spaced = name
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .trim();
  if (!spaced) return name;
  return spaced
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function chartSeries(stats: StatItem[]): ChartPoint[] {
  const byName = new Map(stats.map((stat) => [stat.name, stat]));
  const points: ChartPoint[] = [];
  for (const name of YARDAGE_CHART_STATS) {
    const stat = byName.get(name);
    if (!stat || stat.valueNumeric === null || !Number.isFinite(stat.valueNumeric)) {
      continue;
    }
    points.push({
      name,
      label: labelForStat(name),
      value: stat.valueNumeric,
      valueText: stat.valueText,
    });
  }
  return points;
}

export function groupStats(stats: StatItem[]): StatGroup[] {
  const passing: StatItem[] = [];
  const rushing: StatItem[] = [];
  const defense: StatItem[] = [];
  const other: StatItem[] = [];
  const sorted = [...stats].sort((a, b) => a.name.localeCompare(b.name));
  for (const stat of sorted) {
    const name = stat.name.toLowerCase();
    if (name.includes("pass")) {
      passing.push(stat);
    } else if (name.includes("rush")) {
      rushing.push(stat);
    } else if (/def|interception|fumble|sack|tackle/.test(name)) {
      defense.push(stat);
    } else {
      other.push(stat);
    }
  }
  return [
    { label: "Passing", stats: passing },
    { label: "Rushing", stats: rushing },
    { label: "Defense", stats: defense },
    { label: "Other", stats: other },
  ].filter((group) => group.stats.length > 0);
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const formatted = new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    hourCycle: "h23",
  }).format(date);
  return `${formatted} UTC`;
}

export function displayValue(stat: StatItem): string {
  if (stat.valueText.trim() !== "") return stat.valueText;
  return "—";
}
