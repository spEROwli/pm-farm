# PM Farm Case Study

## One-line summary

PM Farm is a self-updating PM job-search triage tool that turns noisy hiring sources into a focused morning shortlist of fresh Product Manager and Associate Product Manager roles.

## Context

PM Farm started as a technical learning project. I wanted to learn APIs, scraping, automation, GitHub Actions, and AI-assisted coding by building something useful.

The first version was solution-led. I started with the implementation before fully defining the user workflow. That made the project broader than it needed to be.

The useful shift came from asking a product question instead of a technical one:

> Which fresh PM roles are relevant enough to apply to, research, or pursue through warm outreach today?

That reframed the project from a scraper into a daily triage workflow.

## Problem

PM job searches are noisy and time-sensitive. Candidates bounce between company career pages, ATS boards, startup job boards, and general aggregators. The result is duplicated roles, stale postings, and too much time spent searching instead of applying, networking, or preparing.

The core problem was decision friction, not lack of job data.

## User and use case

The initial user was a PM candidate targeting a narrow role profile:

- Product Manager and Associate Product Manager roles
- New York City, San Francisco, and U.S. remote opportunities
- Fresh postings that are still worth acting on
- A dashboard that can be reviewed quickly each morning

## Product goal

Build a lightweight tool that answers one question:

> What roles are fresh enough and relevant enough that I should act on them today?

## MVP scope

The MVP focused on speed, reliability, and actionability:

- Pull job data from live hiring sources.
- Filter for PM and APM roles.
- Prioritize fresh postings over broad coverage.
- Deduplicate repeated listings.
- Preserve source data instead of guessing missing details.
- Publish a lightweight static dashboard.
- Refresh automatically through GitHub Actions.

## Key product decisions

| Decision | Trade-off | Rationale |
|---|---|---|
| Daily triage over broad search | Narrower scope | The user needed a short list of roles worth acting on, not another large job database. |
| Freshness over completeness | Fewer total roles | Recent roles are more actionable than stale coverage. |
| Source fidelity over inferred metadata | Less polished output | Trust matters more than filling every empty field. |
| Deduplication before adding more sources | Slower source expansion | Repeated roles make daily triage slower and less trustworthy. |
| Static dashboard before full web app | Less interactivity | A static page solved the workflow with lower maintenance and faster deployment. |
| PM/APM scope only | Fewer adjacent roles | Narrow role scope improved signal and reduced irrelevant results. |

## What shipped

- Live PM role dashboard
- Automated GitHub Actions refresh
- PM and APM role filtering
- 72-hour freshness rule
- Seniority exclusion logic for executive-layer titles
- Deduplication across URL, company, title, and known company-name variants
- Source validation rules documented in [SCRAPER_RULES.md](SCRAPER_RULES.md)
- Static GitHub Pages deployment
- Local run path for scraping and page generation

Live dashboard: https://sperowli.github.io/pm-farm/pm_roles.html

## What I learned

The main product lesson was that a working technical system is not automatically a good product. The first version was useful as exploration, but the project became stronger when I stopped optimizing for what I could build and narrowed around the decision the user needed to make.

The product win was not building a better job platform. Mature tools already do broad search better. The win was recognizing that my workflow needed something narrower: a reliable daily decision surface for fresh roles worth acting on.

That is the part I would carry into a PM role: define the workflow, clarify the requirements, choose the quality rules that matter, constrain scope, and stop once the product is useful.

## What I would improve next

The next iteration should stay small and decision-oriented:

1. **Freshness filter**  
   Let users switch between roles posted in the last 1, 3, 7, or 14 days.

2. **Company-fit tags**  
   Add lightweight tags such as Healthtech, AI, Hardware, Developer Tools, and Enterprise SaaS.

3. **Shareable search state**  
   Add URL query parameters so filtered views can be shared.

4. **Daily digest**  
   Surface only newly added roles since the previous run.

## PM skills demonstrated

- Reframing a solution-led project around a user workflow
- Product problem framing
- Requirements definition
- Prioritization and scope control
- Data-quality policy design
- Automation strategy
- Technical execution with AI-assisted development
- Iteration based on real usage

## Interview story

PM Farm started as a technical learning project. I wanted to learn APIs, scraping, automation, GitHub Actions, and AI-assisted coding by building something useful.

The first version was solution-led. I had not clearly defined the requirements or the daily workflow before building, which made the project broader than it needed to be.

As I used the tool, I realized the real problem was narrower than building a job-search platform. Tools like Hiring Cafe already do broad search better. The actual workflow I needed was daily triage: which fresh PM roles are relevant enough to apply to, research, or pursue through warm outreach today?

I reframed the project around that workflow. I prioritized freshness, deduplication, source fidelity, and a lightweight dashboard over completeness or feature depth. The product win was not beating mature tools. It was recognizing that the original solution was too broad, narrowing the scope, and turning a technical exploration into a usable decision-support tool.
