# PM Farm

PM Farm is a self-updating job-search triage tool I built during my Product Manager transition. It pulls PM and APM openings from company ATS APIs and targeted startup job sources, filters them to my target profile, and publishes a dashboard I use each morning.

**[Live dashboard](https://sperowli.github.io/pm-farm/pm_roles.html)**

> Built with Claude Code as an execution layer. I owned the problem definition, requirements, filtering rules, acceptance criteria, iteration loop, and daily usage. The repo is meant to show product judgment, not software-engineering theater.

---

## Problem and product arc

Most job-search tools optimize for volume. I needed signal: fresh Product Manager roles in NYC, San Francisco, or U.S. remote that were worth acting on today.

The useful product was not another job database. It was a daily triage surface. That reframe changed the design priorities: freshness over breadth, filtering before display, source fidelity over inferred data, and zero recurring maintenance.

The core insight was practical. Greenhouse, Ashby, Lever, and Workable expose live job data through public endpoints for many companies. That made a focused point solution possible: fetch directly where possible, supplement with targeted startup sources, apply tight rules, and publish automatically.

What shipped: a static dashboard refreshed by GitHub Actions every morning at 7:30 AM ET. It surfaces PM and APM roles posted within the last 72 hours and requires no manual maintenance after deployment.

---

## What it does

- Pulls live openings from company ATS APIs: Greenhouse, Ashby, Lever, and Workable.
- Supplements direct ATS coverage with targeted startup job sources: YC Jobs, Wellfound, hiring.cafe, and The Muse.
- Filters to PM and APM titles in NYC, San Francisco, and U.S. remote, posted within the last 72 hours.
- Drops executive-layer titles at scrape time, including Director, VP, Head, Lead, and Principal.
- Deduplicates across source URL, company and title, and known company-name variants.
- Runs through GitHub Actions and commits the refreshed dashboard automatically.

---

## Product decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Design for daily triage | Build a broad job database | The user need was not more listings. It was a short list of roles worth acting on today. |
| Use direct ATS APIs as the backbone | Rely on LinkedIn, Indeed, or scraped search results | Direct ATS APIs are closer to the source of truth and reduce stale, duplicated, or resold listings. |
| Add targeted startup sources | Only query known company slugs | Early-stage companies often recruit through YC Jobs, Wellfound, and startup job boards rather than a traditional public ATS slug. |
| Enforce a 72-hour freshness cutoff | No cutoff; 7-day window | PM hiring moves fast. Older roles are less likely to produce immediate traction. |
| Filter seniority before display | Let the dashboard user sort through everything | Noise should not reach the dashboard. Obvious mismatches are removed before they enter the output. |
| Keep "Senior PM" titles | Drop Senior along with executive titles | Companies often use Senior as a default prefix. Dropping it would remove roles that may still fit. |
| Preserve source data exactly | Infer missing experience, salary, or location fields | Blank fields stay blank. The tool should not invent data to make the dashboard look more complete. |
| Ship as static HTML | Build a full web app | A static page solved the actual problem with lower maintenance, faster loading, and no hosted backend. |

---

## PM skills demonstrated

- **Problem framing:** Converted a messy job-search workflow into a specific daily decision problem.
- **Product judgment:** Chose a narrow tool that solved one real workflow instead of building a generic job-search platform.
- **Requirements authorship:** Wrote filtering and data-quality rules in [SCRAPER_RULES.md](SCRAPER_RULES.md) with enough precision to drive implementation.
- **Scope discipline:** Explicitly avoided employer profiles, application tracking, salary inference, and other features that would add maintenance without improving daily triage.
- **AI-assisted execution:** Used Claude Code to move faster while retaining ownership of the requirements, constraints, product logic, and acceptance criteria.
- **Production learning:** Early runs exposed failure modes around inferred data and noisy matches. Those failures became stricter source-fidelity and filtering rules.
- **Shipped behavior:** The product runs automatically and is part of my actual job-search workflow, not just a portfolio artifact.

---

## For developers

<details>
<summary>Architecture, setup, and tests</summary>

### Architecture

```
verified_companies.json     company ATS slugs
         |
         v
pmfarm.py -- parallel ThreadPoolExecutor
    |-- Greenhouse  boards-api.greenhouse.io/v1/boards/{slug}/jobs
    |-- Ashby       api.ashbyhq.com/posting-api/job-board/{slug}
    |-- Lever       api.lever.co/v0/postings/{slug}?mode=json
    |-- Workable    apply.workable.com/api/v3/accounts/{slug}/jobs
    |-- The Muse    themuse.com/api/public/jobs
    |-- hiring.cafe via Bright Data Web Unlocker
    |-- YC Jobs     ycombinator.com/jobs/role/product-manager via Web Unlocker
    |-- Wellfound   wellfound.com/role/l/product-manager/{geo} via Web Unlocker
         |
         v
filter: title, seniority, freshness, location, experience bar
         |
         v
dedupe: normalized URL + company/title + name variants + applied log
         |
         |-- pm_roles.csv  ->  build_page.py  ->  pm_roles.html
         |
         |-- companies.db
```

GitHub Actions (`.github/workflows/daily-scrape.yml`) runs the full chain and commits the refreshed output back to `main` each morning.

### Running locally

```bash
python3 pmfarm.py                    # scrape -> pm_roles.csv
python3 build_page.py                # render -> pm_roles.html
python3 add_company.py "Acme Corp"   # probe a company and add to verified_companies.json
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
| hiring.cafe | via Bright Data Web Unlocker | API key, GitHub secret |
| YC Jobs | `ycombinator.com/jobs` via Bright Data Web Unlocker | API key, GitHub secret |
| Wellfound | `wellfound.com/role/l` via Bright Data Web Unlocker | API key, GitHub secret |

### Stack

Python 3.11+ · standard library · GitHub Actions · SQLite · static HTML

### Next steps

- Expand to Workday and SmartRecruiters, which require a different approach because their access patterns are less open.
- Add company-stage filters for Seed, Series A, and Series B roles.
- Improve location parsing for hybrid roles with ambiguous city language.

</details>

---

[MIT](LICENSE)
