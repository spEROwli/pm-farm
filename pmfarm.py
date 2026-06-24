#!/usr/bin/env python3
"""
pmfarm.py — role scraper: Greenhouse · Ashby · Lever (· hiring.cafe via Bright Data)

  python3 pmfarm.py [--remote-only] [--include-unknown-loc]

Targets: Product Manager · Associate Product Manager (APM) only.
NYC hard constraint + US remote. Experience bar: 0-3 yrs stated or unstated.
All data comes from live ATS JSON APIs. See SCRAPER_RULES.md.
Dedupe: gmail_applied.txt (primary) + applied.csv (fallback).
"""

import argparse, csv, datetime, html as H, json, os, re, shutil, subprocess, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── SOURCES (parametric toggles) ──────────────────────────────────────────────
# Master switch per source. Adding or tuning a source is a config edit here, not
# surgery in cmd_local. The ATS sources (greenhouse/ashby/lever) are live; the
# disabled aggregators (themuse/remotive/adzuna) are not toggled here because they
# are intentionally not called at all. "brightdata" (hiring.cafe) ships OFF and
# stays inert — zero spend — until the API key exists. See BRIGHTDATA_SETUP.md.
SOURCES = {
    "greenhouse": True,
    "ashby":      True,
    "lever":      True,
    "workable":   True,
    "brightdata": True,
    "adzuna":     False,  # redirect links go through adzuna.com, not the employer's page
    "muse":       True,
}

# ── Adzuna search API ─────────────────────────────────────────────────────────
# Adzuna lets us SEARCH across all companies by title + location — no slug list
# needed. This is the dynamic discovery tier: any company posting a PM role in
# NYC or SF shows up here regardless of which ATS they use.
# Keys are read from adzuna_key.txt (line 1 = app_id, line 2 = app_key) or env
# vars ADZUNA_APP_ID / ADZUNA_APP_KEY. Free tier: 1000 req/day.
_ADZUNA_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adzuna_key.txt")
ADZUNA_COUNTRY   = "us"
ADZUNA_MAX_PAGES = 3   # 50 results/page × 3 pages = 150 results per search query

# Search queries: title keywords × locations. Adzuna `where` accepts city names.
ADZUNA_SEARCHES = [
    ("product manager",           "new york"),
    ("associate product manager", "new york"),
]


def _load_adzuna_keys() -> tuple[str, str] | tuple[None, None]:
    app_id  = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if app_id and app_key:
        return app_id, app_key
    try:
        lines = open(_ADZUNA_KEY_FILE, encoding="utf-8").read().strip().splitlines()
        return (lines[0].strip(), lines[1].strip()) if len(lines) >= 2 else (None, None)
    except Exception:
        return None, None


def fetch_adzuna() -> list[dict]:
    if not SOURCES.get("adzuna"):
        return []
    app_id, app_key = _load_adzuna_keys()
    if not app_id or not app_key:
        print("  [adzuna] inert: no keys (set ADZUNA_APP_ID/ADZUNA_APP_KEY or adzuna_key.txt)", file=sys.stderr)
        return []

    out: list[dict] = []
    seen_urls: set[str] = set()

    for what, where in ADZUNA_SEARCHES:
        for page in range(1, ADZUNA_MAX_PAGES + 1):
            params = urllib.parse.urlencode({
                "app_id":          app_id,
                "app_key":         app_key,
                "results_per_page": 50,
                "what":            what,
                "where":           where,
                "sort_by":         "date",
                "max_days_old":    MAX_AGE_DAYS,
                "content-type":    "application/json",
            })
            url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/{page}?{params}"
            data = _fetch(url)
            if not data or not isinstance(data, dict):
                break
            results = data.get("results", [])
            if not results:
                break
            for r in results:
                job_url = (r.get("redirect_url") or "").strip()
                if not job_url or job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                title   = (r.get("title") or "").strip()
                if not _passes_title(title):
                    continue
                company = (r.get("company", {}).get("display_name") or "").strip()
                location = (r.get("location", {}).get("display_name") or "").strip()
                desc    = _strip_html(r.get("description") or "")
                created = r.get("created")   # ISO 8601
                j = _make_job("adzuna", company, title, location, job_url, desc[:500], created, full_content=desc)
                if j:
                    out.append(j)

    print(f"  fetch_adzuna: {len(out)} roles across {len(ADZUNA_SEARCHES)} search queries")
    return out


# ── Bright Data / hiring.cafe (gitignored key, same pattern as Adzuna) ─────────
# brightdata_key.txt holds ONE line: the Bright Data API key. hiring.cafe is JS-gated
# and unreachable by the urllib fetchers; we pull its robots-ALLOWED /jobs/<role>/
# locations/<geo> result pages via `bdata scrape` (Web Unlocker renders the JS) and
# parse the embedded __NEXT_DATA__ ssrHits JSON — no paid Scraper Studio collector,
# just cheap Web Unlocker requests (~$1.50 / 1k). Absent/blank key → fetch is inert.
_BRIGHTDATA_KEY_FILE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brightdata_key.txt")
_BRIGHTDATA_RUN_STAMP    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".brightdata_last_run")
BRIGHTDATA_CLI           = os.environ.get("BRIGHTDATA_CLI", "bdata")          # CLI name or absolute path
BRIGHTDATA_UNLOCKER_ZONE = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker1")
BRIGHTDATA_MIN_HOURS     = 12   # once-per-12h spend lock; blocks accidental manual re-runs from double-billing

# hiring.cafe URLs are generated as /jobs/<role-slug>/locations/<geo-slug>. Changing
# coverage = editing these two lists (parametric). Verified geo slugs: "new-york"
# (NYC, primary) and "san-francisco-ca" (SF — confirmed live, 20 hits; note plain
# "san-francisco"/"sf"/"san-francisco-bay-area" all 404 to a generic page).
# MAX_PAGE_LOADS caps total pages fetched per run as the hard spend ceiling
# (9 roles × 2 geos = 18 URLs, under the cap).
HIRINGCAFE_ROLE_SLUGS = [
    "product-manager", "associate-product-manager",
]
HIRINGCAFE_GEO_SLUGS = ["new-york", "san-francisco-ca"]
MAX_PAGE_LOADS       = 30   # hard cap on hiring.cafe page fetches per run (cost ceiling)


def _load_brightdata_key() -> str | None:
    """Return the Bright Data API key, or None when unavailable.
    Checks BRIGHTDATA_API_KEY env var first (set by GitHub Actions secret), then
    falls back to brightdata_key.txt for local Mac runs."""
    env_key = os.environ.get("BRIGHTDATA_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        with open(_BRIGHTDATA_KEY_FILE, encoding="utf-8") as f:
            first = f.readline().strip()
        return first or None
    except Exception:
        return None


def _hiringcafe_urls() -> list[str]:
    """role × geo → hiring.cafe result-page URLs (robots-allowed /jobs/... path),
    capped at MAX_PAGE_LOADS as the per-run spend ceiling."""
    urls = [f"https://hiring.cafe/jobs/{r}/locations/{g}"
            for g in HIRINGCAFE_GEO_SLUGS for r in HIRINGCAFE_ROLE_SLUGS]
    return urls[:MAX_PAGE_LOADS]


# ── FILTERS ──────────────────────────────────────────────────────────────────
TITLE_MUST_INCLUDE = [
    "product manager", "associate product manager",
]
TITLE_EXCLUDE = ["marketing", "product marketing", "product designer", "product analyst"]

# Executive/org-layer titles dropped on the title alone. "Senior" and "Sr" are
# intentionally NOT in this list — many companies use them as default prefixes
# (e.g. "Senior Associate PM") without implying an elevated experience bar. The
# years gate (EXPERIENCE_CAP) handles those. Mid-title occurrences never gate
# (e.g. "Product Manager, Senior Care" passes). PM levels II/III caught at END.
_HARD_SENIOR_RE = re.compile(
    r'^\s*(?:staff|principal|lead|group|head|chief|distinguished|'
    r'director|managing\s+director|vice\s+president|vp|svp|evp)\b'
    r'|\b(?:iv|iii|ii)\b(?=\s*(?:[,\-–—]|$))',
    re.IGNORECASE,
)

# Experience bar (parametric knob). Keep roles requiring <= this many years, plus
# any role with no stated requirement. Roles explicitly requiring MORE are dropped
# at scrape time. The parsed years value is the ground truth — never the title.
EXPERIENCE_CAP = 3

NYC_LOCS    = ["new york", "nyc", "brooklyn", "manhattan"]
SF_LOCS     = [
    "san francisco", "bay area", "silicon valley", "south bay", "east bay",
    "palo alto", "mountain view", "menlo park", "redwood city",
    "san jose", "cupertino", "santa clara", "sunnyvale",
    "san mateo", "foster city", "burlingame", "pleasanton", "san carlos",
    "oakland",
]
REMOTE_LOCS = ["remote", "united states", "anywhere", "nationwide",
               "distributed", "work from anywhere", "work from home"]

# Non-target US metros. A location naming one of these (without "remote") gets
# loc_class="unknown" and is excluded by default. SF metro cities were removed —
# they are now a target geography detected by SF_LOCS above.
_US_NON_NYC = [
    "seattle", "chicago", "austin", "boston",
    "los angeles", "denver", "atlanta", "portland", "miami",
    "dallas", "houston", "phoenix",
    "bellevue", "kirkland", "cambridge", "pittsburgh",
    "philadelphia", "minneapolis", "nashville", "charlotte", "raleigh",
    "salt lake city", "san diego", "las vegas", "tampa", "orlando",
    "detroit", "cleveland", "cincinnati", "indianapolis", "st. louis",
    "kansas city", "new orleans", "richmond", "baltimore", "washington dc",
    "washington, dc", "washington, d.c", "washington",
    # US state names — catch "City, State, United States" patterns from hiring.cafe
    # so "Fort Collins, Colorado, United States" doesn't mis-classify as remote.
    # Omit: new york (NYC), california (SF Bay Area), texas/florida/illinois (cities already there).
    "colorado", "kansas", "ohio", "pennsylvania", "maryland", "georgia",
    "virginia", "kentucky", "indiana", "alabama", "tennessee", "louisiana",
    "arkansas", "mississippi", "oklahoma", "north carolina", "south carolina",
    "iowa", "nebraska", "missouri", "michigan", "minnesota", "wisconsin",
    "montana", "wyoming", "idaho", "utah", "nevada", "new mexico",
    "west virginia", "north dakota", "south dakota", "vermont", "maine",
    "new hampshire", "hawaii", "alaska", "connecticut", "delaware", "rhode island",
    "district of columbia",
]

# Country/region markers that make a role non-US even if it says "remote"
# ("Remote - Canada", "Remote, EMEA"). Used to stop foreign-remote roles from
# being classified as US-remote and slipping past the geo filter.
_INTL_MARKERS = [
    "canada", "toronto", "vancouver", "montreal", "ontario",
    "united kingdom", "london", "england", "ireland", "dublin",
    "france", "paris", "germany", "berlin", "munich", "munzstrasse",
    "netherlands", "amsterdam", "spain", "madrid", "barcelona", "aveiro",
    "portugal", "lisbon", "italy", "rome", "milan", "poland", "warsaw",
    "sweden", "stockholm", "switzerland", "zurich", "emea", "apac",
    "japan", "tokyo", "singapore", "india", "bangalore", "bengaluru",
    "australia", "sydney", "melbourne", "brazil", "sao paulo", "mexico",
    "hungary", "budapest", "israel", "tel aviv", "philippines", "manila",
]

# Keywords in description that signal the role values engineering background.
# Surfaced in terminal output as a "signal" flag — not used for filtering.
HARDWARE_SIGNAL = [
    "mechanical engineer", "hardware", "medical device", "med device", "medtech",
    "regulated", "fda", "iso 13485", "physical product", "manufacturing",
    "embedded", "firmware", "iot", "wearable", "sensor",
    "diagnostics", "clinical", "life sciences", "life-science", "biomedical",
    "surgical", "medical imaging", "point-of-care", "in vitro", "pharmaceutical",
]

LANGUAGE_SIGNAL = [
    "fluent in spanish", "fluent in french", "spanish speaker", "french speaker",
    "bilingual", "multilingual", "latam", "latin america", "francophone",
    "spanish language", "french language", "español", "français",
]

# ── COMPANIES ─────────────────────────────────────────────────────────────────
# Loaded from verified_companies.json if present; falls back to these defaults
# per-ATS (so a cache with only greenhouse slugs still gets Ashby/Lever coverage).
# Run discover.py locally to grow the cache with YC-seeded companies.
_CACHE_FILE = "verified_companies.json"

_FALLBACK_GH = [
    "betterment", "robinhood", "justworks", "mongodb", "datadog", "figma",
    "stripe", "brex", "plaid", "affirm", "sofi", "gusto", "rippling",
    "doubleverify", "pinterest", "carta", "hubspot", "webflow", "etsy",
    "duolingo", "airtable", "benchling", "cockroachlabs", "coda",
    "gemini", "navan", "whatnot", "modal", "replit",
    "hingehealth", "springhealth", "headway", "cerebral", "lyra",
    "ro", "twentyeight-health", "tempus", "color", "flatiron",
    "peloton", "whoop", "oura", "brilliant", "verkada",
    "mantrahealth", "alteradigitalhealth", "mavenclinic", "airbnb",
]
_FALLBACK_ASH = [
    "notion", "harvey", "ramp", "cohere", "linear", "supabase", "mercury",
    "vanta", "clay", "deel", "retool", "scale-ai", "perplexity", "vercel",
    "anyscale", "cursor", "glean", "watershed", "alchemy", "dbt-labs",
    "openai", "anthropic", "arc", "prefect", "runway",
    "nuvation", "sword-health", "nirahealth", "turquoise-health", "ribbon-health",
    "oneapp", "airwallex", "pivotal-health", "plaid", "brigit",
]
_FALLBACK_LEV = [
    "airbnb", "shopify", "canva", "asana", "zendesk", "squarespace",
    "intercom", "netlify", "sendbird", "postman", "contentful",
    "amplitude", "mixpanel", "pagerduty", "cloudflare", "hashicorp",
    "nuro", "veracyte",
    "tenna", "cents", "salvohealth", "mistral", "luni", "Flex",
]


def _load_companies() -> tuple[list, list, list]:
    # Preferred source: companies.db (self-cleaning, learns which slugs are live).
    # Build it with `python3 build_companydb.py`. Falls back to the JSON cache and
    # then the hardcoded lists if the DB is absent or empty.
    try:
        import companydb, os
        if os.path.exists(companydb.DB_FILE):
            gh  = companydb.load_active("greenhouse")
            ash = companydb.load_active("ashby")
            lev = companydb.load_active("lever")
            if gh or ash or lev:
                return (gh or _FALLBACK_GH, ash or _FALLBACK_ASH, lev or _FALLBACK_LEV)
    except Exception as e:
        print(f"  [warn] companies.db load failed ({e}); using JSON cache",
              file=sys.stderr)

    gh = ash = lev = None
    try:
        import os
        if os.path.exists(_CACHE_FILE):
            data = json.loads(open(_CACHE_FILE, encoding="utf-8").read())
            cand = data.get("candidates", {})
            # Merge verified slugs with the wider candidate pool. Candidates are
            # unconfirmed company guesses; a bad slug simply returns no jobs from
            # the API (harmless), while good ones widen coverage for free.
            def _merge(key):
                seen, out = set(), []
                for src in (data.get(key) or [], cand.get(key) or []):
                    for e in src:
                        s = e["slug"] if isinstance(e, dict) else e
                        if s and s not in seen:
                            seen.add(s); out.append(s)
                return out or None   # None → fall through to hardcoded fallback
            gh  = _merge("greenhouse")
            ash = _merge("ashby")
            lev = _merge("lever")
    except Exception as e:
        print(f"  [warn] could not load {_CACHE_FILE}: {e}", file=sys.stderr)
    # Fall back per-ATS so a partial cache never silently drops a whole provider.
    return (
        gh  if gh  is not None else _FALLBACK_GH,
        ash if ash is not None else _FALLBACK_ASH,
        lev if lev is not None else _FALLBACK_LEV,
    )

GREENHOUSE, ASHBY, LEVER = _load_companies()

WORKABLE: list = []
try:
    _vc_data = json.loads(open(_CACHE_FILE, encoding="utf-8").read())
    WORKABLE = _vc_data.get("workable", [])
except Exception:
    pass

# Requirement-style year patterns only. Deliberately NO bare "N years" pattern,
# so phrasing like "10 years of combined team experience" is NOT mistaken for an
# individual requirement. Each pattern's group(s) yield candidate year value(s);
# for ranges we keep the LOW end (the minimum bar to clear).
YEARS_PATTERNS = [
    # range: "3-5 years", "3 to 5 years"  → low end
    (re.compile(r'(\d+)\s*(?:–|—|-|to)\s*(\d+)\s*\+?\s*years?', re.I), "low"),
    # plus: "5+ years"
    (re.compile(r'(\d+)\s*\+\s*years?', re.I), "all"),
    # "N+ years of [≤3 words] experience" — allows "of product management experience"
    (re.compile(r'(\d+)\s*\+?\s*years?\s+of\s+(?:[\w-]+\s+){0,3}experience', re.I), "all"),
    # in-domain: "2+ in product", "5+ years in marketing"
    (re.compile(r'(\d+)\s*\+?\s*(?:years?\s+)?in\s+'
                r'(?:product|marketing|software|tech|engineering|design|'
                r'operations|consulting|business|industry)', re.I), "all"),
    # "at least N years", "minimum of N years"
    (re.compile(r'(?:at\s+least|minimum(?:\s+of)?|min\.?)\s+(\d+)\s*\+?\s*years?', re.I), "all"),
]

# A matched span containing any of these describes team/collective tenure,
# not an individual PM requirement — so it is dropped.
YEARS_DISQUALIFY = ["combined", "collective", "total", "company-wide", "across our"]

# Phrases that frame a year bar as a preferred / nice-to-have qualifier rather
# than a hard requirement. Used by _requirement_kind so a soft LOW bar
# ("Strongly Preferred: 2+ years") can't sink the gate below a hard HIGH bar
# ("Required: 5+ years") — while a plain "5+ … 2+ …" with no qualifier words
# still reads optimistically as 2 (TEST 3). Hard markers let an explicit
# "Required"/"Minimum" clause out-vote a nearby preferred header.
YEARS_SOFT_MARKERS = ("preferred", "preferably", "nice to have", "nice-to-have",
                      "bonus", "ideally", "a plus", "good to have", "desired",
                      "would be a plus", "pluses")
YEARS_HARD_MARKERS = ("required", "requirement", "must have", "must-have",
                      "minimum", "at least", "you must", "we require")

# Sentence/clause separator. _strip_html turns every <li>/<p>/<h*> into ". ",
# so each requirement bullet ends up as its own clause splittable on this.
_SENT_SEP = re.compile(r"[.!?;]\s")

# Drop roles whose posting is older than this many days (when a date is known).
# Aggregators like The Muse keep evergreen listings open for a year+; those are
# stale by any job-seeker's standard. Roles with no date are kept (can't judge).
MAX_AGE_DAYS = 3

APPLIED_FILE = "applied.csv"
GMAIL_FILE   = "gmail_applied.txt"  # synced by pmfarm_gmail_sync.py; one company per line
# Gmail dedupe is COMPANY-level (Gmail only knows a company emailed you, not which
# role), so it hides every role at any company you've applied to — too aggressive.
# OFF by default; role-level dedupe via applied.csv (URL match) is the tracking path.
GMAIL_DEDUPE = False
OUTPUT_FILE  = "pm_roles.csv"

# Populated by fetch_* functions; reset at the start of each cmd_local run.
# key = "source:slug", value = "ok" | "empty" | "fail"
_slug_resolution: dict[str, str] = {}


def _record(source: str, slug: str, status: str) -> None:
    _slug_resolution[f"{source}:{slug}"] = status


# ── helpers ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    # Unescape first so &lt;p&gt; → <p> before the tag regex runs.
    t = H.unescape(text or "")
    # Convert closing block-level tags to ". " so list items become distinct
    # pseudo-sentences that _years_sentence can split on.
    t = re.sub(r"</?(li|p|br|div|tr|h[1-6]|ul|ol|table|tbody|thead|th|td)\b[^>]*>",
               ". ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"(\.\s*){2,}", ". ", t)   # collapse ". . . " → ". "
    return re.sub(r"\s+", " ", t).strip(" .")


def _clause_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """[left, right) of the sentence/clause containing the match at [start, end).
    Because _strip_html makes every requirement bullet its own ". "-delimited
    clause, this isolates the one phrase the year number actually belongs to."""
    left = 0
    for m in _SENT_SEP.finditer(text, 0, start):
        left = m.end()
    nxt = _SENT_SEP.search(text, end)
    return left, (nxt.start() if nxt else len(text))


def _preceding_sentence(text: str, clause_left: int) -> str:
    """The sentence immediately before clause_left — catches header-style
    qualifiers like a standalone 'Strongly Preferred.' line above the bullet."""
    if clause_left <= 0:
        return ""
    head = text[:clause_left]
    seps = list(_SENT_SEP.finditer(head))
    prev = seps[-2].end() if len(seps) >= 2 else 0
    return head[prev:]


def _nearest_marker_kind(s: str, pos: int) -> str | None:
    """'soft' / 'hard' / None for the qualifier marker nearest offset `pos` in
    `s`, so the closest framing word governs the number."""
    s = s.lower()
    best_kind, best_dist = None, None
    for markers, kind in ((YEARS_SOFT_MARKERS, "soft"), (YEARS_HARD_MARKERS, "hard")):
        for mk in markers:
            i = s.find(mk)
            while i != -1:
                d = abs(i - pos)
                if best_dist is None or d < best_dist:
                    best_kind, best_dist = kind, d
                i = s.find(mk, i + 1)
    return best_kind


def _requirement_kind(text: str, start: int, end: int) -> str:
    """'soft' if the year bar at [start, end) is framed as preferred/nice-to-have,
    else 'hard'. The number's OWN clause wins outright; only a clause with no
    marker falls back to its preceding header sentence. This keeps a trailing
    qualifier in one clause ('5+ years preferred. 2+ years required.') from
    leaking onto the next number. Unmarked → 'hard'."""
    left, right = _clause_bounds(text, start, end)
    kind = _nearest_marker_kind(text[left:right], start - left)
    if kind is None:
        head = _preceding_sentence(text, left)
        kind = _nearest_marker_kind(head, len(head))
    return kind or "hard"


def _parse_years(text: str) -> tuple[str, str]:
    """Return (years_raw, years_context).

    Honest-by-design: collects every requirement-style year mention, drops
    team/collective-tenure phrasing, and reports the MINIMUM HARD bar found (the
    most optimistic read, so you never self-reject). A bar framed as preferred /
    nice-to-have is set aside so it can't pull the gate below a real requirement
    — but if a posting states ONLY soft bars, those still count (a sole
    "preferred 8+ years" drops as before). The context column shows every matched
    phrase so you can catch the number if it's lying. No match → unknown.
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
            s   = max(0, m.start() - 30)
            e   = min(len(text), m.end() + 30)
            ctx = "…" + text[s:e].replace("\n", " ").strip() + "…"
            if ctx not in contexts:
                contexts.append(ctx)

    # Gate on hard requirements; soft bars only count when there are no hard
    # ones, so the optimistic low-end never falls onto a "preferred" qualifier.
    pool = hard or soft
    if not pool:
        return ("unknown", "")
    return (str(min(pool)), " | ".join(contexts[:3]))


def _years_sentence(text: str) -> str:
    """Return the first verbatim sentence containing 'year(s)' from the JD content,
    else 'not stated'. SCRAPER_RULES: the years field must be the exact JD sentence,
    never a bucket or a derived number. Run on FULL content, not a truncation."""
    t = re.sub(r"\s+", " ", _strip_html(text or "")).strip()
    for sentence in re.split(r"(?<=[.!?])\s+", t):
        if re.search(r"\byears?\b", sentence, re.I):
            return sentence.strip()[:300]
    return "not stated"


def _norm_url(url: str) -> str:
    """Normalize a job URL for reliable dedupe: lowercase, force https, strip
    query string / fragment / trailing slash. Defeats false misses from
    ?gh_jid=, ?gh_src=, http vs https, and trailing-slash variants."""
    u = (url or "").strip().lower()
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    u = u.split("?", 1)[0].split("#", 1)[0]
    return u.rstrip("/")


def _loc_class(location: str, snippet: str = "") -> str:
    # Classification uses only the location field, not the JD snippet, to prevent
    # body text like "remote work options" from misclassifying in-office roles.
    loc_lower = location.lower()
    has_nyc = any(n in loc_lower for n in NYC_LOCS)
    has_sf  = any(s in loc_lower for s in SF_LOCS)

    # A named foreign country/region makes this international unless it also names
    # a target city — "London + San Francisco" is still a SF role.
    has_intl = any(m in loc_lower for m in _INTL_MARKERS)
    if has_intl and not has_nyc and not has_sf:
        return "international"

    # Explicit "remote" in the location field always wins.
    has_explicit_remote = "remote" in loc_lower

    # Generic US terms only count when no specific non-target city is present,
    # preventing "Seattle, United States" from matching as remote.
    has_non_target_us = any(c in loc_lower for c in _US_NON_NYC)
    has_us_generic    = (not has_non_target_us) and any(r in loc_lower for r in REMOTE_LOCS)

    has_remote = has_explicit_remote or has_us_generic

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


def _days_old(date_str: str | None) -> str:
    if not date_str:
        return "unknown"
    try:
        dt    = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        delta = datetime.datetime.now(datetime.timezone.utc) - dt
        return str(delta.days)
    except Exception:
        return "unknown"


def _passes_title(title: str) -> bool:
    t = title.lower()
    if not any(kw in t for kw in TITLE_MUST_INCLUDE):
        return False
    if any(kw in t for kw in TITLE_EXCLUDE):
        return False
    # Only unambiguous executive titles disqualify on the title alone. Seniority
    # otherwise is enforced by the stated-years gate (EXPERIENCE_CAP) downstream,
    # so a "Senior Associate" or a "Senior PM" with a <=3yr bar is NOT dropped here.
    if _HARD_SENIOR_RE.search(t):
        return False
    return True


def _passes_location(lc: str, remote_only: bool, include_unknown: bool = False) -> bool:
    if remote_only:
        allowed = {"remote", "remote+nyc", "remote+sf", "remote+nyc+sf"}
    else:
        allowed = {"remote", "remote+nyc", "nyc",
                   "sf", "remote+sf", "nyc+sf", "remote+nyc+sf"}
    if include_unknown:
        allowed.add("unknown")
    return lc in allowed


def _ct_key(company: str, title: str) -> str:
    return f"{company.strip().lower()}|{title.strip().lower()}"


def _normalize_company(name: str) -> str:
    """Lowercase + strip all non-alphanumeric chars for Gmail company matching.
    'Globex' → 'globex'; 'Stark Industries' → 'starkindustries'; 'stark-industries' (slug) → 'starkindustries'.
    Known false-negative class: a display name that differs from its ATS slug
    (e.g. 'Acme' vs slug 'acme-labs') won't match — add it to applied.csv manually."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _gmail_applied_set() -> tuple[set[str], list[tuple]]:
    """Read gmail_applied.txt. Returns (normalized_company_set, evidence_list).
    Each evidence entry: (normalized_name, raw_name, subject_line, date_str).
    Silently returns empty set if the file is absent (Gmail dedupe disabled)."""
    companies: set[str] = set()
    evidence:  list[tuple] = []
    try:
        with open(GMAIL_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t", 2)
                raw  = parts[0].strip()
                subj = parts[1].strip() if len(parts) > 1 else ""
                date = parts[2].strip() if len(parts) > 2 else ""
                norm = _normalize_company(raw)
                if norm:
                    companies.add(norm)
                    evidence.append((norm, raw, subj, date))
    except FileNotFoundError:
        print(f"  ℹ  {GMAIL_FILE} not found — Gmail dedupe disabled. "
              "Run: python3 pmfarm_gmail_sync.py", file=sys.stderr)
    return companies, evidence


def _load_applied() -> set[str]:
    seen: set[str] = set()
    try:
        with open(APPLIED_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("url"):
                    seen.add(_norm_url(row["url"]))
                if row.get("company") and row.get("title"):
                    seen.add(_ct_key(row["company"], row["title"]))
    except FileNotFoundError:
        pass
    return seen


def _deduped(jobs: list[dict], applied: set[str]) -> list[dict]:
    out, seen = [], set()
    for j in jobs:
        nu = _norm_url(j["url"])
        ck = _ct_key(j["company"], j["title"])
        if nu in applied or ck in applied:
            continue
        # Within-run dupe: aggregators (The Muse) repeat one role under several
        # location groupings — same company+title is the same job.
        if nu in seen or ck in seen:
            continue
        seen.add(nu)
        seen.add(ck)
        out.append(j)
    return out


def _make_job(source, company, title, location, url, snippet, date_str,
              full_content=None) -> dict:
    content        = full_content if full_content is not None else snippet
    lc             = _loc_class(location)
    years_raw, yc  = _parse_years(content)
    years_sentence = _years_sentence(content)
    body_lower     = (title + " " + content).lower()
    return {
        "source":         source,
        "company":        company,
        "title":          title,
        "location":       location,
        "loc_class":      lc,
        "url":            url,
        "days_old":       _days_old(date_str),
        "years_raw":      years_raw,
        "years_context":  yc,
        "years_sentence": years_sentence,
        "hw_signal":      "YES" if any(kw in body_lower for kw in HARDWARE_SIGNAL) else "",
        "lang_signal":    "YES" if any(kw in body_lower for kw in LANGUAGE_SIGNAL) else "",
        "applied":        "",
    }


# ── ATS fetchers ──────────────────────────────────────────────────────────────

def _fetch(url: str) -> dict | list | None:
    req = urllib.request.Request(url, headers={"User-Agent": "pmfarm/3.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch_greenhouse(slug: str) -> list[dict]:
    data = _fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    if not isinstance(data, dict):
        _record("GH", slug, "fail")
        return []
    out = []
    for j in data.get("jobs", []):
        title = j.get("title", "")
        if not _passes_title(title):
            continue
        loc      = j.get("location", {})
        location = loc.get("name", "") if isinstance(loc, dict) else ""
        content  = _strip_html(j.get("content", ""))
        out.append(_make_job(
            "Greenhouse", slug, title, location,
            j.get("absolute_url", ""), content[:500],
            j.get("updated_at"), full_content=content,
        ))
    _record("GH", slug, "ok" if out else "empty")
    return out


def fetch_ashby(slug: str) -> list[dict]:
    data = _fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not data:
        _record("Ashby", slug, "fail")
        return []
    jobs = data if isinstance(data, list) else data.get("jobPostings", [])
    out  = []
    for j in jobs:
        title = j.get("title", "") or j.get("jobTitle", "")
        if not _passes_title(title):
            continue
        location = j.get("location", "") or j.get("locationName", "")
        content  = _strip_html(j.get("descriptionHtml", "") or j.get("description", ""))
        out.append(_make_job(
            "Ashby", slug, title, location,
            j.get("jobUrl", "") or j.get("applyUrl", ""), content[:500],
            None,   # Ashby does not reliably expose a post date
            full_content=content,
        ))
    _record("Ashby", slug, "ok" if out else "empty")
    return out


def fetch_lever(slug: str) -> list[dict]:
    data = _fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=250")
    if not data:
        _record("Lever", slug, "fail")
        return []
    jobs = data if isinstance(data, list) else data.get("postings", [])
    out  = []
    for j in jobs:
        title = j.get("text", "")
        if not _passes_title(title):
            continue
        cats     = j.get("categories", {})
        location = cats.get("location", "")
        lists_text = " ".join(_strip_html(li.get("content", "")) for li in j.get("lists", []))
        desc_text  = _strip_html(j.get("descriptionPlain", ""))
        content    = f"{lists_text} {desc_text}".strip()
        ts       = j.get("createdAt")
        date_str = (datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone.utc).isoformat().replace("+00:00", "Z")) if ts is not None else None
        out.append(_make_job(
            "Lever", slug, title, location,
            j.get("hostedUrl", ""), content[:500],
            date_str, full_content=content,
        ))
    _record("Lever", slug, "ok" if out else "empty")
    return out


def fetch_workable(slug: str) -> list[dict]:
    """Fetch open roles from Workable's public API — no auth required."""
    url  = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
    data = _fetch(url)
    out  = []
    for j in (data or {}).get("results", []):
        title = j.get("title", "")
        if not _passes_title(title):
            continue
        city = (j.get("location") or {}).get("city", "")
        lc   = _loc_class(city)
        if not _passes_location(lc, False):
            continue
        out.append(_make_job(
            "workable", slug, title, city,
            f"https://apply.workable.com/{slug}/j/{j.get('shortcode', '')}",
            "", j.get("created_at"),
        ))
    return out


# ── The Muse API (free, no key required) ─────────────────────────────────────
# Public job search API focused on tech/startup companies. Has native entry-level
# filters and returns structured JSON with company name, location, and a direct
# link to the role on The Muse. No auth, no rate-limit concerns at this volume.
MUSE_MAX_PAGES = 5   # 20 results/page × 5 pages = 100 roles scanned


def fetch_muse() -> list[dict]:
    if not SOURCES.get("muse"):
        return []
    out = []
    for page in range(MUSE_MAX_PAGES):
        url  = "https://www.themuse.com/api/public/jobs?" + urllib.parse.urlencode(
            {"category": "Product Management", "page": page, "descending": "true"}
        )
        data = _fetch(url)
        results = (data or {}).get("results", [])
        if not results:
            break
        for r in results:
            title   = r.get("name", "")
            company = r.get("company", {}).get("name", "")
            locs    = ", ".join(l["name"] for l in r.get("locations", []))
            lc      = _loc_class(locs)
            if not _passes_title(title):
                continue
            if not _passes_location(lc, False, True):
                continue
            out.append(_make_job(
                "muse", company, title, locs,
                r.get("refs", {}).get("landing_page", ""),
                "", r.get("publication_date"),
            ))
    print(f"  fetch_muse: {len(out)} roles")
    return out


# ── Bright Data / hiring.cafe (Web Unlocker REST API) ────────────────────────
# hiring.cafe is JS-gated and unreachable by the urllib fetchers above. Its
# robots.txt allows /jobs/<role>/locations/<geo> result pages (but blocks the
# ?searchState= search and /job/ detail pages), and each result page embeds the
# full job list as structured JSON in a __NEXT_DATA__ script tag — including the
# DIRECT company apply_url, company_name, location, post date, and a structured
# min years-of-experience. We fetch those pages via Bright Data's Web Unlocker
# REST API (~$1.50/1k requests) and parse the JSON ourselves — no CLI, no npm,
# no Scraper Studio collector needed. Rows map into the standard _make_job()
# shape and flow through the EXACT same experience gate + dedupe as the ATS rows
# in cmd_local; no filtering logic is duplicated here.
#
# INERT by default — returns [] unless SOURCES["brightdata"] is True AND
# brightdata_key.txt holds an API key. Cost is guarded four ways:
#   1. inert-by-default toggle SOURCES["brightdata"] — the master spend switch;
#   2. once-per-day lock (BRIGHTDATA_MIN_HOURS) so a manual re-run cannot re-bill;
#   3. MAX_PAGE_LOADS — hard cap on pages fetched per run (the real spend ceiling);
#   4. role/geo slug lists keep the URL set small and on-target.


def _bd_recent_run() -> bool:
    """True if a paid brightdata run completed < BRIGHTDATA_MIN_HOURS ago. Backs the
    once-per-day spend lock so a manual re-run cannot trigger repeated paid scrapes."""
    try:
        ts = float(open(_BRIGHTDATA_RUN_STAMP).read().strip())
        return (datetime.datetime.now().timestamp() - ts) < BRIGHTDATA_MIN_HOURS * 3600
    except Exception:
        return False


def _hiringcafe_hits(html: str) -> list[dict]:
    """Extract the ssrHits job array from a hiring.cafe result page's __NEXT_DATA__."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []
    hits = ((data.get("props") or {}).get("pageProps") or {}).get("ssrHits")
    return hits if isinstance(hits, list) else []


def _hiringcafe_job(h: dict) -> dict | None:
    """Map one hiring.cafe ssrHit into the standard _make_job() shape, or None if it
    fails the title gate or has no apply link. Folds the structured min years-of-
    experience + requirements text into `content` so the SAME _parse_years gate
    downstream sees the requirement (hiring.cafe gives a clean number when stated)."""
    v5 = h.get("v5_processed_job_data") or {}
    ji = h.get("job_information") or {}
    title = (ji.get("title") or v5.get("core_job_title") or "").strip()
    url   = (h.get("apply_url") or "").strip()
    if not title or not url or not _passes_title(title):
        return None
    company  = (v5.get("company_name")
                or (h.get("enriched_company_data") or {}).get("name") or "(unknown)")
    location = v5.get("formatted_workplace_location") or ""
    date_str = None  # estimated_publish_date reflects original post date, not last-active; treat like Ashby (no reliable date)
    parts: list[str] = []
    yoe = v5.get("min_industry_and_role_yoe")
    if not v5.get("is_min_industry_and_role_yoe_not_mentioned") and yoe is not None:
        parts.append(f"{yoe}+ years experience required")   # so _parse_years can read the bar
    if v5.get("requirements_summary"):
        parts.append(str(v5["requirements_summary"]))
    content = _strip_html(". ".join(parts)) or title
    return _make_job("hiring.cafe", company, title, location,
                     url, content[:500], date_str, full_content=content)


def _bd_fetch_html(url: str, api_key: str) -> str:
    """Fetch a JS-rendered page via Bright Data Web Unlocker REST API."""
    payload = json.dumps({
        "zone": BRIGHTDATA_UNLOCKER_ZONE,
        "url": url,
        "format": "raw",
    }).encode()
    req = urllib.request.Request(
        "https://api.brightdata.com/request",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_brightdata() -> list[dict]:
    # 1. Inert unless explicitly enabled AND an API key exists.
    if not SOURCES.get("brightdata"):
        return []
    api_key = _load_brightdata_key()
    if not api_key:
        print("  [brightdata] inert: no API key (set BRIGHTDATA_API_KEY env var or brightdata_key.txt)", file=sys.stderr)
        return []

    # 2. Once-per-day spend lock — a manual re-run within the window is free.
    if _bd_recent_run():
        print(f"  [brightdata] skipped: a paid run completed < {BRIGHTDATA_MIN_HOURS}h ago "
              f"(spend lock). Delete {os.path.basename(_BRIGHTDATA_RUN_STAMP)} to force a re-run.",
              file=sys.stderr)
        return []

    # 3. Fetch each role×geo result page via the REST API. The first successful
    #    (billed) request stamps the spend lock so a manual re-run is free.
    urls = _hiringcafe_urls()
    out: list[dict] = []
    pages_ok = stamped = 0
    for url in urls:
        try:
            html = _bd_fetch_html(url, api_key)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            print(f"  [brightdata] HTTP {e.code} (zone='{BRIGHTDATA_UNLOCKER_ZONE}'): {body}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"  [brightdata] fetch failed ({url}): {e}", file=sys.stderr)
            continue
        if not stamped:
            try:
                open(_BRIGHTDATA_RUN_STAMP, "w").write(str(datetime.datetime.now().timestamp()))
            except Exception:
                pass
            stamped = 1
        pages_ok += 1
        for h in _hiringcafe_hits(html):
            j = _hiringcafe_job(h)
            if j:
                out.append(j)

    print(f"  fetch_brightdata: {pages_ok}/{len(urls)} hiring.cafe pages -> "
          f"{len(out)} matched title filter")
    return out


# ── output ─────────────────────────────────────────────────────────────────────

def _sort_key(j: dict) -> tuple:
    loc_order = {
        "remote": 0, "remote+nyc": 1, "remote+sf": 1, "remote+nyc+sf": 1,
        "nyc": 2, "sf": 2, "nyc+sf": 2,
        "unknown": 3,
    }
    order = loc_order.get(j["loc_class"], 4)
    try:
        age = int(j["days_old"])
    except (ValueError, TypeError):
        age = 9999
    return (order, age)


def _output(jobs: list[dict], skipped: int = 0):
    jobs.sort(key=_sort_key)

    print(f"\n{'-' * 72}")
    for j in jobs:
        age = f"{j['days_old']}d" if j["days_old"] != "unknown" else "?d"
        yrs = j["years_raw"] if j["years_raw"] != "unknown" else "?"
        hw   = "  *** HW/MEDTECH SIGNAL ***" if j.get("hw_signal") else ""
        lang = "  [LANG]" if j.get("lang_signal") else ""
        print(f"[{j['source']:11s}] {j['company']:18s}  {j['title']}{hw}{lang}")
        print(f"  {(j['location'] or j['loc_class']):32s}  age={age:<6s}  yrs_req={yrs}")
        if j["years_context"]:
            print(f"  \"{j['years_context'][:90]}\"")
        print(f"  {j['url']}\n")

    if skipped:
        print(f"(skipped {skipped} already-applied role(s) from {APPLIED_FILE})\n")

    fields = ["source", "company", "title", "location", "loc_class",
              "url", "days_old", "years_raw", "years_context", "years_sentence",
              "hw_signal", "lang_signal", "applied"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(jobs)
    print(f"Saved {len(jobs)} role(s) -> {OUTPUT_FILE}")
    print(f"Fill the 'applied' column as you go. Save as {APPLIED_FILE} to dedupe next run.")


# ── local mode ────────────────────────────────────────────────────────────────

def cmd_local(remote_only: bool, include_unknown_loc: bool = False):
    _slug_resolution.clear()

    # ── Gmail company-level dedupe (OFF by default — see GMAIL_DEDUPE) ─────────
    if GMAIL_DEDUPE:
        gmail_set, gmail_evidence = _gmail_applied_set()
        print(f"\nGmail applied set: {len(gmail_set)} companies")
        if gmail_set:
            for norm, raw, subj, date in sorted(gmail_evidence, key=lambda x: x[0]):
                print(f"  {raw:<28s} <- \"{subj[:55]}\"  ({date[:10]})")
        else:
            print("  (none — run python3 pmfarm_gmail_sync.py to enable)")
    else:
        gmail_set, gmail_evidence = set(), []
        print("\nGmail dedupe OFF — companies shown even if you've applied "
              "(role-level dedupe via applied.csv stays active)")

    # ── ATS fetch (each provider gated by its SOURCES toggle) ─────────────────
    tasks: list[tuple] = []
    if SOURCES.get("greenhouse"):
        tasks += [(fetch_greenhouse, s) for s in GREENHOUSE]
    if SOURCES.get("ashby"):
        tasks += [(fetch_ashby, s) for s in ASHBY]
    if SOURCES.get("lever"):
        tasks += [(fetch_lever, s) for s in LEVER]
    if SOURCES.get("workable"):
        tasks += [(fetch_workable, s) for s in WORKABLE]

    raw: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(fn, slug): (fn.__name__, slug) for fn, slug in tasks}
        for fut in as_completed(futs, timeout=120):
            fn_name, slug = futs[fut]
            try:
                rows = fut.result()
                if rows:
                    print(f"  {fn_name}({slug}): {len(rows)} matched title filter")
                raw.extend(rows)
            except Exception as e:
                print(f"  {fn_name}({slug}) error: {e}", file=sys.stderr)

    # ── Adzuna search (dynamic discovery — no slug list needed) ──────────────────
    # Searches by title+location across ALL companies. Catches any company posting
    # a PM role in NYC/SF regardless of which ATS they use. Inert without keys.
    if SOURCES.get("adzuna"):
        try:
            raw.extend(fetch_adzuna())
        except Exception as e:
            print(f"  [adzuna] FAILED: {e}", file=sys.stderr)

    # ── The Muse API (free, no key required) ──────────────────────────────────
    if SOURCES.get("muse"):
        try:
            raw.extend(fetch_muse())
        except Exception as e:
            print(f"  [muse] FAILED: {e}", file=sys.stderr)

    # ── Bright Data / hiring.cafe (gated source) ──────────────────────────────
    # Inert unless SOURCES["brightdata"] is True AND brightdata_key.txt is set up.
    # Its rows join `raw` and pass through the SAME freshness + experience gate +
    # location filter + dedupe below as the ATS rows.
    if SOURCES.get("brightdata"):
        try:
            raw.extend(fetch_brightdata())
        except Exception as e:
            print(f"  [brightdata] FAILED: {e}", file=sys.stderr)

    # ── ATS-DIRECT ONLY ──────────────────────────────────────────────────────
    # Every role comes from Greenhouse/Ashby/Lever (and, once enabled, hiring.cafe
    # direct apply links), whose URLs are the company's own application page — a
    # clean direct link, every time. Job-board aggregators are deliberately avoided:
    # they redirect through their own domains rather than the employer's apply page.

    # ── freshness filter: drop stale postings with a known age > MAX_AGE_DAYS ──
    def _too_old(j: dict) -> bool:
        try:
            return int(j["days_old"]) > MAX_AGE_DAYS
        except (ValueError, TypeError):
            return False   # unknown age → keep (can't judge)
    stale = [j for j in raw if _too_old(j)]
    if stale:
        print(f"\nDropped {len(stale)} stale role(s) older than {MAX_AGE_DAYS}d "
              f"(e.g. {', '.join(sorted({j['company'] for j in stale}))[:80]})")
    raw = [j for j in raw if not _too_old(j)]

    # ── experience-bar gate (hard requirement): drop ONLY roles that explicitly
    #    state more than EXPERIENCE_CAP years. Unstated years and 0-EXPERIENCE_CAP
    #    both pass. years_raw is the optimistic low-end from _parse_years, so a
    #    "3-5 years" role reads as 3 and is kept. Title seniority never gates here.
    def _over_bar(j: dict) -> bool:
        try:
            return int(j["years_raw"]) > EXPERIENCE_CAP
        except (ValueError, TypeError):
            return False   # "unknown" / unstated → keep
    over = [j for j in raw if _over_bar(j)]
    if over:
        print(f"Dropped {len(over)} role(s) explicitly requiring >{EXPERIENCE_CAP}yrs "
              f"(e.g. {', '.join(sorted({j['company'] for j in over}))[:80]})")
    raw = [j for j in raw if not _over_bar(j)]

    # ── location filter (unknown excluded by default — P2) ───────────────────
    unknown_count = sum(1 for j in raw if j["loc_class"] == "unknown")
    filtered = [j for j in raw if _passes_location(j["loc_class"], remote_only, include_unknown_loc)]
    excluded_unknown = sum(1 for j in raw if j["loc_class"] == "unknown"
                          and not _passes_location("unknown", remote_only, include_unknown_loc))

    # ── applied.csv URL/name dedupe (fallback, manual) ────────────────────────
    applied = _load_applied()
    pre_url = len(filtered)
    url_deduped = _deduped(filtered, applied)
    skipped_url = pre_url - len(url_deduped)

    # ── aggregator variant-name collapse ──────────────────────────────────────
    # Aggregators (Adzuna) list one role under different spellings of the company
    # ("JPMorganChase" vs "JPMorgan Chase Bank, National Association"), which the
    # exact-string _ct_key cannot catch. Treat two rows as the same job when their
    # titles match and one normalized company name is a prefix of the other. Keep
    # the row from the more authoritative source (direct ATS over aggregator).
    _SRC_RANK = {"greenhouse": 0, "ashby": 0, "lever": 0, "workable": 0,
                 "hiring.cafe": 1, "muse": 2, "adzuna": 3}
    pre_collapse = len(url_deduped)
    collapsed: list[dict] = []
    for j in sorted(url_deduped, key=lambda r: _SRC_RANK.get(r.get("source", "").lower(), 4)):
        jt, jc = j["title"].strip().lower(), _normalize_company(j["company"])
        is_dup = any(
            k["title"].strip().lower() == jt
            and (kc := _normalize_company(k["company"]))
            and jc and min(len(jc), len(kc)) >= 6
            and (jc.startswith(kc) or kc.startswith(jc))
            for k in collapsed
        )
        if not is_dup:
            collapsed.append(j)
    n_collapsed = pre_collapse - len(collapsed)
    if n_collapsed:
        print(f"Collapsed {n_collapsed} aggregator duplicate(s) (same role, variant company name)")
    url_deduped = collapsed

    # ── Gmail company-level dedupe ────────────────────────────────────────────
    gmail_skipped: list[tuple] = []
    jobs: list[dict] = []
    if gmail_set:
        for j in url_deduped:
            norm = _normalize_company(j["company"])
            if norm in gmail_set:
                ev = next((e for e in gmail_evidence if e[0] == norm), None)
                gmail_skipped.append((j, ev))
            else:
                jobs.append(j)
    else:
        jobs = url_deduped

    if gmail_skipped:
        print(f"\nRoles skipped by Gmail dedupe: {len(gmail_skipped)}")
        for j, ev in gmail_skipped[:10]:
            ev_str = (f"\"{ev[2][:50]}\" ({ev[3][:10]})" if ev
                      else f"\"{j['company']}\" matched")
            print(f"  {j['company']:<24s} {j['title'][:45]}")
            print(f"    <- {ev_str}")
        if len(gmail_skipped) > 10:
            print(f"  … and {len(gmail_skipped) - 10} more")

    _NYC_CLASSES = {"nyc", "remote+nyc", "nyc+sf", "remote+nyc+sf"}
    _SF_CLASSES  = {"sf",  "remote+sf",  "nyc+sf", "remote+nyc+sf"}
    nyc_count    = sum(1 for j in filtered if j["loc_class"] in _NYC_CLASSES)
    sf_count     = sum(1 for j in filtered if j["loc_class"] in _SF_CLASSES)
    remote_count = sum(1 for j in filtered if "remote" in j["loc_class"])
    print(f"\n{len(raw)} title-matched -> {len(filtered)} after location "
          f"(NYC={nyc_count} SF={sf_count} remote={remote_count} excluded-unknown={excluded_unknown}) "
          f"-> {len(url_deduped)} after URL-dedupe -> {len(jobs)} after Gmail-dedupe")
    if skipped_url:
        print(f"(also skipped {skipped_url} by applied.csv URL/name match)")
    if excluded_unknown and not include_unknown_loc:
        print(f"(tip: --include-unknown-loc to see the {excluded_unknown} unclassified roles)")

    # ── slug resolution table (P4 observability) ──────────────────────────────
    if _slug_resolution:
        ok_n    = sum(1 for v in _slug_resolution.values() if v == "ok")
        empty_n = sum(1 for v in _slug_resolution.values() if v == "empty")
        fail_n  = sum(1 for v in _slug_resolution.values() if v == "fail")
        total_n = len(_slug_resolution)
        print(f"\nSlug hit-rate: {ok_n}/{total_n} with PM roles | "
              f"{empty_n} resolved-empty | {fail_n} failed (404/timeout)")
        if fail_n:
            failed = [k for k, v in sorted(_slug_resolution.items()) if v == "fail"]
            print("  Failed slugs: " + ", ".join(failed[:20])
                  + (f" … +{fail_n - 20} more" if fail_n > 20 else ""))

        # Persist this run's outcomes so companies.db self-cleans: live slugs
        # rise, repeatedly-failing ones get pruned from future runs.
        try:
            import companydb, os
            if os.path.exists(companydb.DB_FILE):
                companydb.record_results(_slug_resolution)
                print(f"  (recorded results to {companydb.DB_FILE})")
        except Exception as e:
            print(f"  [warn] could not update companies.db: {e}", file=sys.stderr)

    _output(jobs, 0)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Role scraper — PM · TPM · FDE · SE · SA · BizOps · StratOps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--remote-only", action="store_true",
                   help="Remote/US-wide roles only; drop NYC-specific listings")
    p.add_argument("--include-unknown-loc", action="store_true",
                   help="Include roles whose location could not be classified")
    args = p.parse_args()

    cmd_local(args.remote_only, args.include_unknown_loc)


if __name__ == "__main__":
    main()
