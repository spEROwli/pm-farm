# PM Farm — Case Study

## Overview

PM Farm is a daily triage tool for a Product Manager job search. Every morning it
pulls fresh PM and APM openings from eight live hiring sources, filters them to a
focused target profile, removes roles I have already seen, and publishes a single
dashboard I review over coffee. It runs itself through GitHub Actions and costs
about fifty cents a month.

I built it with Claude Code. I am a product manager, not a software engineer. The
value of this project is not the code; it is the set of product decisions behind
it: what to build, what to reuse, what to leave out, and how to keep the output
honest. Claude Code was the execution layer. The judgment was mine.

**[Live dashboard](https://sperowli.github.io/pm-farm/pm_roles.html)**

---

## Starting point

The project began as a learning exercise around APIs, automation, GitHub Actions,
and AI-assisted development. The first version was more implementation-led than
workflow-led: I was building because building felt productive.

Using it made the real problem clearer. I did not need a broad job platform. I
needed a fast way to see which fresh roles were worth acting on that day. Once I
named that, I set a real goal and decided just as deliberately what not to build.

---

## Problem

PM job searches generate a lot of repeated and stale information. The same role
shows up across company pages, ATS boards, startup job boards, and aggregators.
Listings go stale, roles I already applied to keep reappearing, and aggregator
sites route through redirect links instead of the company's own application. The
work is not just finding listings. It is deciding which ones deserve my time.

---

## Product goal

Build a lightweight tool that answers one question well:

> Which fresh PM-track roles should I review today?

---

## Scope

The first useful version held a tight line:

- PM and APM roles only
- New York City, San Francisco, and U.S. remote
- Recent postings
- Deduplication across repeated listings
- Source data preserved exactly as returned
- Static dashboard output
- Automated daily refresh

---

## Trade-offs

The interesting part of this project was the decisions, not the code.

| Decision | Choice and reasoning |
|---|---|
| Direct APIs vs. aggregators | Direct ATS APIs (Greenhouse, Ashby, Lever, Workable) give clean links but cover fewer companies. I used them as the trusted core, then added search-style sources for breadth, held to the same filters. |
| Build vs. reuse | Three sources are JavaScript-gated and unreachable by a plain request. Instead of writing fragile scraping code, I used the Bright Data Web Unlocker. I did not reinvent the wheel. |
| Signal vs. proxy | Job titles are noisy. "Senior Associate" can mean entry level at one company and senior at another. So I filter on the stated years of experience, the real requirement, not the title. |
| Freshness vs. completeness | Recent roles are the ones worth acting on, so the pipeline favors a smaller fresh list over a larger stale one. |
| Source truth vs. filled-in fields | The tool never invents a missing detail. A blank experience field means the posting did not state one. The rules are written down in [SCRAPER_RULES.md](SCRAPER_RULES.md). |
| Cost as a constraint | The gated source bills per request, so I built spend guards in from the start: a request cap and a pay-as-you-go ceiling. Cost was a design input, not an afterthought. |

---

## What shipped

- Role collection from eight live sources, four direct ATS APIs plus four
  search-style sources, with the gated ones reached through Bright Data.
- PM and APM title filtering, with an externally configurable title list so the
  same pipeline can widen to adjacent roles without touching the default output.
- Experience-range and freshness filtering read from the posting itself.
- Deduplication by URL, company and title, aggregator name variants, and my own
  application history.
- Source-fidelity validation so no invented data ever reaches the dashboard.
- A static, mobile-friendly dashboard with search and filter chips.
- A daily GitHub Actions run that rebuilds and republishes with no machine of
  mine needing to be on.
- A test suite covering filtering, dedupe, location classification, experience
  parsing, and the Bright Data parse path.

---

## What I learned

The main lesson was to separate the mechanism from the product. The scraper is
the mechanism. The product is the daily decision surface. The project got better
when I narrowed it around the workflow instead of adding features.

The most useful lesson was about how I work: to notice when building becomes
avoidance, to cut a path that was not serving the goal, and to reach for existing
tools rather than rebuild them. Knowing when to build and when to stop is the part
of this project I am most proud of.

Working with Claude Code also taught me the shape of the ecosystem product work
depends on: how different APIs behave, the difference between open and gated data,
what a design system looks like in shipped code, and how to weigh cost against
coverage. I understand it because I built inside it.

---

## Possible next steps

- Add freshness filters for 1, 3, 7, and 14 day windows.
- Add lightweight company tags on each card.
- Add shareable search URLs.
- Add a short daily digest of newly added roles.
