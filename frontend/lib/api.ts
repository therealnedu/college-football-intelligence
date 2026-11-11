import {
  gamesFromSnapshot,
  parseSnapshot,
  seasonsFromSnapshot,
  SnapshotParseError,
  statsFromSnapshot,
  teamListFromSnapshot,
  type SnapshotDocument,
} from "@/lib/snapshot";
import type {
  ApiErrorBody,
  GamesResponse,
  SeasonBounds,
  TeamListResponse,
  TeamStatsResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/cfip-api";

export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;

  constructor(message: string, code: string, status: number, details: Record<string, unknown>) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function apiBaseUrl(): string {
  return API_BASE;
}

export function delivery(): "api" | "snapshot" {
  return process.env.NEXT_PUBLIC_DATA_SOURCE === "snapshot" ? "snapshot" : "api";
}

let snapshotRequest: Promise<SnapshotDocument> | null = null;

export function loadSnapshot(): Promise<SnapshotDocument> {
  if (snapshotRequest) return snapshotRequest;
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  snapshotRequest = fetch(`${base}/data/snapshot.json`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) {
        throw new ApiError(
          "The static snapshot was not published with this page.",
          "SNAPSHOT_MISSING",
          response.status,
          {},
        );
      }
      const body: unknown = await response.json().catch(() => null);
      try {
        return parseSnapshot(body);
      } catch (error) {
        if (error instanceof SnapshotParseError) {
          throw new ApiError(error.message, error.code, 500, {});
        }
        throw error;
      }
    })
    .catch((error: unknown) => {
      snapshotRequest = null;
      if (error instanceof ApiError) throw error;
      throw new ApiError("The browser could not read the static snapshot.", "SNAPSHOT_UNREACHABLE", 0, {});
    });
  return snapshotRequest;
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError(
      `The browser could not reach the CFIP API at ${API_BASE}.`,
      "API_UNREACHABLE",
      0,
      {},
    );
  }
  const body = (await response.json().catch(() => null)) as ApiErrorBody | T | null;
  if (!response.ok) {
    const error = body && typeof body === "object" && "error" in body ? body.error : null;
    throw new ApiError(
      error?.message ?? `The API returned HTTP ${response.status}.`,
      error?.code ?? "HTTP_ERROR",
      response.status,
      error?.details ?? {},
    );
  }
  return body as T;
}

function fromSnapshot<T>(read: (document: SnapshotDocument) => T): Promise<T> {
  return loadSnapshot().then((document) => {
    try {
      return read(document);
    } catch (error) {
      if (error instanceof SnapshotParseError) {
        throw new ApiError(error.message, error.code, 404, {});
      }
      throw error;
    }
  });
}

export function fetchSeasons(): Promise<SeasonBounds> {
  if (delivery() === "snapshot") return fromSnapshot((document) => seasonsFromSnapshot(document));
  return getJson<SeasonBounds>("/seasons");
}

export function fetchTeams(season: number): Promise<TeamListResponse> {
  if (delivery() === "snapshot") return fromSnapshot((document) => teamListFromSnapshot(document, season));
  return getJson<TeamListResponse>(`/teams?season=${season}`);
}

export function fetchTeamStats(teamId: number, season: number): Promise<TeamStatsResponse> {
  if (delivery() === "snapshot") {
    return fromSnapshot((document) => statsFromSnapshot(document, teamId, season));
  }
  return getJson<TeamStatsResponse>(`/teams/${teamId}/stats?season=${season}`);
}

export function fetchGames(season: number): Promise<GamesResponse> {
  if (delivery() === "snapshot") return fromSnapshot((document) => gamesFromSnapshot(document, season));
  return getJson<GamesResponse>(`/games?season=${season}`);
}
