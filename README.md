# PM Farm

PM Farm is a job-search intelligence pipeline that pulls Product Manager and Associate Product Manager roles from live hiring APIs, filters them to a focused target profile, and publishes a triage-ready dashboard for daily review.

**[Live dashboard](https://sperowli.github.io/pm-farm/pm_roles.html)** · **[Case study](CASE_STUDY.md)**

---

## What it does

- Pulls roles from five keyless hiring APIs: Greenhouse, Ashby, Lever, Workable, and The Muse.
- Adds hiring.cafe, YC Jobs, and Wellfound when a Bright Data key is configured. Without a key they stay inert and cost nothing, so the public dashboard runs on the five above.
- Filters to PM and APM roles in New York City, San Francisco, and U.S. remote.
- Prioritizes recent postings.
- Removes obvious seniority mismatches.
- Deduplicates repeated listings.
- Publishes a static dashboard through GitHub Pages.
- Runs automatically through GitHub Actions.

---

## Design choices

| Choice | Reason |
|---|---|
| Narrow role scope | Keeps the dashboard focused. |
| Freshness filter | Recent postings are more useful for daily review. |
| Source fidelity | The tool does not invent missing job details. |
| Static dashboard | Fast to host and maintain. |
| Documented rules | Filtering behavior is explicit in [SCRAPER_RULES.md](SCRAPER_RULES.md). |

---

## For developers

<details>
<summary>Architecture, setup, configuration, sources, and tests</summary>

### Architecture

```
verified_companies.json
         |
         v
pmfarm.py -- source fetchers, filters, dedupe
         |
         '-- pm_roles.csv -> build_page.py -> pm_roles.html
```

GitHub Actions (`.github/workflows/daily-scrape.yml`) runs the pipeline and commits the refreshed output back to `main`.

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
| `TITLE_MUST_INCLUDE` | PM / APM | Which role titles qualify; an optional `titles_local.txt` can replace this list for flexibility to adapt to other role titles |
| `NYC_LOCS / SF_LOCS` | see file | Target geographies |
| `SOURCES` | all on | Toggle each source |

### Tests

```bash
python3 test_pmfarm.py
```

13 test groups cover title and seniority filtering, deduplication, location classification, experience parsing, Bright Data HTML parsing, and output rendering.

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

The three Bright Data sources skip themselves and log `inert` when no key is present, so a keyless run is a clean five-source run rather than a failure. Adzuna is not a listing source: `discover.py --from-adzuna` uses it to seed company names, which are then scraped directly from their own ATS.

### Stack

Python 3.11+ · standard library · GitHub Actions · GitHub Pages · static HTML

### Version 1 Status

This version is feature-complete as a daily PM/APM triage board. Additional filtering, tagging, or digest features are out of scope for this portfolio demonstration.

</details>

---

[MIT](LICENSE)
