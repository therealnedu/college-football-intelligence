# Synthetic fixtures

These JSON files are **not** recordings of CollegeFootballData.com and they are **not** college football statistics.

They exist so unit tests, API tests, and a local UI review can run when `CFBD_API_KEY` is unset. Every file carries `_fixture` text that includes the exact phrase `NOT REAL COLLEGE FOOTBALL STATISTICS`. The loader refuses a file that omits that phrase.

Do not replace these rows with real provider responses and leave them in git. Caching real responses is allowed on a private server under the provider's terms; publishing them in this repository would be a different act, and this repo does not do it.
