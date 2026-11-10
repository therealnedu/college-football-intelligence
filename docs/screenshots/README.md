# Screenshots

Captured on 2026-11-10 from the local UI at http://127.0.0.1:43123, with the API in fixture mode.

The schools and numbers in these images are the synthetic fixtures in `backend/fixtures`. They are not college football statistics.

| File | What it shows |
| --- | --- |
| `01-fixture-team-list.png` | Season 2025 default, fixture banner, three invented schools |
| `02-fixture-falcons-stats.png` | Stored tokens, including `1,234` and the non-numeric `99:99`, and a yardage chart of those stored numbers. "Served from cache" is from an earlier request in the same process |
| `03-empty-stat-rows.png` | Empty Roster College: the team exists and the stat request stored zero rows |
| `04-mobile-team-list.png` | The same ledger at a 390px width |
| `05-missing-key-error.png` | The error panel. The browser fulfilled the teams request with the JSON the API returns when `CFBD_API_KEY` is missing. The API process was still in fixture mode. The 503 itself was checked by `tests/test_api.py`, not by this picture |
