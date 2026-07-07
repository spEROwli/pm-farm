# PM Farm Case Study

## Summary

PM Farm is a daily triage tool for Product Manager and Associate Product Manager job searches. It narrows a noisy search process into a focused list of recent roles to review each morning.

## Starting point

The project began as a technical learning exercise around APIs, automation, GitHub Actions, and AI-assisted development. The first version was more implementation-led than workflow-led.

Using it made the actual problem clearer: I did not need a broad job platform. I needed a quick way to see which fresh roles were worth acting on that day.

## Problem

PM job searches create a lot of repeated and stale information. Roles appear across company pages, ATS boards, startup job boards, and aggregators. The work is not just finding listings. It is deciding which ones deserve time.

## Product goal

Build a lightweight tool that answers one question:

> Which fresh PM-track roles should I review today?

## Scope

The first useful version focused on a few constraints:

- PM and APM roles only
- New York City, San Francisco, and U.S. remote
- Recent postings
- Deduplication across repeated listings
- Source data preserved as returned
- Static dashboard output
- Automated daily refresh

## Trade-offs

| Trade-off | Choice |
|---|---|
| Breadth vs. focus | Focused role scope |
| Completeness vs. freshness | Freshness |
| Rich UI vs. focused output | Static dashboard |
| Filled-in fields vs. source truth | Source truth |
| More sources vs. lower noise | Lower noise first |

## What shipped

- Role collection from live hiring sources
- PM and APM filtering
- Freshness filtering
- Deduplication logic
- Static dashboard
- GitHub Actions refresh
- Validation rules in [SCRAPER_RULES.md](SCRAPER_RULES.md)

Live dashboard: https://sperowli.github.io/pm-farm/pm_roles.html

## What I learned

The main lesson was to separate the mechanism from the product. The scraper is the mechanism. The product is the daily decision surface.

The project became better when I narrowed it around the workflow instead of adding more features. For this use case, a focused reliable tool was more useful than a broader platform.

## Possible next steps

- Add freshness filters for 1, 3, 7, and 14 day windows.
- Add lightweight company tags.
- Add shareable search URLs.
- Add a short daily digest for newly added roles.
