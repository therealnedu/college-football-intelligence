import { describe, expect, it } from "vitest";

import { deliveryDetail, provenanceTitle } from "@/lib/provenance";
import { parseSnapshot } from "@/lib/snapshot";

describe("provenance copy", () => {
  it("names fixture data and live data differently", () => {
    expect(provenanceTitle("fixture")).toBe("Fixture data. Not real college football statistics.");
    expect(provenanceTitle("live")).toContain("CollegeFootballData.com");
    expect(provenanceTitle("live")).not.toContain("NOT REAL COLLEGE FOOTBALL STATISTICS");
    expect(deliveryDetail("snapshot", "Nov 11, 2026")).toContain("static snapshot");
    expect(deliveryDetail("api", null)).toContain("key stays on the server");
  });
});

describe("parseSnapshot", () => {
  it("accepts a labeled fixture snapshot and rejects an unlabeled one", () => {
    const document = parseSnapshot(fixtureSnapshot());
    expect(document.teams[0]?.school).toBe("Fixture Falcons University");

    const unlabeled = fixtureSnapshot();
    unlabeled.attribution.statement = "Looks official.";
    unlabeled.attribution.fixtureNotice = null;
    expect(() => parseSnapshot(unlabeled)).toThrow(/synthetic-data label/);
  });

  it("rejects a live snapshot that still carries the fixture label", () => {
    const document = fixtureSnapshot();
    document.dataMode = "live";
    document.attribution.dataMode = "live";
    expect(() => parseSnapshot(document)).toThrow(/fixture label/);
  });
});

function fixtureSnapshot() {
  return {
    snapshotVersion: 1 as const,
    generatedAt: "2026-11-11T00:00:00Z",
    season: 2025,
    dataMode: "fixture" as const,
    delivery: "snapshot" as const,
    attribution: {
      providerName: "CFIP synthetic fixture",
      providerUrl: null,
      termsUrl: null,
      statement: "NOT REAL COLLEGE FOOTBALL STATISTICS",
      fetchedAt: "2026-11-11T00:00:00Z",
      dataMode: "fixture" as const,
      fixtureNotice: "NOT REAL COLLEGE FOOTBALL STATISTICS",
    },
    seasons: {
      minSeason: 2025,
      maxSeason: 2025,
      defaultSeason: 2025,
      coverageNote: "One season.",
    },
    teams: [
      {
        id: 1,
        externalId: 900001,
        school: "Fixture Falcons University",
        mascot: null,
        abbreviation: null,
        conference: null,
        division: null,
        classification: "fixture",
        color: null,
        alternateColor: null,
      },
    ],
    games: [],
    statsByTeamId: { "1": [] },
    ingest: {
      providerCalls: 0,
      stoppedEarly: false,
      note: "Built from fixtures. NOT REAL COLLEGE FOOTBALL STATISTICS.",
      resources: [],
    },
  };
}
