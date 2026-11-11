# Synthetic recorded responses

These files are **not** recordings of CollegeFootballData.com. They are handwritten stand-ins shaped like the documented team, game, and season-stat lists, so the ingest tests can run in CI without `CFBD_API_KEY` and without storing a provider payload.

Every file includes `_fixture` text with the phrase `NOT REAL COLLEGE FOOTBALL STATISTICS`. The test loader refuses a file that omits it. Do not replace these bodies with real provider responses.
