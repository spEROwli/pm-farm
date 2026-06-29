# PM Farm Case Study

## One-line summary

PM Farm is a live job-search intelligence tool that helps Product Manager candidates find fresh, relevant roles across fragmented hiring sources and act faster.

## Problem

Product Manager job searches are noisy and time-sensitive. Candidates often bounce between company career pages, ATS boards, startup job boards, and general aggregators. The result is slow triage, duplicated roles, stale postings, and too much time spent searching instead of applying or networking.

The core problem was not lack of job data. It was decision friction.

## User

The initial user was a PM candidate targeting a narrow role profile:

- Product Manager and Associate Product Manager roles
- New York City, San Francisco, and remote-friendly opportunities
- Fresh postings that are still worth acting on
- Roles that can be triaged quickly each morning

## Product goal

Build a lightweight tool that answers one question:

> What PM roles are fresh enough and relevant enough that I should act on them today?

## MVP scope

The MVP focused on speed, reliability, and actionability:

- Pull job data from hiring sources.
- Filter for PM-track roles.
- Remove stale or irrelevant roles.
- Deduplicate repeated listings.
- Publish a static dashboard.
- Refresh automatically through GitHub Actions.

## Key product decisions

### 1. Freshness over completeness

A large stale list is not useful in a fast job search. PM Farm prioritizes recent postings so the user can focus on roles where timing still creates an advantage.

### 2. Direct sources before generic aggregation

The tool favors hiring-system data and live sources over recycled listings. This improves confidence that a role is real and currently actionable.

### 3. Simple interface before complex workflow

The dashboard stays intentionally lightweight. The goal is not to become a full CRM. The goal is to help the user decide what to apply to or research next.

### 4. Data fidelity over polished guesses

The tool avoids inventing missing fields. If the source does not state a location, salary, URL, or experience requirement, the dashboard should not infer one. This preserves trust.

## Trade-offs

| Trade-off | Choice | Reason |
|---|---|---|
| Completeness vs. freshness | Freshness | Recent roles drive action. |
| Rich UI vs. fast shipping | Static dashboard | Lower maintenance and faster deployment. |
| Inferred metadata vs. source truth | Source truth | Trust beats cosmetic completeness. |
| Broad roles vs. PM focus | PM focus | Narrower scope improves signal. |
| Complex backend vs. automation | GitHub Actions | Enough automation without infrastructure overhead. |

## What shipped

- Live PM role dashboard
- Automated refresh workflow
- Deduplication logic
- PM/APM role filtering
- Source validation rules
- Static GitHub Pages deployment
- Local run path for scraping and page generation

Live dashboard: https://sperowli.github.io/pm-farm/pm_roles.html

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

- Product problem framing
- User workflow simplification
- Requirements definition
- Prioritization and scope control
- Data-quality policy design
- Automation strategy
- Technical execution with AI-assisted development
- Iteration based on real usage

## Interview story

I built PM Farm because my own job search had become too fragmented. I was wasting time checking multiple sources and still missing fresh postings. I narrowed the problem to daily role triage, defined strict data-quality rules, and shipped a live dashboard that refreshes automatically. The main product decision was to optimize for actionability, not completeness. That meant prioritizing freshness, source fidelity, and a lightweight interface over a more complex product. The result is a working tool I can use each morning to decide where to apply, research, or pursue warm outreach.
