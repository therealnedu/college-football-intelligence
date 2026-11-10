import type { ApiErrorBody, SeasonBounds, TeamListResponse, TeamStatsResponse } from "@/lib/types";

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

export function fetchSeasons(): Promise<SeasonBounds> {
  return getJson<SeasonBounds>("/seasons");
}

export function fetchTeams(season: number): Promise<TeamListResponse> {
  return getJson<TeamListResponse>(`/teams?season=${season}`);
}

export function fetchTeamStats(teamId: number, season: number): Promise<TeamStatsResponse> {
  return getJson<TeamStatsResponse>(`/teams/${teamId}/stats?season=${season}`);
}
