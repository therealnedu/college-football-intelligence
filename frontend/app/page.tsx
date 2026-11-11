import { readFileSync } from "node:fs";
import path from "node:path";

import { TeamLedger } from "@/components/team-ledger";
import { parseSnapshot, type SnapshotDocument } from "@/lib/snapshot";

export default function HomePage() {
  const initialSnapshot = loadBuildSnapshot();
  return (
    <main>
      <TeamLedger initialSnapshot={initialSnapshot} />
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs leading-relaxed text-muted-foreground sm:px-6">
        School names identify the subject of a row. They are not a claim of affiliation, and team logos are
        not stored. Live figures, when a CollegeFootballData.com key was used to build the page or to answer
        the API, come from that provider and are not official NCAA, conference, or school statistics. Fixture
        figures were written for review and are not football statistics. This product does not publish odds
        or picks. Comparison, grounded questions, and an agent are not in this release.
      </footer>
    </main>
  );
}

function loadBuildSnapshot(): SnapshotDocument | null {
  if (process.env.NEXT_PUBLIC_DATA_SOURCE !== "snapshot") return null;
  const file = path.join(process.cwd(), "public", "data", "snapshot.json");
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown error";
    throw new Error(
      `Static snapshot build requires ${file}. Run the ingest command before next build. ${message}`,
    );
  }
  return parseSnapshot(raw);
}
