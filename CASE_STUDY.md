# PM Farm Case Study

## One-line summary

PM Farm is a live job-search intelligence tool that started as a technical learning project and evolved into a focused daily triage workflow for Product Manager candidates.

## Origin

I started PM Farm because I wanted to learn practical AI-assisted software development: working with APIs, scraping job sources, automating runs, and publishing a usable page. The first version was solution-led. I was asking, "Can I build this?" before I had fully sharpened the user problem.

That was the important lesson. As I used the tool, I realized the product opportunity was not to outcompete mature search platforms. Tools like Hiring Cafe are broader, faster, and more polished. The better product question was narrower:

> What would make my own daily PM job-search triage faster, more reliable, and easier to act on?

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

### 1. Reframe the project from technical exploration to user workflow

The original motivation was learning. The product discipline came from narrowing the project around a real workflow: daily role triage. That shift changed the success criteria from "more scraping" to "faster decision-making."

### 2. Freshness over completeness

A large stale list is not useful in a fast job search. PM Farm prioritizes recent postings so the user can focus on roles where timing still creates an advantage.

### 3. Direct sources before generic aggregation

The tool favors hiring-system data and live sources over recycled listings. This improves confidence that a role is real and currently actionable.

### 4. Simple interface before complex workflow

The dashboard stays intentionally lightweight. The goal is not to become a full CRM. The goal is to help the user decide what to apply to or research next.

### 5. Data fidelity over polished guesses

The tool avoids inventing missing fields. If the source does not state a location, salary, URL, or experience requirement, the dashboard should not infer one. This preserves trust.

## Trade-offs

| Trade-off | Choice | Reason |
|---|---|---|
| Learning project vs. product artifact | Product artifact | The project became more useful when framed around a real workflow. |
| Completeness vs. freshness | Freshness | Recent roles drive action. |
| Rich UI vs. fast shipping | Static dashboard | Lower maintenance and faster deployment. |
| Inferred metadata vs. source truth | Source truth | Trust beats cosmetic completeness. |
| Broad roles vs. PM focus | PM focus | Narrower scope improves signal. |
| Competing with mature tools vs. focused workflow | Focused workflow | The goal is not to beat Hiring Cafe. The goal is to demonstrate product judgment and solve a narrow daily need. |

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

The biggest product lesson was that building from a technical idea is not enough. The project became stronger when I admitted the first version was solution-led, then reframed around a specific user workflow and constrained the scope.

That is the part I would carry into a PM role: do not defend the original solution. Find the sharper problem, define the decision the user needs to make, and reshape the product around that.

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

PM Farm started as a technical learning project. I wanted to learn APIs, scraping, automation, and AI-assisted coding by building something useful. The first version was solution-led. As I used it, I realized the actual product problem was narrower: I needed a faster way to triage fresh PM roles each morning so I could spend more time applying, networking, and preparing. I reframed the tool around that workflow, prioritized freshness and source fidelity over completeness, and shipped a lightweight dashboard that refreshes automatically. I do not position it as better than mature tools like Hiring Cafe. The product win was recognizing the sharper problem, constraining the scope, and turning a technical exploration into a usable decision-support tool.
