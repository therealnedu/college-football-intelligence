"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, fetchSeasons, fetchTeamStats, fetchTeams } from "@/lib/api";
import { chartSeries, displayValue, formatTimestamp, groupStats } from "@/lib/stats";
import type { SeasonBounds, TeamListResponse, TeamStatsResponse } from "@/lib/types";

const StatChart = dynamic(
  () => import("@/components/stat-chart").then((module) => module.StatChart),
  {
    ssr: false,
    loading: () => <Skeleton className="h-64 w-full" />,
  },
);

type LoadState<T> =
  | { status: "loading" }
  | { status: "error"; error: ApiError }
  | { status: "ready"; data: T };

export function TeamLedger() {
  const [bounds, setBounds] = useState<LoadState<SeasonBounds>>({ status: "loading" });
  const [season, setSeason] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [directory, setDirectory] = useState<LoadState<TeamListResponse> | { status: "idle" }>({
    status: "idle",
  });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [stats, setStats] = useState<LoadState<TeamStatsResponse> | { status: "idle" }>({
    status: "idle",
  });

  useEffect(() => {
    const controller = new AbortController();
    fetchSeasons()
      .then((data) => {
        if (controller.signal.aborted) return;
        setBounds({ status: "ready", data });
        setSeason(data.defaultSeason);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setBounds({ status: "error", error: asApiError(error) });
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (season === null) return;
    const controller = new AbortController();
    setDirectory({ status: "loading" });
    setSelectedId(null);
    setStats({ status: "idle" });
    fetchTeams(season)
      .then((data) => {
        if (controller.signal.aborted) return;
        setDirectory({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setDirectory({ status: "error", error: asApiError(error) });
      });
    return () => controller.abort();
  }, [season]);

  useEffect(() => {
    if (season === null || selectedId === null) return;
    const controller = new AbortController();
    setStats({ status: "loading" });
    fetchTeamStats(selectedId, season)
      .then((data) => {
        if (controller.signal.aborted) return;
        setStats({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setStats({ status: "error", error: asApiError(error) });
      });
    return () => controller.abort();
  }, [season, selectedId]);

  const filtered = useMemo(() => {
    const teams = directory.status === "ready" ? directory.data.teams : [];
    const needle = query.trim().toLowerCase();
    if (!needle) return teams;
    return teams.filter((team) =>
      [team.school, team.mascot, team.conference, team.abbreviation]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(needle)),
    );
  }, [directory, query]);

  const notice =
    directory.status === "ready"
      ? directory.data.attribution
      : stats.status === "ready"
        ? stats.data.attribution
        : null;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 lg:py-10">
      <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="grid size-11 shrink-0 place-items-center rounded-lg bg-primary font-heading text-lg text-primary-foreground">
            CF
          </div>
          <div>
            <p className="text-xs tracking-[0.18em] text-muted-foreground uppercase">Phase 1 · Team ledger</p>
            <h1 className="font-heading text-3xl leading-tight text-foreground sm:text-4xl">
              College Football Intelligence
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:text-base">
              Pick a season and one team. The ledger shows that team&apos;s season stats as stored by the
              CFIP API, with the source and the time they were fetched.
            </p>
          </div>
        </div>
        <p className="max-w-xs text-xs text-muted-foreground">
          Not a betting product. No odds, no picks, and no comparison view in this phase.
        </p>
      </header>

      {notice?.dataMode === "fixture" && (
        <div
          role="status"
          className="rounded-xl border border-primary/50 bg-primary/10 px-4 py-3 text-sm text-foreground"
        >
          <p className="font-semibold">Fixture data. Not real college football statistics.</p>
          <p className="mt-1 text-muted-foreground">{notice.fixtureNotice}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Season</CardTitle>
              <CardDescription>Box-score coverage documented from 2004.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {bounds.status === "loading" && <Skeleton className="h-9 w-full" />}
              {bounds.status === "error" && <ErrorPanel error={bounds.error} />}
              {bounds.status === "ready" && season !== null && (
                <>
                  <label className="text-xs text-muted-foreground" htmlFor="season">
                    Season year
                  </label>
                  <select
                    id="season"
                    className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
                    value={season}
                    onChange={(event) => setSeason(Number(event.target.value))}
                  >
                    {seasonOptions(bounds.data).map((year) => (
                      <option key={year} value={year}>
                        {year}
                        {year === bounds.data.defaultSeason ? " · default" : ""}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs leading-relaxed text-muted-foreground">{bounds.data.coverageNote}</p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Team</CardTitle>
              <CardDescription>
                {directory.status === "ready"
                  ? `${directory.data.teams.length} teams stored for ${directory.data.season}.`
                  : "Loaded from the API for the selected season."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <label className="sr-only" htmlFor="team-filter">
                Filter teams
              </label>
              <Input
                id="team-filter"
                placeholder="Filter by school or conference"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                disabled={directory.status !== "ready"}
              />
              {directory.status === "idle" && (
                <p className="text-sm text-muted-foreground">Waiting for the season list.</p>
              )}
              {directory.status === "loading" && (
                <div className="flex flex-col gap-2" aria-busy="true" aria-live="polite">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              )}
              {directory.status === "error" && <ErrorPanel error={directory.error} />}
              {directory.status === "ready" && filtered.length === 0 && (
                <p className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
                  {directory.data.teams.length === 0
                    ? "The API stored no teams for this season."
                    : "No team matches that filter."}
                </p>
              )}
              {directory.status === "ready" && filtered.length > 0 && (
                <ul className="flex max-h-80 flex-col gap-1 overflow-auto" role="listbox" aria-label="Teams">
                  {filtered.map((team) => (
                    <li key={team.id}>
                      <Button
                        type="button"
                        role="option"
                        aria-selected={team.id === selectedId}
                        variant={team.id === selectedId ? "default" : "ghost"}
                        onClick={() => setSelectedId(team.id)}
                        className="h-auto w-full justify-start px-3 py-2 text-left"
                      >
                        <span className="flex flex-col items-start">
                          <span className="font-medium">{team.school}</span>
                          <span
                            className={`text-xs font-normal ${
                              team.id === selectedId ? "text-primary-foreground/80" : "text-muted-foreground"
                            }`}
                          >
                            {[team.conference, team.classification].filter(Boolean).join(" · ") ||
                              "Affiliation not stored"}
                          </span>
                        </span>
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </aside>

        <section aria-live="polite">
          {selectedId === null && directory.status !== "error" && (
            <Card className="min-h-80">
              <CardHeader>
                <CardTitle>Select a team</CardTitle>
                <CardDescription>
                  Season totals appear here after you choose a school. Nothing is fetched from the data
                  provider until the API cache is cold.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  The first request for a season stores the team list. Choosing a team stores that team&apos;s
                  season stats. A repeat within the cache window is served from SQLite and does not spend
                  another provider call.
                </p>
              </CardContent>
            </Card>
          )}
          {stats.status === "loading" && <StatsSkeleton />}
          {stats.status === "error" && (
            <Card>
              <CardHeader>
                <CardTitle>Stats could not be loaded</CardTitle>
              </CardHeader>
              <CardContent>
                <ErrorPanel error={stats.error} />
              </CardContent>
            </Card>
          )}
          {stats.status === "ready" && <StatsPanel response={stats.data} />}
        </section>
      </div>
    </div>
  );
}

function StatsPanel({ response }: { response: TeamStatsResponse }) {
  const groups = groupStats(response.stats);
  const points = chartSeries(response.stats);
  const accent = response.team.color ?? "var(--primary)";

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs tracking-wide text-muted-foreground uppercase">
                {response.season} season
              </p>
              <CardTitle className="font-heading text-3xl">{response.team.school}</CardTitle>
              <CardDescription className="mt-1 text-sm">
                {[response.team.mascot, response.team.conference, response.team.classification]
                  .filter(Boolean)
                  .join(" · ") || "No affiliation stored"}
              </CardDescription>
            </div>
            <span className="inline-block h-8 w-8 rounded-full ring-1 ring-border" style={{ background: accent }} aria-hidden />
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{response.cache.hit ? "Served from cache" : "Fetched and stored"}</Badge>
            <Badge variant="outline">{response.attribution.dataMode === "fixture" ? "Fixture mode" : "Live mode"}</Badge>
          </div>
          <p>{response.attribution.statement}</p>
          <dl className="grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Fetched</dt>
              <dd>{formatTimestamp(response.attribution.fetchedAt)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Provider</dt>
              <dd>
                {response.attribution.providerUrl ? (
                  <a className="underline underline-offset-2" href={response.attribution.providerUrl}>
                    {response.attribution.providerName}
                  </a>
                ) : (
                  response.attribution.providerName
                )}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Yardage</CardTitle>
          <CardDescription>
            Only total, net passing, and rushing yards are charted, and only when a numeric value was stored.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <StatChart points={points} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Season stats</CardTitle>
          <CardDescription>
            {response.stats.length === 0
              ? "No stat rows were stored."
              : `${response.stats.length} stored stat${response.stats.length === 1 ? "" : "s"}. Values are shown as stored, not recalculated.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {response.stats.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border px-3 py-8 text-center text-sm text-muted-foreground">
              This team is in the directory, and the stat request completed, but there were no season stat
              rows to store.
            </p>
          ) : (
            <div className="flex flex-col gap-6">
              {groups.map((group) => (
                <div key={group.label}>
                  <h3 className="mb-2 text-xs tracking-[0.16em] text-muted-foreground uppercase">{group.label}</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[28rem] text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-xs text-muted-foreground">
                          <th className="py-2 pr-3 font-medium">Stat</th>
                          <th className="py-2 pr-3 font-medium">Stored value</th>
                          <th className="py-2 font-medium">Numeric</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.stats.map((stat) => (
                          <tr key={stat.name} className="border-b border-border/70">
                            <td className="py-2 pr-3">{stat.name}</td>
                            <td className="py-2 pr-3 font-medium">{displayValue(stat)}</td>
                            <td className="py-2 text-muted-foreground">
                              {stat.valueNumeric === null ? "Not numeric" : stat.valueNumeric}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <Card aria-busy="true">
      <CardHeader>
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-2/3" />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </CardContent>
    </Card>
  );
}

function ErrorPanel({ error }: { error: ApiError }) {
  const howTo = typeof error.details.howTo === "string" ? error.details.howTo : null;
  return (
    <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-3 text-sm">
      <p className="font-medium">{error.message}</p>
      <p className="mt-1 text-xs text-muted-foreground">Code {error.code}</p>
      {howTo && <p className="mt-2 text-muted-foreground">{howTo}</p>}
    </div>
  );
}

function seasonOptions(bounds: SeasonBounds): number[] {
  const years: number[] = [];
  for (let year = bounds.maxSeason; year >= bounds.minSeason; year -= 1) {
    years.push(year);
  }
  return years;
}

function asApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError("Something went wrong while loading the ledger.", "UNKNOWN", 0, {});
}
