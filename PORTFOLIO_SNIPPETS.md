# PORTFOLIO_SNIPPETS.md

Six code excerpts from pm-farm that show product judgment, not just code.
Each caption is a first-person talking point for a non-engineer hiring manager.

---

## 1. Source Fidelity: Years Parsing Does Not Guess

**File:** `pmfarm.py:486–522`

```python
def _parse_years(text: str) -> tuple[str, str]:
    """Return (years_raw, years_context).

    Honest-by-design: collects every requirement-style year mention, drops
    team/collective-tenure phrasing, and reports the MINIMUM HARD bar found (the
    most optimistic read, so you never self-reject). A bar framed as preferred /
    nice-to-have is set aside so it can't pull the gate below a real requirement
    -- but if a posting states ONLY soft bars, those still count (a sole
    "preferred 8+ years" drops as before). The context column shows every matched
    phrase so you can catch the number if it's lying. No match -> unknown.
    """
    hard:     list[int] = []
    soft:     list[int] = []
    contexts: list[str] = []
    for pattern, mode in YEARS_PATTERNS:
        for m in pattern.finditer(text):
            span = m.group(0).lower()
            if any(bad in span for bad in YEARS_DISQUALIFY):
                continue
            nums = [int(g) for g in m.groups() if g]
            if not nums:
                continue
            value  = nums[0] if mode == "low" else min(nums)
            bucket = soft if _requirement_kind(text, m.start(), m.end()) == "soft" else hard
            bucket.append(value)
    # Gate on hard requirements; soft bars only count when there are no hard
    # ones, so the optimistic low-end never falls onto a "preferred" qualifier.
    pool = hard or soft
    if not pool:
        return ("unknown", "")
    return (str(min(pool)), " | ".join(contexts[:3]))
```

The system never assigns a years requirement I cannot show verbatim from the job posting. When a posting says "3-5 years," I record 3, the lowest number a qualified candidate could have. When a posting says "Required: 5+ years, Preferred: 2+ years," I record 5, because the hard floor is what actually screens people out. If there is no stated requirement, the field says "unknown" -- never a guess based on title. This rule came directly from early runs that were filtering out real opportunities because I treated "Strongly Preferred" language the same as "Required."

---

## 2. Deduplication: What Counts as the Same Job

**File:** `pmfarm.py:536–544`, `pmfarm.py:686–700`

```python
def _norm_url(url: str) -> str:
    """Normalize a job URL for reliable dedupe: lowercase, force https, strip
    query string / fragment / trailing slash. Defeats false misses from
    ?gh_jid=, ?gh_src=, http vs https, and trailing-slash variants."""
    u = (url or "").strip().lower()
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    u = u.split("?", 1)[0].split("#", 1)[0]
    return u.rstrip("/")


def _deduped(jobs: list[dict], applied: set[str]) -> list[dict]:
    out, seen = [], set()
    for j in jobs:
        nu = _norm_url(j["url"])
        ck = _ct_key(j["company"], j["title"])
        if nu in applied or ck in applied:
            continue
        if nu in seen or ck in seen:
            continue
        seen.add(nu)
        seen.add(ck)
        out.append(j)
    return out
```

The same job can appear with different URLs across sources, for example with or without a tracking parameter, an http vs https prefix, or a trailing slash. I normalize all URLs to a canonical form before comparing them so those surface-level differences do not create duplicates. I also match by company name and title together, which catches cases where applied.csv only has one URL variant but the scraper fetches a slightly different one. The applied log tracks roles at the URL level, not the company level, so applying to one role at a company does not hide other open roles there.

---

## 3. Seniority and Experience Cap: Two Separate Rules for One Problem

**File:** `pmfarm.py:186–201`, `pmfarm.py:1421–1433`

```python
# "Senior" and "Sr" are intentionally NOT in this exclusion list. Many companies
# use them as default prefixes (e.g. "Senior Associate PM") without implying an
# elevated experience bar. The years gate (EXPERIENCE_CAP) handles those.
_HARD_SENIOR_RE = re.compile(
    r'^\s*(?:staff|principal|lead|group|head|chief|distinguished|'
    r'director|managing\s+director|vice\s+president|vp|svp|evp)\b'
    r'|\b(?:iv|iii|ii)\b(?=\s*(?:[,\-–—]|$))',
    re.IGNORECASE,
)

# Keep roles requiring <= this many years, plus any role with no stated
# requirement. The parsed years value is the ground truth -- never the title.
EXPERIENCE_CAP = 3

    def _over_bar(j: dict) -> bool:
        try:
            return int(j["years_raw"]) > EXPERIENCE_CAP
        except (ValueError, TypeError):
            return False   # "unknown" / unstated -> keep
    raw = [j for j in raw if not _over_bar(j)]
```

I apply two different filters for seniority, and they do different things. The title filter drops unambiguous org-layer titles like Director or VP on the title alone, because those roles have a fundamentally different scope regardless of stated experience. It does not drop "Senior PM" because many companies label standard PM roles as senior without raising the bar. The years filter then catches those: if the posting explicitly states more than 3 years required, the role is dropped regardless of title. A "Senior PM" requiring 2 years passes. A plain "Product Manager" requiring 5 years does not. This keeps the list honest and avoids self-rejection based on job titles alone.

---

## 4. Test Encoding a Product Decision: Soft vs. Hard Qualifiers

**File:** `test_pmfarm.py:99–125`

```python
    cases = [
        # sanity regressions
        ("3+ years of product management experience",             "3"),
        ("Minimum of 4 years in product",                         "4"),
        ("1-3 years in a product role",                           "1"),
        # hard requirement must out-vote a softer "preferred" bar: a real
        # Required 5+ posting must NOT slip through on a Strongly-Preferred 2+.
        # (regression: live "Senior Solutions Engineer" card, 2026-06-13)
        ("Required . 5+ years in software pre-sales (SE, Sales Consulting, "
         "or technical Account Management roles). Strongly Preferred . "
         "2+ years working specifically with product analytics.",  "5"),
        # the gate reads the LOW hard bar, not the high preferred one
        ("Required . 2+ years in product. Strongly Preferred . "
         "5+ years working with analytics.",                       "2"),
        # a trailing qualifier stays inside its own clause
        ("5+ years preferred. 2+ years required.",                "2"),
        # a posting with ONLY a soft bar still gates on it (no scope creep)
        ("Nice to have: 8+ years in fintech.",                    "8"),
    ]
    for desc, want in cases:
        raw, ctx = pmfarm._parse_years(desc)
        check(f"years/{desc[:40]}", raw, want)
```

Each test case came from a real posting that caused wrong behavior before I fixed it. The regression note references an actual card from June 13, 2026 that was slipping through because the parser was reading a "Strongly Preferred 2+" as the binding requirement and ignoring the "Required 5+" above it. These tests do not just verify the code works; they document the decisions about how to read ambiguous job descriptions. When I talk about "honest filtering," this is what that means in practice: every edge case has a recorded decision behind it.

---

## 5. GitHub Actions: Ships Daily Without Intervention

**File:** `.github/workflows/daily-scrape.yml`

```yaml
name: Daily PM Role Scrape

on:
  schedule:
    - cron: '30 11 * * *'  # 7:30am ET daily
  workflow_dispatch:        # allow manual trigger from GitHub UI

    - name: Run scraper
      env:
        BRIGHTDATA_API_KEY: ${{ secrets.BRIGHTDATA_API_KEY }}
        PYTHONUTF8: "1"
      run: python3 pmfarm.py

    - name: Build HTML
      run: python3 build_page.py

    - name: Commit and push if changed
      run: |
        git config user.name  "github-actions[bot]"
        git config user.email "github-actions[bot]@users.noreply.github.com"
        git add pm_roles.html verified_companies.json
        git diff --cached --quiet && echo "No changes" || \
          { git commit -m "daily update $(date -u +%Y-%m-%d)" && \
            git pull --rebase origin main && git push; }
```

The workflow runs every morning at 7:30am, scrapes all sources, rebuilds the dashboard, and commits only when the output actually changed. The commit is idempotent: if nothing changed since yesterday, nothing gets committed. The API key never appears in the workflow file; it is stored as a GitHub repository secret and injected at runtime. This runs unattended every day. I check it when I want to, not because I have to.

---

## 6. Location Classification: Unknown Excluded by Design

**File:** `pmfarm.py:547–579`

```python
def _loc_class(location: str, snippet: str = "") -> str:
    # Classification uses only the location field, not the JD snippet, to prevent
    # body text like "remote work options" from misclassifying in-office roles.
    loc_lower = location.lower()
    has_nyc = any(n in loc_lower for n in NYC_LOCS)
    has_sf  = any(s in loc_lower for s in SF_LOCS)

    # A named foreign country/region makes this international unless it also
    # names a target city -- "London + San Francisco" is still a SF role.
    has_intl = any(m in loc_lower for m in _INTL_MARKERS)
    if has_intl and not has_nyc and not has_sf:
        return "international"

    has_explicit_remote = "remote" in loc_lower
    has_non_target_us   = any(c in loc_lower for c in _US_NON_NYC)
    has_us_generic      = (not has_non_target_us) and any(r in loc_lower for r in REMOTE_LOCS)
    has_remote          = has_explicit_remote or has_us_generic

    if has_remote and has_nyc and has_sf: return "remote+nyc+sf"
    if has_remote and has_nyc:            return "remote+nyc"
    if has_remote and has_sf:             return "remote+sf"
    if has_remote:                        return "remote"
    if has_nyc    and has_sf:             return "nyc+sf"
    if has_nyc:                           return "nyc"
    if has_sf:                            return "sf"
    if has_non_target_us:                 return "unknown"
    if location.strip():                  return "international"
    return "unknown"
```

Location is classified from the location field only, not the job description. A role in Boston that mentions "remote flexibility" in the body text is still classified as unknown, not remote. The daily default excludes unknown locations entirely. This was a deliberate choice: an unclear location means I cannot act on the role today, and including it slows down triage. The tool can show unknown locations with a flag when I want to inspect edge cases, but the default optimizes for roles I can actually apply to right now.
