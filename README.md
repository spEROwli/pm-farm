# PM Farm

**A daily job-search intelligence tool for Product Manager roles, built by a PM using Claude Code.**

PM Farm pulls fresh PM and APM openings from eight live hiring sources every
morning, filters them to a focused target profile, removes roles I have already
seen, and publishes a triage-ready dashboard through GitHub Actions.

&nbsp;&nbsp;**[→ Live dashboard](https://sperowli.github.io/pm-farm/pm_roles.html)**
&nbsp;&nbsp;·&nbsp;&nbsp;**[→ Case study](CASE_STUDY.md)**

> I built this with Claude Code as my engineering pair. I am a product manager,
> not a software engineer: I defined the problem, wrote the requirements and
> filtering rules, made the build-versus-reuse and cost trade-offs, and iterated
> against real output every day. Claude Code was the execution layer; the product
> decisions were mine.

---

## What it does

- **Pulls from eight live sources** — the Greenhouse, Ashby, Lever, and Workable
  ATS APIs directly, plus The Muse, YC Jobs, Wellfound, and hiring.cafe. The
  JavaScript-gated sources are reached through the Bright Data Web Unlocker.
- **Filters to a focused profile** — PM and APM roles in New York City, San
  Francisco, and U.S. remote, within a target experience range.
- **Prioritizes freshness** — recent postings first; stale listings are dropped.
- **Deduplicates** by normalized URL, company and title, aggregator name
  variants, and my own application history.
- **Preserves source truth** — the tool never invents a missing job detail. See
  [SCRAPER_RULES.md](SCRAPER_RULES.md).
- **Runs itself** — GitHub Actions scrapes, rebuilds, and republishes daily.

---

## Design choices

| Choice | Reason |
|---|---|
| Direct ATS APIs as the backbone | Clean, direct application links, no auth. |
| Bright Data for gated sources | Reused an existing tool instead of writing fragile scraping code. |
| Filter on stated experience, not title | Titles are noisy; the years requirement is the real signal. |
| Freshness over completeness | Recent roles are the ones worth acting on today. |
| Source fidelity over convenience | A blank field is honest; an invented one is not. |
| Cost as a design constraint | Spend guards and a request cap from the start. |
| Static dashboard | Simple to host, fast to load, nothing to maintain. |

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

GitHub Actions (`.github/workflows/daily-scrape.yml`) runs the pipeline and
commits the refreshed output back to `main`.

### Running locally

```bash
python3 pmfarm.py                    # scrape -> pm_roles.csv
python3 build_page.py                # render -> pm_roles.html
python3 add_company.py "Acme Corp"   # probe a company and add to verified_companies.json
```

The title filter is externally configurable. `TITLE_MUST_INCLUDE` defaults to PM
and APM. Adding an optional `titles_local.txt` (one title fragment per line)
replaces that list for a local run and writes to `pm_roles_wide.csv`, so the
default portfolio output stays untouched.

### Configuration

| Variable | Default | Effect |
|---|---|---|
| `MAX_AGE_DAYS` | `3` | Drop postings older than this |
| `EXPERIENCE_CAP` | `3` | Max years of required experience to keep |
| `TITLE_MUST_INCLUDE` | PM / APM | Which role titles qualify (override with `titles_local.txt`) |
| `NYC_LOCS / SF_LOCS` | see file | Target geographies |
| `SOURCES` | all on | Toggle each source |

### Tests

```bash
python3 test_pmfarm.py
```

13 test groups cover title and seniority filtering, deduplication, location
classification, experience parsing, Bright Data HTML parsing, and output
rendering.

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

Python 3.11+ · standard library · Bright Data Web Unlocker · GitHub Actions ·
GitHub Pages · static HTML. Built with Claude Code.

### Possible next steps

- Add freshness filters for 1, 3, 7, and 14 day windows.
- Add lightweight company tags.
- Add shareable search URLs.
- Add a short daily digest.

</details>

---

[MIT](LICENSE)
