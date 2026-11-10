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

- A live CollegeFootballData.com response. Not run.
- A public deployment. Not done.
- AI quality. No model is called.
- Production traffic, on-call, or a team operating the system.
- The owner's personal drafting or coding of this repository.

## How to talk about it

1. Start with the analyst and the missing provenance, not with the stack.
2. Show the terms decision: private cache and display, no raw proxy, no logos, no betting routes.
3. Show the cache as the answer to a 1,000-call budget.
4. Say clearly that the screen in fixture mode is a labeled synthetic review, and that the live path is implemented and untested until `pytest -m live` passes on his key.
5. Close with the next decision he needs to make: key, public-repo host, and the RAM on the machine that would run Ollama. Those are in the README.

That sequence is the senior TPM signal: outcome, constraint, tradeoff, evidence, and the decision still in front of the owner.
