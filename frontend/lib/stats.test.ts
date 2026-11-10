import { describe, expect, it } from "vitest";

import { chartSeries, formatTimestamp, groupStats, labelForStat } from "@/lib/stats";
import type { StatItem } from "@/lib/types";

const stats: StatItem[] = [
  { name: "rushingYards", valueNumeric: 40, valueText: "40", conference: "Fixture Conference" },
  { name: "netPassingYards", valueNumeric: 100, valueText: "100", conference: "Fixture Conference" },
  { name: "possessionTime", valueNumeric: null, valueText: "99:99", conference: "Fixture Conference" },
  { name: "passingTDs", valueNumeric: 3, valueText: "3", conference: "Fixture Conference" },
  { name: "interceptions", valueNumeric: 2, valueText: "2", conference: "Fixture Conference" },
  { name: "turnoverMargin", valueNumeric: 1, valueText: "1", conference: "Fixture Conference" },
];

describe("chartSeries", () => {
  it("plots only stored numeric yardage stats and does not fill missing ones with zero", () => {
    const series = chartSeries(stats);
    expect(series.map((point) => point.name)).toEqual(["netPassingYards", "rushingYards"]);
    expect(series.map((point) => point.value)).toEqual([100, 40]);
    expect(series.some((point) => point.name === "totalYards")).toBe(false);
  });

  it("returns an empty series when nothing chartable was stored", () => {
    expect(chartSeries([stats[2]])).toEqual([]);
  });
});

describe("groupStats", () => {
  it("groups by the stat name and sorts within the group", () => {
    const groups = groupStats(stats);
    expect(groups.map((group) => group.label)).toEqual(["Passing", "Rushing", "Defense", "Other"]);
    expect(groups[0].stats.map((stat) => stat.name)).toEqual(["netPassingYards", "passingTDs"]);
    expect(groups[2].stats.map((stat) => stat.name)).toEqual(["interceptions"]);
    expect(groups[3].stats.map((stat) => stat.name)).toEqual(["possessionTime", "turnoverMargin"]);
  });
});

describe("labels and timestamps", () => {
  it("splits a camel-case stat name for display", () => {
    expect(labelForStat("netPassingYards")).toBe("Net Passing Yards");
  });

  it("formats timestamps in UTC and leaves invalid input unchanged", () => {
    expect(formatTimestamp("2026-11-10T05:35:00Z")).toContain("UTC");
    expect(formatTimestamp("not-a-date")).toBe("not-a-date");
  });
});
