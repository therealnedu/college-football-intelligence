# Product definition

College Football Intelligence Platform (CFIP), phase 1.

Access date for the constraints below: 2026-11-10. Owner: Chinedu Onyemaobi.

## Problem

A football operations analyst who needs one program's season totals still has to assemble them from scattered pages. The number that lands in a meeting often has no record of which provider it came from or when it was fetched. Comparison, scouting narratives, and any later question-answering are unsafe until that first number is attributable.

CFIP's first job is that number: one season, one team, stored by our API, with a source and a timestamp.

## Target users

| User | Need in this phase | Not their need yet |
| --- | --- | --- |
| Football operations analyst or graduate assistant | A sourced season line for one team before a meeting | A prediction, a ranking model, or a betting card |
| Media researcher | The same line, with enough provenance to say where it came from | A bulk export of the provider |
| Product owner (Chinedu) | A portfolio that shows scope, licensing, and sequencing decisions | A claim that he typed the implementation line by line |

The product is not a sportsbook and does not target bettors. Betting lines exist at the data provider. This product does not request them.

## Primary use cases

1. Choose a season and a team. Read that team's season stats, the provider statement, and the fetch time.
2. Open the same team again inside the cache window. The API serves SQLite and does not spend another provider call.
3. Hit a missing key, a rejected key, a rate limit, or an empty stat set, and see a specific failure or empty state instead of a blank page.

## MVP scope

In this phase:

- Server-side access to CollegeFootballData.com, with the key only in the environment.
- A normalized store of teams and season team stats, plus a refresh log.
- A web ledger: season, team, stats, chart of stored yardage when those values are numeric, source, timestamp.
- Loading, empty, and error states.
- A fixture mode whose files say `NOT REAL COLLEGE FOOTBALL STATISTICS`, so the UI can be reviewed without a key and without pretending the numbers are real.

Out of this phase:

- Two-team comparison, charts as an analysis product, and saved matchup notes.
- Natural-language questions, scouting reports, and an evaluation set.
- Tool-calling agents and execution metrics.
- Public deployment, authentication, and a security review.
- Player stats, recruiting, ratings, weather, and betting lines.
- Logos. The provider's terms do not grant trademark or logo rights, so logos are dropped during normalization.

## Business value

There is no revenue target. The value of phase 1 is a trustworthy stat line and a quota-aware way to refresh it.

- The analyst's outcome is time-to-a-sourced-number, not a model score. Phase 1 is done for a team when the screen shows stored stats, a provider statement, and `fetchedAt`.
- The free provider tier is 1,000 calls per month. Caching is a product requirement. A public page that refetches on every view would spend the month's quota.
- The refresh log is the audit trail: what was requested, whether it succeeded, how many rows were written, and any rate-limit header the provider sent.
- Later phases (comparison, grounded answers, an agent) sit on this ledger. They are not valuable if the ledger can be confused with invented numbers or with a raw copy of the provider.

## What "real" means here

Live mode is implemented. It was not executed in this environment, because `CFBD_API_KEY` was not set. Fixture mode was executed. Fixture rows are synthetic. See the README verification section before describing any figure as a college football statistic.
