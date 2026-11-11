import type {
  Attribution,
  CacheInfo,
  Game,
  GamesResponse,
  SeasonBounds,
  StatItem,
  Team,
  TeamListResponse,
  TeamStatsResponse,
} from "@/lib/types";

export const FIXTURE_LABEL = "NOT REAL COLLEGE FOOTBALL STATISTICS";

export type SnapshotIngest = {
  providerCalls: number;
  stoppedEarly: boolean;
  note: string;
  resources: { resource: string; status: string; recordsWritten: number }[];
};

export type SnapshotDocument = {
  snapshotVersion: 1;
  generatedAt: string;
  season: number;
  dataMode: "live" | "fixture";
  delivery: "snapshot";
  attribution: Attribution;
  seasons: SeasonBounds;
  teams: Team[];
  games: Game[];
  statsByTeamId: Record<string, StatItem[]>;
  ingest: SnapshotIngest;
};

export class SnapshotParseError extends Error {
  code: string;

  constructor(message: string, code: string) {
    super(message);
    this.code = code;
  }
}

export function parseSnapshot(payload: unknown): SnapshotDocument {
  if (!isRecord(payload) || payload.snapshotVersion !== 1) {
    throw new SnapshotParseError("The snapshot file is not a CFIP snapshot.", "SNAPSHOT_INVALID");
  }
  if (payload.dataMode !== "live" && payload.dataMode !== "fixture") {
    throw new SnapshotParseError(
      "The snapshot does not say whether its data is live or fixture.",
      "SNAPSHOT_INVALID",
    );
  }
  if (!isRecord(payload.attribution) || typeof payload.attribution.statement !== "string") {
    throw new SnapshotParseError("The snapshot is missing its source statement.", "SNAPSHOT_INVALID");
  }
  const notice = typeof payload.attribution.fixtureNotice === "string" ? payload.attribution.fixtureNotice : "";
  const statement = payload.attribution.statement;
  if (payload.dataMode === "fixture" && !statement.includes(FIXTURE_LABEL) && !notice.includes(FIXTURE_LABEL)) {
    throw new SnapshotParseError(
      "A fixture snapshot must carry the synthetic-data label.",
      "SNAPSHOT_UNLABELED",
    );
  }
  if (payload.dataMode === "live" && (statement.includes(FIXTURE_LABEL) || notice.includes(FIXTURE_LABEL))) {
    throw new SnapshotParseError(
      "A live snapshot is carrying the fixture label.",
      "SNAPSHOT_MISLABELED",
    );
  }
  if (!isRecord(payload.seasons) || typeof payload.seasons.defaultSeason !== "number") {
    throw new SnapshotParseError("The snapshot is missing its season bounds.", "SNAPSHOT_INVALID");
  }
  if (!Array.isArray(payload.teams) || !Array.isArray(payload.games) || !isRecord(payload.statsByTeamId)) {
    throw new SnapshotParseError("The snapshot is missing teams, games, or stats.", "SNAPSHOT_INVALID");
  }
  if (!isRecord(payload.ingest) || typeof payload.ingest.note !== "string") {
    throw new SnapshotParseError("The snapshot is missing its build note.", "SNAPSHOT_INVALID");
  }
  return payload as SnapshotDocument;
}

export function seasonsFromSnapshot(doc: SnapshotDocument): SeasonBounds {
  return doc.seasons;
}

export function teamListFromSnapshot(doc: SnapshotDocument, season: number): TeamListResponse {
  assertSeason(doc, season);
  return {
    season: doc.season,
    teams: doc.teams,
    attribution: doc.attribution,
    cache: cacheFor(doc),
  };
}

export function statsFromSnapshot(doc: SnapshotDocument, teamId: number, season: number): TeamStatsResponse {
  assertSeason(doc, season);
  const team = doc.teams.find((item) => item.id === teamId);
  if (!team) {
    throw new SnapshotParseError("No team with that id is in this snapshot.", "TEAM_NOT_FOUND");
  }
  return {
    team,
    season: doc.season,
    stats: doc.statsByTeamId[String(teamId)] ?? [],
    attribution: doc.attribution,
    cache: cacheFor(doc),
  };
}

export function gamesFromSnapshot(doc: SnapshotDocument, season: number): GamesResponse {
  assertSeason(doc, season);
  return {
    season: doc.season,
    teamId: null,
    games: doc.games,
    attribution: doc.attribution,
    cache: cacheFor(doc),
  };
}

function assertSeason(doc: SnapshotDocument, season: number): void {
  if (season !== doc.season) {
    throw new SnapshotParseError(
      `This static snapshot only includes the ${doc.season} season.`,
      "SEASON_NOT_IN_SNAPSHOT",
    );
  }
}

function cacheFor(doc: SnapshotDocument): CacheInfo {
  return {
    hit: true,
    ttlSeconds: 0,
    fetchedAt: doc.attribution.fetchedAt,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
