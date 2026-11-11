export type DataMode = "live" | "fixture";

export type Attribution = {
  providerName: string;
  providerUrl: string | null;
  termsUrl: string | null;
  statement: string;
  fetchedAt: string;
  dataMode: DataMode;
  fixtureNotice: string | null;
};

export type CacheInfo = {
  hit: boolean;
  ttlSeconds: number;
  fetchedAt: string;
};

export type Team = {
  id: number;
  externalId: number;
  school: string;
  mascot: string | null;
  abbreviation: string | null;
  conference: string | null;
  division: string | null;
  classification: string | null;
  color: string | null;
  alternateColor: string | null;
};

export type TeamListResponse = {
  season: number;
  teams: Team[];
  attribution: Attribution;
  cache: CacheInfo;
};

export type StatItem = {
  name: string;
  valueNumeric: number | null;
  valueText: string;
  conference: string | null;
};

export type TeamStatsResponse = {
  team: Team;
  season: number;
  stats: StatItem[];
  attribution: Attribution;
  cache: CacheInfo;
};

export type Game = {
  id: number;
  externalId: number;
  season: number;
  week: number | null;
  seasonType: string | null;
  startAt: string | null;
  homeTeamId: number | null;
  awayTeamId: number | null;
  homeSchool: string;
  awaySchool: string;
  homePoints: number | null;
  awayPoints: number | null;
  neutralSite: boolean | null;
  venue: string | null;
  status: string | null;
};

export type GamesResponse = {
  season: number;
  teamId: number | null;
  games: Game[];
  attribution: Attribution;
  cache: CacheInfo;
};

export type SeasonBounds = {
  minSeason: number;
  maxSeason: number;
  defaultSeason: number;
  coverageNote: string;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
};
