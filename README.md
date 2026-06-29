# PM Farm

**PM Farm is a live job-search intelligence tool for Product Manager candidates.** It pulls fresh Product Manager-track roles from company hiring systems, filters them to a focused target profile, and publishes a triage-ready dashboard that refreshes automatically.

**Live dashboard:** https://sperowli.github.io/pm-farm/pm_roles.html  
**Case study:** [CASE_STUDY.md](CASE_STUDY.md)

## Product framing

Job seekers lose time checking fragmented career sites, stale aggregators, and noisy job boards. PM Farm was built to solve one specific user problem:

> Help a Product Manager candidate quickly find fresh, relevant roles and decide where to act today.

This project was built as a practical job-search operating tool, not as a coding novelty. I defined the user problem, source strategy, filtering rules, data-quality constraints, and prioritization logic, then used Claude Code as an implementation accelerator.

## What it does

- **Aggregates fresh PM roles** from company hiring sources and startup job boards.
- **Filters to a target profile** focused on Product Manager and Associate Product Manager roles across NYC, San Francisco, and remote-friendly searches.
- **Prioritizes freshness** so recent postings are easier to act on before they become stale.
- **Deduplicates noisy listings** across URL, company, title, and source variants.
- **Publishes a static dashboard** that can be opened quickly each morning.
- **Runs automatically** through GitHub Actions so the tool stays current without manual scraping.

## Product decisions

| Decision | Why it mattered |
|---|---|
| Freshness over completeness | Recent roles are more actionable than large stale lists. |
| Direct hiring sources first | Company ATS feeds reduce dependency on recycled listings. |
| Simple static dashboard | Fast to ship, easy to host, low maintenance. |
| Strict data fidelity rules | Trust matters more than filling every field. |
| Narrow role scope | PM and APM searches need precision more than volume. |

## Architecture

```text
verified_companies.json
        |
        v
pmfarm.py  -> source fetchers + filters + dedupe
        |
        +--> pm_roles.csv
        |
        v
build_page.py -> pm_roles.html -> GitHub Pages
```

Core stack:

- Python 3.11+
- Standard library
- SQLite
- GitHub Actions
- GitHub Pages
- Static HTML

## Data-quality principles

The scraper follows a strict rule: if a role was not returned by a live source during the run, it does not get emitted. It does not invent job titles, locations, URLs, salaries, or experience requirements. See [SCRAPER_RULES.md](SCRAPER_RULES.md) for the full validation rules.

## Running locally

```bash
python3 pmfarm.py
python3 build_page.py
```

## Tests

```bash
python3 -m pytest test_pmfarm.py -v
```

## Roadmap

The next highest-leverage improvements are intentionally small:

- Add visible freshness filters: 1 day, 3 days, 7 days.
- Add lightweight company-fit tags such as Healthtech, AI, Hardware, Developer Tools, and Enterprise SaaS.
- Add shareable search URLs using query parameters.
- Add a short daily digest for newly added roles.

## Why this matters

PM Farm demonstrates product judgment more than software complexity: identifying a painful workflow, narrowing scope, defining data-quality rules, shipping a working tool, and iterating toward faster decisions.

## License

[MIT](LICENSE)
