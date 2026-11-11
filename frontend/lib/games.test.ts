import { describe, expect, it } from "vitest";

import { gamesForTeam, matchupText, pointsText } from "@/lib/games";
import type { Game } from "@/lib/types";

const games: Game[] = [
  {
    id: 2,
    externalId: 910002,
    season: 2025,
    week: 2,
    seasonType: "regular",
    startAt: "2025-09-13T16:00:00Z",
    homeTeamId: 3,
    awayTeamId: 1,
    homeSchool: "Empty Roster College",
    awaySchool: "Fixture Falcons University",
    homePoints: null,
    awayPoints: null,
    neutralSite: true,
    venue: "Placeholder Stadium",
    status: "scheduled",
  },
  {
    id: 1,
    externalId: 910001,
    season: 2025,
    week: 1,
    seasonType: "regular",
    startAt: "2025-09-06T16:00:00Z",
    homeTeamId: 1,
    awayTeamId: 2,
    homeSchool: "Fixture Falcons University",
    awaySchool: "Sample State Polytechnic",
    homePoints: 24,
    awayPoints: 10,
    neutralSite: false,
    venue: "Fixture Field",
    status: "final",
  },
];

describe("pointsText", () => {
  it("leaves a missing score blank instead of showing zero", () => {
    expect(pointsText(null)).toBe("—");
    expect(pointsText(0)).toBe("0");
    expect(matchupText(games[0])).toBe("Fixture Falcons University — vs Empty Roster College —");
    expect(matchupText(games[1])).toBe("Sample State Polytechnic 10 at Fixture Falcons University 24");
  });
});

describe("gamesForTeam", () => {
  it("returns that team's games in week order", () => {
    const rows = gamesForTeam(games, { id: 1, school: "Fixture Falcons University" });
    expect(rows.map((game) => game.week)).toEqual([1, 2]);
    expect(gamesForTeam(games, { id: 3, school: "Empty Roster College" })).toHaveLength(1);
    expect(gamesForTeam(games, { id: 9, school: "Nobody" })).toHaveLength(0);
  });
});
