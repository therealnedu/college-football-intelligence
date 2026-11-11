# Portfolio value

This slice is for Chinedu Onyemaobi, a senior PM / TPM candidate, to walk through in an interview or on LinkedIn. The phase 1 code and these documents were produced by a Cursor cloud agent under his direction. He should present the decisions, the scope cuts, and the verification gaps. He should not present the repository as code he typed line by line.

## What a hiring manager can see

**Problem framing.** The user is an analyst who needs one sourced season line. The product is not "an AI platform for college football." Phase 1 refuses comparison, predictions, and betting so the first release has an exit test: select a team, read stored stats, see who provided them and when.

**Scope and sequencing.** The backlog stories have acceptance checks that do not require a made-up benchmark. The roadmap's phase 1 exit criterion that is still open is named: the live provider smoke test. Later AI work is specified with an evaluation set before a model is chosen, which is the AI PM habit of defining "good" before the demo.

**Constraints as product work.** The $0 rule, the provider's terms, and the 1,000-call month changed the design. The cache, the refusal to store raw responses, the separate fixture source, and the hosting note about Render's disk are those constraints showing up in the system. A TPM who can point at a terms clause and a table is doing the job.

**Architecture in plain language.** The browser never holds the key. The API normalizes and caches. The UI is replaceable. SQLite is the local database because it needs no account. Postgres is a URL change that has not been tested, and the document says so.

**Measurement.** Request duration is logged. Cache hits are a field, not a hope. The refresh log is the audit. The live smoke test, when the owner runs it, checks shape and cache behavior and does not lock the build to a particular yardage number. Phase 3's success metric is a citation count from a run.

**Risk and honesty.** The risk register includes the missing key, quota, host sleep, and the chance someone quotes fixture numbers. The technology assessment distinguishes pages that were opened from limits that were only discussed second-hand. Groq's retrieved rate table is labeled as the Developer plan because that is what the page said.

## What this does not demonstrate yet

- A live CollegeFootballData.com response. The client and the ingest path are tested with synthetic recorded responses. `pytest -m live` was not run. No key was available.
- A verified public URL. The Pages workflow is in the repo. The expected address is https://therealnedu.github.io/college-football-intelligence/ . It was not opened, because the workflow runs from `main` and Pages has to be enabled by the owner.
- Comparison, grounded answers, or an agent. Not built. No model is called.
- Production traffic, on-call, or a team operating the system.
- The owner's personal drafting or coding of this repository. Product direction is his. The code was written by an AI coding agent under that direction.

## How to talk about it

1. Start with the analyst and the missing provenance, not with the stack.
2. Show the terms decision: private cache and display, no raw proxy, no logos, no betting routes.
3. Show the cache as the answer to a 1,000-call budget.
4. Say clearly that the screen in fixture mode is a labeled synthetic review, and that the live path is implemented and untested until `pytest -m live` passes on his key.
5. For the public link, say it is a static snapshot. Without the secret it is fixture data. With the secret it is one season from CollegeFootballData.com, rebuilt on a schedule, and the browser does not hold the key.
6. Close with the steps still in front of him: enable Pages, add the key as `CFBD_API_KEY`, and, later, the RAM on the machine that would run Ollama. Those are in the README.

That sequence is the senior TPM signal: outcome, constraint, tradeoff, evidence, and the decision still in front of the owner.
