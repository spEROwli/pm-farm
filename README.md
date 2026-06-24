# PM Farm

A personal automation I built during my job search: a daily scraper that pulls
Product-Manager-track openings directly from companies' hiring APIs, filters them
to my target profile, and publishes a triage-ready dashboard — refreshed every morning
without me touching it.

**[Live dashboard →](https://sperowli.github.io/pm-farm/pm_roles.html)**

> Built entirely with Claude Code — used as a daily force multiplier, not a novelty. I'm a PM
> candidate, not a software engineer. I defined the problem, wrote the requirements and filtering
> rules (see [`SCRAPER_RULES.md`](SCRAPER_RULES.md)), iterated on the logic based on what the
> data showed, and have opened this dashboard every morning since it shipped.

---

## Why I built this

Most job-search tools re-sell listings that are 2–3 days stale, charge for API
access, or require scraping fragile HTML. The three dominant ATS platforms —
Greenhouse, Ashby, and Lever — all expose live JSON APIs with no auth required.
So I cut the middleman: fetch directly, filter precisely, publish automatically.

The result is a single self-updating page I open each morning instead of cycling
through a dozen career sites.

## What it does

- **Pulls from live sources** — company ATS APIs (Greenhouse, Ashby, Lever, Workable)
  with no auth required, plus hiring.cafe via Bright Data Web Unlocker for companies not
  on those ATS platforms. Every role on the live dashboard was returned by a real API or
  live scrape call that morning — no stale caches, no re-sold listings.
- **Filters to a tight target profile:** Product Manager and Associate Product
  Manager only, NYC + SF + US-remote. Executive-layer titles (Director, VP, Head,
  Lead, Principal) are dropped at scrape time; "Senior" is kept since companies
  often use it as a default prefix with no actual seniority bar.
- **Enforces freshness:** anything posted more than 72 hours ago is removed —
  PM hiring moves fast, and a stale listing is a dead one.
- **De-duplicates** by normalized URL, by company+title, and across aggregator
  name variants (e.g. "JPMorganChase" vs "JPMorgan Chase Bank, N.A.").
- **Runs itself** via GitHub Actions at 7:30am ET daily and commits the updated
  dashboard — zero maintenance once deployed.

## Architecture

```
verified_companies.json     ~95 company ATS slugs
         │
         ▼
pmfarm.py ── parallel ThreadPoolExecutor
    ├── Greenhouse  boards-api.greenhouse.io/v1/boards/{slug}/jobs
    ├── Ashby       api.ashbyhq.com/posting-api/job-board/{slug}
    ├── Lever       api.lever.co/v0/postings/{slug}?mode=json
    ├── Workable    apply.workable.com/api/v3/accounts/{slug}/jobs
    ├── The Muse    themuse.com/api/public/jobs
    └── hiring.cafe via Bright Data Web Unlocker
         │
         ▼
filter: title (PM/APM only) · experience bar (regex from JD) · 72h freshness · location
         │
         ▼
dedupe: normalized URL + company|title + aggregator name-variants + applied log
         │
         ├── pm_roles.csv  →  build_page.py  →  pm_roles.html   (the dashboard)
         │
         └── companies.db  (self-cleaning: slugs that return nothing are pruned)
```

GitHub Actions workflow (`.github/workflows/daily-scrape.yml`) runs the full
chain and commits the outputs back to `main` each morning.

## Key engineering decisions

**Direct ATS access as the backbone, search APIs for breadth.** The curated
~95 companies are hit directly through their public Greenhouse/Ashby/Lever/Workable
JSON (no auth, typically <100ms/request) — those are the companies I most want to
work at. Adzuna, The Muse, and hiring.cafe then widen coverage to any company
posting a matching role, so the list isn't capped at the curated set. Everything
flows through the same title/experience/freshness gate, so a role from a search
API is held to the exact same bar as a direct ATS hit.

**Pure standard library.** `urllib`, `csv`, `sqlite3`, `re`, `ThreadPoolExecutor`
— no requests, no BeautifulSoup, no pandas. Zero third-party dependencies.
Fast to install, zero dependency drift.

**Data fidelity over convenience.** Every field on the dashboard reflects exactly
what the ATS returned. Blank experience field = the JD didn't state one. The
scraper never guesses or fills in. See [`SCRAPER_RULES.md`](SCRAPER_RULES.md).

**Self-healing company list.** `discover.py` seeds new ATS slugs from three sources:
YC's public company directory (default), Forbes Cloud 100 (`--from-forbes`, parses
`__NEXT_DATA__` JSON from the Next.js list page), and the a16z portfolio
(`--from-a16z`, static fetch with Bright Data JS-render fallback). Each discovered
company is probed against Greenhouse/Ashby/Lever and promoted to
`verified_companies.json` with a `source` tag — no API key needed for direct ATS
hits on future runs. `companies.db` tracks hit rates per slug; ones that return
nothing across several runs are pruned automatically.

## Running it

```bash
python3 pmfarm.py         # scrape → pm_roles.csv
python3 build_page.py     # render → pm_roles.html
```

Automated runs are handled by GitHub Actions
([`.github/workflows/daily-scrape.yml`](.github/workflows/daily-scrape.yml)) —
it runs the full pipeline at 7:30am ET daily and commits the refreshed dashboard,
so the live page stays current with no machine of mine needing to be on.

## Configuration

Tune at the top of `pmfarm.py`:

| Variable | Default | Effect |
|---|---|---|
| `MAX_AGE_DAYS` | `3` | Drop postings older than this (72h freshness rule) |
| `EXPERIENCE_CAP` | `3` | Max years required experience to keep |
| `TITLE_MUST_INCLUDE` | PM / APM | Which role titles qualify |
| `NYC_LOCS / SF_LOCS` | see file | Target geographies |
| `SOURCES` | all on | Toggle each source |

The company list lives in `verified_companies.json` (committed) and `companies.db`
(local, self-cleaning). Run `python3 discover.py` to seed new companies.

## Tests

```bash
python3 -m pytest test_pmfarm.py -v
```

12 test groups (105 assertions) covering title/seniority filtering,
deduplication, location classification, experience parsing, and output rendering.

## Data sources

| Source | Endpoint | Auth |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io` | none |
| Ashby | `api.ashbyhq.com` | none |
| Lever | `api.lever.co` | none |
| Workable | `apply.workable.com` | none |
| The Muse | `themuse.com/api` | none |
| hiring.cafe | via Bright Data Web Unlocker | API key (GitHub secret) |

## Stack

Python 3.11+ · standard library · GitHub Actions · SQLite · static HTML

## License

[MIT](LICENSE)
