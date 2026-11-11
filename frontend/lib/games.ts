import type { Game } from "@/lib/types";

/** A missing score stays blank. It is not rendered as zero. */
export function pointsText(points: number | null): string {
  if (points === null) return "—";
  return String(points);
}

export function statusText(status: string | null): string {
  if (status === "final") return "Final";
  if (status === "scheduled") return "Scheduled";
  if (status === "in_progress") return "In progress";
  if (status === "cancelled") return "Cancelled";
  if (status === "postponed") return "Postponed";
  return "Status not stored";
}

export function matchupText(game: Game): string {
  const place = game.neutralSite ? "vs" : "at";
  return `${game.awaySchool} ${pointsText(game.awayPoints)} ${place} ${game.homeSchool} ${pointsText(game.homePoints)}`;
}

export function gamesForTeam(games: Game[], team: { id: number; school: string }): Game[] {
  const school = team.school.trim().toLowerCase();
  return games
    .filter((game) => {
      if (game.homeTeamId === team.id || game.awayTeamId === team.id) return true;
      return game.homeSchool.toLowerCase() === school || game.awaySchool.toLowerCase() === school;
    })
    .slice()
    .sort((left, right) => {
      const byWeek = (left.week ?? 999) - (right.week ?? 999);
      if (byWeek !== 0) return byWeek;
      return (left.startAt ?? "").localeCompare(right.startAt ?? "");
    });
}
