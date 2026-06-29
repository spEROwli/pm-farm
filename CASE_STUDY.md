# PM Farm Case Study

## One-line summary

PM Farm is a live PM job-search triage tool that started as a technical learning project and evolved into a focused daily decision-support workflow for Product Manager candidates.

## Origin

PM Farm started as a technical learning project. I wanted to learn APIs, scraping, automation, GitHub Actions, and AI-assisted coding by building something useful.

The first version was solution-led. I started with the solution before clearly defining the requirements or the user workflow. That led to unnecessary complexity, inefficient planning, and some overbuilding.

As I used the tool, the useful shift was asking what decision the user actually needed to make. The answer was not “show every possible PM job.” Tools like Hiring Cafe already do broad search better. The answer was narrower:

> Help me quickly decide which fresh PM roles deserve action today.

That reframed PM Farm from a broad job-search idea into a daily triage workflow.

## Problem

Product Manager job searches are noisy and time-sensitive. Candidates bounce between company career pages, ATS boards, startup job boards, and general aggregators. The result is duplicated roles, stale postings, and too much time spent searching instead of applying, networking, or preparing.

The core problem was decision friction, not lack of job data.

## User

The initial user was a PM candidate targeting a narrow role profile:

- Product Manager and Associate Product Manager roles
- New York City, San Francisco, and remote-friendly opportunities
- Fresh postings that are still worth acting on
- Roles that can be triaged quickly each morning

## Product goal

Build a lightweight tool that answers one question:

> What PM roles are fresh enough and relevant enough that I should apply to, research, or pursue through warm outreach today?

## MVP scope

The MVP focused on speed, reliability, and actionability:

- Pull job data from hiring sources.
- Filter for PM-track roles.
- Prioritize fresh postings over complete coverage.
- Deduplicate repeated listings.
- Preserve source fidelity instead of guessing missing details.
- Publish a lightweight static dashboard.
- Refresh automatically through GitHub Actions.

## Key product decisions

### 1. Reframe the project from technical exploration to user workflow

The original motivation was learning. The product discipline came from admitting the first version was solution-led, then narrowing the project around a real workflow: daily role triage. That shift changed the success criteria from “more scraping” to “faster decision-making.”

### 2. Freshness over completeness

A large stale list is not useful in a fast job search. Freshness mattered more than completeness because recent roles are more actionable than broad, stale coverage.

### 3. Source fidelity over polished guessing

The tool avoids inventing missing fields. If the source does not state a location, salary, URL, or experience requirement, the dashboard should not infer one. Source fidelity mattered more than making the output look complete.

### 4. Deduplication before adding more sources

More sources can create more noise. Deduplication mattered more than adding additional feeds because repeated roles make daily triage slower and less trustworthy.

### 5. Lightweight dashboard before complex product

The dashboard stays intentionally lightweight. The goal is not to become a full CRM or job platform. The goal is to help the user decide what to apply to, research, or pursue next.

## Trade-offs

| Trade-off | Choice | Reason |
|---|---|---|
| Learning project vs. product artifact | Product artifact | The project became more useful when framed around a real workflow. |
| Completeness vs. freshness | Freshness | Recent roles drive action. |
| Rich UI vs. fast shipping | Static dashboard | Lower maintenance and faster deployment. |
| Inferred metadata vs. source truth | Source truth | Trust beats cosmetic completeness. |
| More sources vs. less noise | Less noise | Deduplication improved triage more than adding feeds. |
| Broad roles vs. PM focus | PM focus | Narrower scope improves signal. |
| Full job platform vs. focused workflow | Focused workflow | Stopping at a useful workflow mattered more than building a complex product. |

## What shipped

- Live PM role dashboard
- Automated refresh workflow
- Deduplication logic
- PM/APM role filtering
- Source validation rules
- Static GitHub Pages deployment
- Local run path for scraping and page generation

Live dashboard: https://sperowli.github.io/pm-farm/pm_roles.html

## What I learned

The biggest product lesson was that building from a technical idea is not enough. The first version was solution-led because I started with the solution before defining requirements. That created unnecessary complexity and inefficient planning.

The project became stronger when I stopped defending the original solution and asked what decision the user actually needed to make. The decision was not “show every possible PM job.” It was “help me quickly decide which fresh roles deserve action today.”

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
- User workflow simplification
- Requirements definition
- Prioritization and scope control
- Data-quality policy design
- Automation strategy
- Technical execution with AI-assisted development
- Iteration based on real usage

## Interview story

PM Farm started as a technical learning project. I wanted to learn APIs, scraping, automation, GitHub Actions, and AI-assisted coding by building something useful.

The first version was solution-led. I had not clearly defined the requirements or the user workflow before building, which led to some inefficient planning and overbuilding.

As I used the tool, I realized the real problem was narrower than “build a job search platform.” Tools like Hiring Cafe already do broad search better. The actual workflow I needed was daily triage: which fresh PM roles are relevant enough to apply to, research, or pursue through warm outreach today?

I reframed the project around that workflow. I prioritized freshness, deduplication, source fidelity, and a lightweight dashboard over completeness or feature depth. The product win was not beating mature tools. It was recognizing that the original solution was too broad, narrowing the scope, and turning a technical exploration into a usable decision-support tool.
