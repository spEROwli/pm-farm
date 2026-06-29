# PM Farm

**PM Farm is a live PM job-search triage tool.** It pulls fresh Product Manager-track roles from hiring sources, filters them to a focused target profile, and publishes a lightweight dashboard for daily review.

**Live dashboard:** https://sperowli.github.io/pm-farm/pm_roles.html  
**Case study:** [CASE_STUDY.md](CASE_STUDY.md)

## Project framing

PM Farm started as a technical learning project. I wanted to learn how to work with APIs, scraping, automation, GitHub Actions, and AI-assisted coding by building something useful.

The first version was solution-led. I was asking, “Can I build this?” before I had clearly defined the user workflow.

As I used the tool, the sharper product problem became clear:

> How can a PM candidate reduce daily job-search triage time and focus on fresh roles worth acting on today?

PM Farm does not try to beat mature search tools like Hiring Cafe. Those tools are broader, faster, and more polished. The value here is narrower: a scoped workflow for one user profile, with explicit freshness, deduplication, and data-quality rules.

The product lesson was learning to move from technical exploration to a defined workflow: identify the decision the user needs to make, constrain the scope, and ship something usable.

## What it does

- **Aggregates fresh PM roles** from company hiring sources and startup job boards.
- **Filters to a target profile** focused on Product Manager and Associate Product Manager roles across NYC, San Francisco, and remote-friendly searches.
- **Prioritizes freshness** so recent postings are easier to act on before they become stale.
- **Deduplicates noisy listings** across URL, company, title, and source variants.
- **Preserves source fidelity** by avoiding invented job details or polished guesses.
- **Publishes a static dashboard** that can be opened quickly each morning.
- **Runs automatically** through GitHub Actions so the tool stays current without manual scraping.

## Product decisions

| Decision | Why it mattered |
|---|---|
| Technical exploration became a product workflow | The project moved from "learn APIs" to "reduce daily triage friction." |
| Freshness over completeness | Recent roles are more actionable than large stale lists. |
| Deduplication before more sources | Reducing repeated roles made the dashboard more useful than adding more noisy inputs. |
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

PM Farm demonstrates the product arc I wanted to practice: start with technical curiosity, recognize when the first solution is too broad, define the sharper user workflow, constrain scope, and ship a working tool.

The project is not meant to prove that I built a better job platform. It is meant to show that I can learn quickly, use AI-assisted development responsibly, define quality rules, make trade-offs, and turn a messy technical exploration into a usable decision-support workflow.

## License

[MIT](LICENSE)
