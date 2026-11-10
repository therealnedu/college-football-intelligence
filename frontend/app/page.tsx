import { TeamLedger } from "@/components/team-ledger";

export default function HomePage() {
  return (
    <main>
      <TeamLedger />
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs leading-relaxed text-muted-foreground sm:px-6">
        CFIP phase 1 stores a normalized team ledger. School names identify the subject of a row. They are
        not a claim of affiliation, and team logos are not stored. In live mode, figures come from
        CollegeFootballData.com and are not official NCAA, conference, or school statistics. In fixture
        mode, the numbers were written for review and are not football statistics.
      </footer>
    </main>
  );
}
