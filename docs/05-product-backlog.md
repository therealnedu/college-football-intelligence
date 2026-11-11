# Product backlog

Ordered for the roadmap in `docs/06-roadmap.md`. Identifiers are stable. Acceptance is written so a later phase can be tested without inventing a statistic.

Priority is top to bottom inside each epic. Phase 1 stories are implemented except the live-provider check, which is blocked on a key.

On 2026-11-11 epic E6 was pulled in front of comparison. E2, E3, and E4 are not implemented. E6's workflow is in the repo. Its public URL is not verified, and its live provider run is still blocked on a key.

## E1. Attributable team ledger

### E1-S1. Select a season and see teams

As an analyst, I choose a season and see the teams stored for it, so I can pick a program without guessing the spelling.

Acceptance:

- `GET /seasons` returns the minimum 2004, the maximum as the current UTC year, and the default as the previous calendar year.
- `GET /teams?season=` returns schools sorted by name for that season.
- A season before 2004 or after the maximum returns `SEASON_OUT_OF_RANGE`.
- A missing season parameter returns `VALIDATION_ERROR`.

### E1-S2. Read one team's season stats with provenance

As an analyst, I open one team and see each stored stat as text, plus a numeric value only when the token is a finite number, so a clock is not treated as a yardage total.

Acceptance:

- `GET /teams/{id}/stats?season=` returns `name`, `valueText`, and `valueNumeric`.
- `valueText` for an input token `1,234` stays `1,234`, and `valueNumeric` is 1234.
- A token such as `99:99` has a null `valueNumeric`.
- The response includes `fetchedAt`, a provider name, and a statement.
- Live responses name CollegeFootballData.com and say the figures are not official NCAA, conference, or school statistics.
- Fixture responses name `CFIP synthetic fixture` and include `NOT REAL COLLEGE FOOTBALL STATISTICS`.
- The JSON does not include `logos`, `twitter`, or the upstream key `statValue`.
- An unknown id returns `TEAM_NOT_FOUND`.
- A known team with no stat rows returns 200 and an empty `stats` array.

### E1-S3. Do not spend a second provider call inside the cache window

As the owner of a 1,000-call monthly key, I can reopen the same season and team and not consume another call.

Acceptance:

- The second `GET /teams?season=` for a fresh success sets `cache.hit` to true.
- The second stats request does the same.
- `GET /refresh-status` shows one success row for that team-list refresh, not one row per read.
- A test with a mocked provider counts one teams request and one stats request across those repeats.

### E1-S4. Survive provider timeouts and quota responses

As an analyst, I see a specific error when the provider is down or refuses the key, so I do not refresh the page into a second failure blindly.

Acceptance:

- No key: HTTP 503, code `CFBD_NOT_CONFIGURED`, and a details string that points at the free-key page. The client does not open a connection.
- HTTP 401 from the provider is not retried.
- HTTP 503 is retried with backoff, then succeeds if a later attempt is 200.
- `Retry-After` above 30 seconds fails on the first response with `CFBD_RATE_LIMITED` and does not block the web request for the whole wait.
- Timeouts retry up to `CFBD_MAX_RETRIES` and then return `CFBD_TIMEOUT`.
- The failed attempt is a row on `data_refresh_logs`.

### E1-S5. See loading, empty, and error states

As an analyst, the page tells me whether it is loading, whether the team has no rows, or why the request failed.

Acceptance:

- The team list shows a skeleton while the request is in flight, an empty message when the filter matches nothing, and the API error text on failure.
- A missing key shows the `howTo` text from the API.
- Fixture mode shows a banner that the numbers are not real college football statistics before any chart.

## E6. One-season ingest and a public snapshot

Added 2026-11-11. This is the public-data release. It is not the comparison epic.

### E6-S1. Load one season without duplicating rows

As the owner of a 1,000-call key, I can load teams, games, and season stats for one season in a few calls, and run the load again without a second copy of the rows.

Acceptance:

- A live load requests `GET /teams`, `GET /games`, and `GET /stats/season` once each for that season, unless a fresh success is already inside the cache TTL. `--force` refreshes anyway.
- The games request uses `seasonType=both` and does not request a betting route.
- The stats request does not pass `team`, so one call covers the classification.
- A second forced run updates a changed score and leaves one row per external id.
- A run inside the TTL, without `--force`, makes no provider call.
- Teams outside `CFIP_INGEST_CLASSIFICATION` are not stored on a live load. Fixture schools are not filtered, because they are not FBS.
- Logos, social handles, and betting objects are not stored and are not in the snapshot file.
- A missing score stays null.

### E6-S2. Stay inside a small quota

As the owner, a scheduled refresh does not walk every team and does not ignore a low remaining-quota header.

Acceptance:

- The client pauses between successful provider calls.
- If the remaining-quota header is below `CFIP_INGEST_MIN_REMAINING`, later resources are not requested. The snapshot says the load was partial.
- HTTP 401 is not retried. A `Retry-After` above 30 seconds fails on the first response. Those rules already live on the client.
- CI and the default Pages build do not call the network when `CFBD_API_KEY` is empty.

### E6-S3. Publish a labeled static page

As a visitor with the public link, I can tell whether I am looking at fixture data or CollegeFootballData.com data, and the page works without a Python server.

Acceptance:

- The Pages workflow builds a static export. The browser reads the snapshot. It does not receive the key.
- Fixture snapshots include `NOT REAL COLLEGE FOOTBALL STATISTICS`. A snapshot that omits that label is refused.
- A live snapshot does not carry that label. It names CollegeFootballData.com and says the figures are not official NCAA, conference, or school statistics.
- The page shows the source before a chart. A filter with no match, an empty stat list, and a blank score are visible states.
- The workflow falls back to fixtures when the secret is absent. It does not pretend those rows are live.

The workflow file is in the repo. Enabling GitHub Pages, and adding the key, are owner steps. They are not done in this environment.

## E2. Compare two teams

### E2-S1. Pick two teams in one season

As an analyst, I select two teams and see their stored season stats side by side.

Acceptance:

- Both columns show only stats already stored for that season.
- A stat present for one team and missing for the other is blank on the missing side. It is not filled with zero.
- The page names both `fetchedAt` values.

### E2-S2. Chart a shared stat

As an analyst, I chart one stat name that both teams have as a number.

Acceptance:

- The chart uses `valueNumeric` from stored rows.
- If either side is null, the chart explains that the stat is not numeric for both teams and does not draw a bar for the null side.

### E2-S3. Save a matchup note

As an analyst, I can save a short note on the pair so the comparison survives a refresh.

Acceptance:

- A row is written to `matchup_analyses` for the ordered pair and season.
- The note is labeled as an analyst note, not as a model output.
- Reloading the pair shows the note.

## E3. Grounded questions and scouting reports

### E3-S1. Ask a question that can only be answered from stored rows

As an analyst, I ask which stored yardage figures we have for a team and season, and the answer cites those rows.

Acceptance:

- The answer quotes `stat_name`, `valueText`, and `fetchedAt` for every figure it states.
- If the row is absent, the answer says it is not stored. It does not estimate.
- A fixture-origin row is labeled as a fixture in the answer.
- An evaluation set of at least 25 questions is checked in, with expected citations. A run reports how many answers cited the expected rows. That count is a measured result, not a target written in advance as if it had been achieved.

### E3-S2. Draft a scouting report

As an analyst, I generate a report that only uses stored stats and says so.

Acceptance:

- The report is stored in `scouting_reports` with `grounded` true only if every figure in the body matches a stored `valueText`.
- The model name and prompt version are stored.
- The report is not published as an NCAA or school document.

## E4. Agentic workflow

### E4-S1. Multi-step tool use

As an analyst, I ask for a comparison that requires looking up two teams, and the agent calls the catalog tools rather than answering from memory.

Acceptance:

- Each tool call writes `ai_execution_logs` with agent name, tool name, status, start, finish, and an input hash. The prompt body is not stored.
- A validator checks every figure in the final text against stored rows. `output_validated` is false if any figure does not match.
- A run report states tool-call count, validation pass count, and failure count from that execution log. Those are measured after a run.

## E5. Portfolio release

### E5-S1. Tests, security pass, deploy, and a case study

As the owner, I can point an interviewer at a README, a passing CI run, and a case study that matches what was actually verified.

Acceptance:

- CI runs the backend tests and the frontend tests on every push.
- The security pass checks that the key is not in git, the browser bundle, or logs, and that raw provider bodies are not on the public API.
- The deploy target matches a row in the technology assessment, including its sleep and persistence limits.
- The case study separates implemented, simulated, and planned work, and it does not describe the agent-written code as hand-typed by the owner.

## Explicitly rejected

- Odds, spreads, pick'em, or bankroll features.
- A public endpoint that returns stored raw provider responses.
- Publishing fixture numbers without the fixture label.
