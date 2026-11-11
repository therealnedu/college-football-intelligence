# Free technology assessment

Researched live on 2026-11-10. Prices and limits below are what those pages said that day. They move. Re-read the linked page before relying on a number in an interview.

The budget rule for this project is $0 and no service that asks for payment information. "Free tier" that requires a card is out until the owner sees a signup screen that does not ask for one.

## Football data

**Choice: CollegeFootballData.com.** No other dataset was substituted.

| Fact | Source, accessed 2026-11-10 |
| --- | --- |
| Free key, no credit card, sent to an email address | https://collegefootballdata.com/key |
| Free tier: 1,000 API calls per month. Academic: 3,000, also $0. Paid tiers start at $1/month. Over the limit, HTTP 429 until the 1st | https://collegefootballdata.com/api-tiers |
| Auth header: `Authorization: Bearer <key>`. Keep the key out of source and out of the browser | https://api.collegefootballdata.com/authentication |
| Base URL `https://api.collegefootballdata.com` | https://api.collegefootballdata.com/getting-started |
| Terms effective 2026-08-12, Rad Sports Analytics LLC. Commercial use is allowed and does not change the quota. Private cache and display of a reasonable portion are allowed. A raw feed, public mirror, substitute API, or programmatic access to stored raw responses is not. Do not present the data as official NCAA, conference, or school data. Attribution is appreciated, not required. No SLA | https://collegefootballdata.com/terms |
| Team and player box scores, including season team stats: 2004 through the present. The current season can be incomplete. Their page says coverage was last verified 2026-09-03 | https://api.collegefootballdata.com/data-availability |
| Account usage, including `remainingCalls`, is `GET /info`. This client does not call it, because that would spend a call to learn about calls | https://api.collegefootballdata.com/api/info |

Path check, unauthenticated, 2026-11-10. No stat payload was returned.

| Request | HTTP | Meaning |
| --- | --- | --- |
| `GET /teams?year=2024` | 401 | The route exists and requires a key |
| `GET /stats/season?year=2024&team=Michigan` | 401 | The route exists and requires a key |
| `GET /stats/team/season?year=2024&team=Michigan` | 404 | Not a route. The client does not use it |

The stats reference (https://api.collegefootballdata.com/api/stats) describes team statistics aggregated by season with `year`, `team`, `conference`, `startWeek`, `endWeek`, and `classification`, and a `TeamStat` of `season`, `team`, `conference`, `statName`, `statValue`. The team reference (https://api.collegefootballdata.com/api/teams) shows `id`, `school`, `mascot`, `abbreviation`, `conference`, `classification`, colors, `logos`, and `location`. Logos and location are dropped on ingest.

A successful 200 body was not retrieved. The normalizer matches the documented shape and is tested with synthetic fixtures. If a live body is not a list, the API returns `UPSTREAM_INVALID` instead of inventing rows.

Betting lines are in the provider's catalog. CFIP does not call those routes.

## Frontend hosting

The UI is a Next.js app. It does not run the Python API.

| Option | What the page said | Fit |
| --- | --- | --- |
| Cloudflare Pages Free | 500 builds/month, 1 build at a time, 20 minute build timeout, 20,000 files, 25 MiB per file, 100 projects. Page updated 2026-09-05. https://developers.cloudflare.com/pages/platform/limits/ | Best $0 home for the UI |
| Vercel Hobby | $0, personal and non-commercial. Included usage includes 100 GB fast data transfer and 1,000,000 CDN requests. https://vercel.com/docs/plans/hobby | Fine for a personal portfolio if the owner accepts the non-commercial clause. It does not host this FastAPI process |
| GitHub Pages | Published site up to 1 GB, soft bandwidth 100 GB/month, not for a commercial SaaS. https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits | Static only. Usable if the UI is exported and the API is elsewhere |

## Backend hosting

Do not assume a frontend host runs a persistent Python process. This API is a long-running FastAPI app with a database file or a database server.

| Option | What was read on 2026-11-10 | Fit under the $0 / no-card rule |
| --- | --- | --- |
| Render free web service | Spins down after 15 minutes without inbound traffic and takes about a minute to wake. Filesystem is ephemeral, so a SQLite file is lost on spin-down, restart, or redeploy. 750 free instance hours per workspace per month. Free Postgres expires 30 days after creation. https://render.com/docs/free | Usable for a public demo only with an external database. Cold start is part of the demo, not a defect to hide |
| Neon Free | No credit card. 100 projects, 100 CU-hours per project per month, 1 GB storage per project, scale to zero after 5 idle minutes, data kept when compute sleeps. Compute suspends until the next period if the CU-hour or transfer cap is hit. https://neon.com/pricing and https://neon.com/faqs/free-plan-limits-and-quotas | Best $0 place for the cache to survive a Render sleep |
| Supabase Free | $0, 500 MB database, projects pause after about a week of low activity and must be resumed. https://supabase.com/pricing and https://supabase.com/docs/guides/platform/free-project-pausing | Worse for a link that sits quiet between interviews |
| PythonAnywhere free | 100 CPU seconds, 512 MiB disk, one web app with a one-month expiry. Accounts created after 2026-01-15 do not list the older MySQL and scheduled-task extras. https://help.pythonanywhere.com/pages/FreeAccountsFeatures/ | Not a durable demo |
| Oracle Always Free | Up to two AMD micro VMs and, for Always Free tenancies, Ampere A1 equivalent to 2 OCPUs and 12 GB. Idle instances can be reclaimed when, over 7 days, CPU and network stay under 20 percent (and memory under 20 percent on A1). https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm | Real persistent compute. The retrieved page did not say whether signup asks for a card. It is not the recommendation until the owner confirms signup needs no payment method |
| Fly.io | Their Python hosting article says the monthly free allowance was removed for new customers in October 2024. https://fly.io/learn/python-hosting | Not a $0 plan for a new account |
| Railway | Search results on 2026-11-10 described a small monthly credit, not a month of always-on compute. Not used, because the primary pricing page was not the source of a durable free tier | Not recommended |

## What has to run locally

- The verified setup: API on port 43124 and UI on port 43123, SQLite on disk.
- The live smoke test, after a key exists.
- Any later Ollama model. A public URL will not include a local model unless the owner's machine is on and tunneled, which is a poor demo.

## LLM inference, for phases 3 and 4

Nothing in phase 1 calls a model. This section is a decision input, not a result.

**Default when a model is added: Ollama on the owner's machine, cloud features off.**

| Fact | Source, accessed 2026-11-10 |
| --- | --- |
| Quickstart model `gemma4:e2b`. Download about 7.2 GB. They recommend 8 GB of available VRAM, or unified memory on a Mac. Less VRAM can use system RAM, and responses may be slower. No API key for the local path | https://docs.ollama.com/quickstart |
| Local runs: Ollama does not see prompts. Cloud-hosted models are a different path and do process prompts. `OLLAMA_NO_CLOUD=1` disables cloud features | https://docs.ollama.com/faq |
| Default context 4096 tokens. Agent-style tasks are described as needing at least 64000, which uses more memory. Below 24 GiB VRAM, the default context length they document is 4k | https://docs.ollama.com/context-length and https://docs.ollama.com/faq |
| NVIDIA compute capability 5.0+ . Windows install needs at least 4 GB for the binary, plus model storage that can be tens to hundreds of GB | https://docs.ollama.com/gpu and https://docs.ollama.com/windows |

The owner needs to report RAM, GPU or unified memory, and free disk before a model is chosen. A 70B model is not the plan. The quickstart's small model is the plan if the machine has about 8 GB of VRAM or unified memory. CPU-only is a fallback with slower answers, not a second product.

**Hosted free inference was not selected.**

Groq's plans page lists a Free plan at $0 ("Build and Test") and a Developer plan that needs a payment method to upgrade. https://console.groq.com/settings/billing/plans

The rate-limit page retrieved the same day showed a table and captioned it as base limits for the **Developer** plan, including `openai/gpt-oss-20b` and `openai/gpt-oss-120b` at 30 requests/minute, 1,000 requests/day, 8,000 tokens/minute, and 200,000 tokens/day. https://console.groq.com/docs/rate-limits

Those figures are not recorded here as the Free plan. The page said exact limits are on the account limits screen and that the table can have exceptions. A hosted model also sends prompts off the machine, which fights the reason to ground answers in our database. Revisit Groq only after the owner reads the Free tab in their own account and accepts the data leaving the laptop.

Google's Gemini free tier was not opened on a primary pricing page in this run, so it is not a recommendation.

## Recommended public demo

Decision on 2026-11-11: the public link is a **GitHub Pages static snapshot of this same repository**. It needs no new account and no card. The workflow is `.github/workflows/pages.yml`. The expected URL is https://therealnedu.github.io/college-football-intelligence/ . That URL is not a verified deployment until Pages is set to GitHub Actions and the workflow runs on `main`.

The snapshot is one season. Live builds call the provider about three times and then the page is static, so visitors do not spend the 1,000-call month. Without the `CFBD_API_KEY` secret, the page is the labeled fixture snapshot.

1. **Interviews and daily use:** run both processes locally. SQLite persists. The key stays in `.env`.
2. **The public link:** GitHub Pages, as above. No separate frontend host, API host, or database account.
3. **Optional, not set up:** Cloudflare Pages for a UI, Render's free web service for FastAPI, and Neon Free for Postgres, as assessed below. That path needs extra accounts. Expect a cold start of about a minute after 15 idle minutes. Do not commit a database file of provider rows. Put `CFBD_API_KEY` in the API host's environment, not in the static site. Render's own free-tier page says not to use free instances for production. This combination was not deployed.
