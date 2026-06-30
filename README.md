# PM Farm

A daily scraper built during my job search: pulls Product Manager openings directly from company ATS APIs, filters to a target profile, and publishes a triage-ready dashboard refreshed every morning.

**[Live dashboard](https://sperowli.github.io/pm-farm/pm_roles.html)**

> Built with Claude Code as a daily force multiplier, not a novelty. I am a PM candidate, not a software engineer. I defined the problem, wrote the requirements and filtering rules (see [SCRAPER_RULES.md](SCRAPER_RULES.md)), iterated on the logic based on what the data showed, and have opened this dashboard every morning since it shipped.

---

## Problem and Product Arc

Most job-search tools resell listings that are 2 to 3 days stale, charge for API access, or require scraping fragile HTML. Greenhouse, Ashby, and Lever all expose live JSON APIs with no authentication required. That gap made a point solution feasible: fetch directly, filter precisely, publish automatically.

The reframe that drove the design: this is not a scraper, it is a daily triage tool. That distinction changed what the system needs to optimize for: freshness over breadth, signal over volume, zero maintenance overhead.

What shipped: a self-updating dashboard that runs at 7:30am ET every morning via GitHub Actions, surfaces only PM and APM roles posted within the last 72 hours, and requires no maintenance after deployment. I have used it every workday since.

---

## What it does

- Pulls live openings directly from company ATS APIs (Greenhouse, Ashby, Lever, Workable) and startup job boards (YC Jobs, Wellfound). No third-party aggregators, no resold data.
- Filters to PM and APM titles in NYC, SF, and US remote, posted within 72 hours. Executive-layer titles (Director, VP, Head, Lead, Principal) are dropped at scrape time.
- Deduplicates across sources so the same role from multiple platforms appears once, including name-variant collisions across aggregators.
- Runs itself via GitHub Actions at 7:30am ET daily and commits the refreshed dashboard. Zero maintenance after deployment.

---

## Product decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Direct ATS APIs as the backbone | Third-party aggregators (LinkedIn, Indeed) | Aggregators add latency and resell stale listings. Direct ATS APIs return live data and require no authentication. |
| 72-hour freshness cutoff | No cutoff; 7-day window | PM hiring moves fast. A listing five days old is likely already in late-stage rounds. |
| Drop executive titles at scrape time | Filter in the dashboard after fetch | Removes noise before it enters the data. Director, VP, Head, Lead, and Principal are never relevant targets. |
| Keep "Senior PM" titles | Drop Senior along with executive titles | Companies frequently use "Senior" as a default prefix with no actual seniority bar attached. |
| Zero third-party dependencies | requests, pandas, BeautifulSoup | No dependency drift, no install friction. Standard library only: urllib, csv, sqlite3, re, ThreadPoolExecutor. |
| Blank fields stay blank | Infer or fill missing data | Every field on the dashboard reflects what the ATS returned. The scraper never guesses. Production failures from gap-filling were the forcing function: see [SCRAPER_RULES.md](SCRAPER_RULES.md). |

---

## PM skills demonstrated

- **Problem framing:** Identified a structural gap between stale aggregator data and live ATS APIs, then built a targeted point solution rather than a general-purpose tool.
- **Reframing the product:** Recognized the system I was building was a daily triage tool, not a scraper. That reframe defined what to optimize for.
- **Scope discipline:** Defined what the product does not do as explicitly as what it does. No employer profiles, no application tracking, no salary inference.
- **Requirements authorship:** Wrote filtering and data quality rules in [SCRAPER_RULES.md](SCRAPER_RULES.md) with enough precision that a non-technical collaborator could implement them.
- **Learning from production failures:** Early runs shipped invented roles. SCRAPER_RULES.md exists because I diagnosed the failure mode and encoded the fix as a constraint, not a comment.
- **Shipped and in use:** The system has run in production every weekday since deployment. I use it daily. That is the bar.

---

## For developers

<details>
<summary>Architecture, setup, and tests</summary>

### Architecture

```
verified_companies.json     ~95 company ATS slugs
         |
         v
pmfarm.py -- parallel ThreadPoolExecutor
    |-- Greenhouse  boards-api.greenhouse.io/v1/boards/{slug}/jobs
    |-- Ashby       api.ashbyhq.com/posting-api/job-board/{slug}
    |-- Lever       api.lever.co/v0/postings/{slug}?mode=json
    |-- Workable    apply.workable.com/api/v3/accounts/{slug}/jobs
    |-- The Muse    themuse.com/api/public/jobs
    |-- hiring.cafe via Bright Data Web Unlocker
    |-- YC Jobs     ycombinator.com/jobs/role/product-manager (Web Unlocker)
    |-- Wellfound   wellfound.com/role/l/product-manager/{geo} (Web Unlocker)
         |
         v
filter: title (PM/APM only) · experience bar (regex from JD) · 72h freshness · location
         |
         v
dedupe: normalized URL + company|title + aggregator name-variants + applied log
         |
         |-- pm_roles.csv  ->  build_page.py  ->  pm_roles.html  (the dashboard)
         |
         |-- companies.db  (self-cleaning: slugs that return nothing are pruned)
```

GitHub Actions (`.github/workflows/daily-scrape.yml`) runs the full chain and commits the outputs back to `main` each morning.

### Running locally

```bash
python3 pmfarm.py                    # scrape -> pm_roles.csv
python3 build_page.py                # render -> pm_roles.html
python3 add_company.py "Acme Corp"   # probe a single company and add to verified_companies.json
```

### Configuration

| Variable | Default | Effect |
|---|---|---|
| `MAX_AGE_DAYS` | `3` | Drop postings older than this |
| `EXPERIENCE_CAP` | `3` | Max years required experience to keep |
| `TITLE_MUST_INCLUDE` | PM / APM | Which role titles qualify |
| `NYC_LOCS / SF_LOCS` | see file | Target geographies |
| `SOURCES` | all on | Toggle each source |

### Tests

```bash
python3 -m pytest test_pmfarm.py -v
```

13 test groups covering title and seniority filtering, deduplication, location classification, experience parsing, Bright Data HTML parsing, and output rendering.

### Data sources

| Source | Endpoint | Auth |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io` | none |
| Ashby | `api.ashbyhq.com` | none |
| Lever | `api.lever.co` | none |
| Workable | `apply.workable.com` | none |
| The Muse | `themuse.com/api` | none |
| hiring.cafe | via Bright Data Web Unlocker | API key (GitHub secret) |
| YC Jobs | `ycombinator.com/jobs` via Bright Data Web Unlocker | API key (GitHub secret) |
| Wellfound | `wellfound.com/role/l` via Bright Data Web Unlocker | API key (GitHub secret) |

### Stack

Python 3.11+ · standard library · GitHub Actions · SQLite · static HTML

### Next steps

- Expand to Workday and SmartRecruiters (closed auth; requires a different approach)
- Add series-round filter (Seed, A, B) using Crunchbase or PitchBook data
- Improve location parsing for hybrid roles with ambiguous city language

</details>

---

[MIT](LICENSE)
