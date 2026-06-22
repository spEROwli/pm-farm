#!/usr/bin/env python3
"""
discover.py — Grow verified_companies.json by seeding from multiple company sources.

Modes:

  python3 discover.py                    # fetch YC NYC+SF companies, probe ATS slugs, update cache
  python3 discover.py --dry-run          # same, but only print findings, don't write
  python3 discover.py --from-adzuna      # seed company names from Adzuna PM search results
  python3 discover.py --from-forbes      # seed from Forbes Cloud 100 list (__NEXT_DATA__ JSON)
  python3 discover.py --from-a16z        # seed from a16z portfolio (static fetch; BD fallback)
  python3 discover.py <flag> --dry-run   # dry-run any of the above

Requires local/non-container execution — the container blocks outbound HTTP to
ATS boards. Run this on your laptop once a week to expand the slug cache, then
commit verified_companies.json and it's available in every future Claude Code run.

Discovery pipeline (all modes):
  1. Fetch company names from the source
  2. For each company, probe Greenhouse → Ashby → Lever with a slug guess
     (slug guess = company name lowercased, punctuation stripped, spaces → hyphens)
  3. If a board resolves AND has >= 1 role matching TITLE_MUST_INCLUDE → add to cache
  4. Persist verified_companies.json

The yc-oss API is a GitHub Pages-hosted mirror of YC's Algolia index:
  https://yc-oss.github.io/api/companies/all.json
"""

import json, re, sys, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

from pmfarm import TITLE_MUST_INCLUDE, NYC_LOCS, SF_LOCS

CACHE_FILE         = Path("verified_companies.json")
YC_API_URL         = "https://yc-oss.github.io/api/companies/all.json"
FORBES_CLOUD100_URL = "https://www.forbes.com/lists/cloud100/"
A16Z_PORTFOLIO_URL  = "https://a16z.com/portfolio/"
GEO_STRINGS        = NYC_LOCS + SF_LOCS
TITLE_MUST         = TITLE_MUST_INCLUDE
MAX_WORKERS        = 12
PROBE_DELAY        = 0.15   # seconds between probes to avoid rate-limit

# ── slug guessing ─────────────────────────────────────────────────────────────

def _guess_slug(name: str) -> list[str]:
    """Return ordered list of slug candidates for a company name."""
    base = name.lower().strip()
    variants = [
        re.sub(r"[^a-z0-9]+", "-", base).strip("-"),   # hyphens
        re.sub(r"[^a-z0-9]+", "",  base),               # no separator
        re.sub(r"\s+",         "-", base.split(",")[0]).strip("-"),  # first word group
    ]
    # strip common suffixes
    for suffix in (" inc", " corp", " llc", " co", " ai", " health", " labs"):
        stripped = re.sub(r"[^a-z0-9]+", "-", base.replace(suffix, "")).strip("-")
        if stripped not in variants:
            variants.append(stripped)
    return list(dict.fromkeys(v for v in variants if v))  # dedupe, keep order


# ── ATS probers ───────────────────────────────────────────────────────────────

def _get(url: str) -> dict | list | None:
    req = urllib.request.Request(url, headers={"User-Agent": "pmfarm-discover/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _fetch_html(url: str) -> str | None:
    """Fetch a page and return raw HTML. Used for Next.js / JS-rendered sources."""
    req = urllib.request.Request(url, headers={"User-Agent": "pmfarm-discover/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _has_pm_role(jobs: list[dict], title_key: str) -> bool:
    for j in jobs:
        t = (j.get(title_key) or "").lower()
        if any(kw in t for kw in TITLE_MUST):
            return True
    return False


def _probe_greenhouse(slug: str) -> bool:
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if not data:
        return False
    return _has_pm_role(data.get("jobs", []), "title")


def _probe_ashby(slug: str) -> bool:
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not data:
        return False
    jobs = data if isinstance(data, list) else data.get("jobPostings", [])
    return _has_pm_role(jobs, "title")


def _probe_lever(slug: str) -> bool:
    data = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=50")
    if not data:
        return False
    jobs = data if isinstance(data, list) else data.get("postings", [])
    return _has_pm_role(jobs, "text")


PROBERS = [
    ("greenhouse", _probe_greenhouse),
    ("ashby",      _probe_ashby),
    ("lever",      _probe_lever),
]


# ── cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {"greenhouse": [], "ashby": [], "lever": [], "yc": []}


def _known_slugs(cache: dict) -> set[str]:
    out = set()
    for ats_list in cache.values():
        if isinstance(ats_list, list):
            out.update(e["slug"] for e in ats_list if isinstance(e, dict))
    return out


def _save_cache(cache: dict):
    for ats in ["greenhouse", "ashby", "lever", "yc"]:
        cache.setdefault(ats, [])
    cache.get("_meta", {}) and cache.update({
        "_meta": {**cache["_meta"], "last_updated": __import__("datetime").date.today().isoformat()}
    })
    CACHE_FILE.write_text(json.dumps(cache, indent=2))
    print(f"  Saved {CACHE_FILE}")


# ── main ──────────────────────────────────────────────────────────────────────

def discover(dry_run: bool = False):
    print("Fetching YC company directory…")
    all_cos = _get(YC_API_URL)
    if not all_cos:
        print("ERROR: Could not fetch YC API. Are you running locally (not in container)?")
        sys.exit(1)
    print(f"  {len(all_cos)} companies total")

    # Filter to NYC/SF-adjacent companies with open jobs.
    # NB: the yc-oss schema uses `isHiring` (not `hiring`) and carries location in
    # `all_locations` (a string) + `regions` (a list) — older field names silently
    # matched nothing.
    candidates = []
    for co in all_cos:
        if not co.get("isHiring"):
            continue
        loc = (str(co.get("all_locations") or "") + " " +
               " ".join(co.get("regions") or [])).lower()
        if not any(n in loc for n in GEO_STRINGS):
            continue
        candidates.append(co)

    print(f"  {len(candidates)} NYC/SF companies currently hiring")

    cache    = _load_cache()
    known    = _known_slugs(cache)
    found    = 0

    for co in candidates:
        name = co.get("name") or co.get("company_name") or ""
        if not name:
            continue

        for slug in _guess_slug(name):
            if slug in known:
                break  # already cached

            for ats_name, prober in PROBERS:
                time.sleep(PROBE_DELAY)
                try:
                    if prober(slug):
                        entry = {
                            "slug": slug,
                            "name": name,
                            "tags": ["nyc"],
                            "yc_batch": co.get("batch", ""),
                        }
                        if not dry_run:
                            cache[ats_name].append(entry)
                            known.add(slug)
                        print(f"  + [{ats_name:12s}] {slug:30s}  ({name})")
                        found += 1
                        break  # found ATS, skip other probers
                except Exception as e:
                    print(f"    probe error {ats_name}/{slug}: {e}", file=sys.stderr)

    if not dry_run and found:
        _save_cache(cache)

    print(f"\nDone. {found} new {'(dry-run, not saved)' if dry_run else 'companies added to cache'}.")


# ── Adzuna → direct ATS promotion ────────────────────────────────────────────

def discover_from_adzuna(dry_run: bool = False) -> None:
    """
    Use Adzuna as a company-name seed: pull its PM search results, extract
    unique company names, then probe Greenhouse / Ashby / Lever for each one
    using the same slug-guessing logic as the YC path.

    Companies found this way get added to verified_companies.json and are
    hit directly on every future scrape — no Adzuna key needed for them again.

    Usage:
        python3 discover.py --from-adzuna          # live run
        python3 discover.py --from-adzuna --dry-run
    """
    from pmfarm import _load_adzuna_keys, ADZUNA_SEARCHES, ADZUNA_COUNTRY, MAX_AGE_DAYS

    app_id, app_key = _load_adzuna_keys()
    if not app_id or not app_key:
        print("No Adzuna keys. Set adzuna_key.txt or ADZUNA_APP_ID/ADZUNA_APP_KEY.")
        sys.exit(1)

    print("Fetching Adzuna results for company-name discovery…")
    company_names: list[str] = []
    seen_names: set[str] = set()

    for what, where in ADZUNA_SEARCHES:
        for page in range(1, 4):   # up to 150 results per query
            params = urllib.parse.urlencode({
                "app_id":           app_id,
                "app_key":          app_key,
                "results_per_page": 50,
                "what":             what,
                "where":            where,
                "sort_by":          "date",
                "max_days_old":     MAX_AGE_DAYS,
                "content-type":     "application/json",
            })
            url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/{page}?{params}"
            data = _get(url)
            if not data or not isinstance(data, dict):
                break
            results = data.get("results") or []
            if not results:
                break
            for r in results:
                name = (r.get("company") or {}).get("display_name", "").strip()
                if name and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    company_names.append(name)

    print(f"  {len(company_names)} unique companies from Adzuna")

    cache = _load_cache()
    known = _known_slugs(cache)
    found = 0

    for name in company_names:
        for slug in _guess_slug(name):
            if slug in known:
                break

            for ats_name, prober in PROBERS:
                time.sleep(PROBE_DELAY)
                try:
                    if prober(slug):
                        entry = {
                            "slug":   slug,
                            "name":   name,
                            "tags":   [],
                            "source": "adzuna-discover",
                        }
                        if not dry_run:
                            cache.setdefault(ats_name, []).append(entry)
                            known.add(slug)
                        print(f"  + [{ats_name:12s}] {slug:30s}  ({name})")
                        found += 1
                        break
                except Exception as e:
                    print(f"    probe error {ats_name}/{slug}: {e}", file=sys.stderr)

    if not dry_run and found:
        _save_cache(cache)

    suffix = " (dry run, not saved)" if dry_run else " added to cache"
    print(f"\nDone. {found} new companies promoted to direct ATS{suffix}.")


# ── Forbes Cloud 100 → direct ATS promotion ───────────────────────────────────

def _walk_for_names(obj, key: str) -> list[str]:
    """Recursively search a JSON object for lists whose items contain `key`."""
    results: list[str] = []
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], str):
            results.append(obj[key])
        for v in obj.values():
            results.extend(_walk_for_names(v, key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_walk_for_names(item, key))
    return results


def discover_from_forbes(dry_run: bool = False) -> None:
    """
    Seed company names from the Forbes Cloud 100 list page.

    Forbes serves the list as a Next.js app; the full data is embedded in a
    <script id="__NEXT_DATA__"> tag as JSON. We fetch the page with urllib,
    extract that JSON, walk common path patterns for the list items, and fall
    back to a recursive key search if the primary path misses.

    Usage:
        python3 discover.py --from-forbes          # live run
        python3 discover.py --from-forbes --dry-run
    """
    print(f"Fetching Forbes Cloud 100 page…")
    html = _fetch_html(FORBES_CLOUD100_URL)
    if not html:
        print("ERROR: Could not fetch Forbes Cloud 100 page.")
        sys.exit(1)

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        print("ERROR: __NEXT_DATA__ script tag not found — Forbes page structure may have changed.")
        sys.exit(1)

    try:
        data = json.loads(m.group(1))
    except Exception as e:
        print(f"ERROR: Could not parse __NEXT_DATA__ JSON: {e}")
        sys.exit(1)

    # Primary path: props.pageProps.list.listItems[*].organizationName or .name
    company_names: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        n = name.strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            company_names.append(n)

    try:
        items = data["props"]["pageProps"]["list"]["listItems"]
        for item in items:
            _add(item.get("organizationName") or item.get("name") or "")
    except (KeyError, TypeError):
        pass

    # Fallback: recursive walk for organizationName, then name
    if not company_names:
        for key in ("organizationName", "name"):
            for n in _walk_for_names(data, key):
                _add(n)

    if not company_names:
        print("WARNING: No company names extracted from Forbes page — page structure may have changed.")
        return

    print(f"  {len(company_names)} companies from Forbes Cloud 100")

    cache = _load_cache()
    known = _known_slugs(cache)
    found = 0

    for name in company_names:
        for slug in _guess_slug(name):
            if slug in known:
                break

            for ats_name, prober in PROBERS:
                time.sleep(PROBE_DELAY)
                try:
                    if prober(slug):
                        entry = {
                            "slug":   slug,
                            "name":   name,
                            "tags":   [],
                            "source": "forbes-cloud100",
                        }
                        if not dry_run:
                            cache.setdefault(ats_name, []).append(entry)
                            known.add(slug)
                        print(f"  + [{ats_name:12s}] {slug:30s}  ({name})")
                        found += 1
                        break
                except Exception as e:
                    print(f"    probe error {ats_name}/{slug}: {e}", file=sys.stderr)

    if not dry_run and found:
        _save_cache(cache)

    suffix = " (dry run, not saved)" if dry_run else " added to cache"
    print(f"\nDone. {found} new companies promoted to direct ATS{suffix}.")


# ── a16z portfolio → direct ATS promotion ─────────────────────────────────────

def _extract_a16z_names(html: str) -> list[str]:
    """
    Extract portfolio company names from a16z HTML.

    Tries __NEXT_DATA__ JSON first (a16z is also Next.js), then falls back to
    heading-tag regex. Returns a deduplicated list of plausible company names.
    """
    names: list[str] = []
    seen: set[str] = set()
    _UI_NOISE = {"portfolio", "filter", "all", "companies", "team", "about",
                 "blog", "news", "jobs", "contact", "home", "menu", "search"}

    def _add(name: str) -> None:
        n = name.strip()
        if len(n) < 2 or n.lower() in _UI_NOISE:
            return
        if n.lower() not in seen:
            seen.add(n.lower())
            names.append(n)

    # Strategy 1: __NEXT_DATA__ JSON
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            for n in _walk_for_names(data, "name"):
                _add(n)
        except Exception:
            pass

    # Strategy 2: heading tags (works on both static and BD-rendered HTML)
    if len(names) < 5:
        for n in re.findall(r'<h[23][^>]*>([^<]{2,60})</h[23]>', html):
            _add(n)

    return names


def discover_from_a16z(dry_run: bool = False) -> None:
    """
    Seed company names from the a16z portfolio page.

    Tries a plain urllib fetch first (works if a16z serves static HTML for SEO).
    If fewer than 5 company names are found — indicating a JS-gated response —
    falls back to Bright Data Web Unlocker (same key/function as pmfarm.py).
    Fails gracefully with a printed message if no Bright Data key is configured.

    Usage:
        python3 discover.py --from-a16z           # live run
        python3 discover.py --from-a16z --dry-run
    """
    print("Fetching a16z portfolio page (static)…")
    html = _fetch_html(A16Z_PORTFOLIO_URL) or ""
    company_names = _extract_a16z_names(html)

    if len(company_names) < 5:
        print(f"  Static fetch returned {len(company_names)} names — falling back to Bright Data JS render…")
        from pmfarm import _load_brightdata_key, _bd_fetch_html
        api_key = _load_brightdata_key()
        if not api_key:
            print("No Bright Data key — skipping a16z JS-render fallback. "
                  "Set BRIGHTDATA_API_KEY or create brightdata_key.txt.")
            sys.exit(1)
        try:
            html = _bd_fetch_html(A16Z_PORTFOLIO_URL, api_key)
        except Exception as e:
            print(f"ERROR: Bright Data fetch failed: {e}")
            sys.exit(1)
        company_names = _extract_a16z_names(html)

    print(f"  {len(company_names)} companies from a16z portfolio")

    if not company_names:
        print("WARNING: No company names extracted — page structure may have changed.")
        return

    cache = _load_cache()
    known = _known_slugs(cache)
    found = 0

    for name in company_names:
        for slug in _guess_slug(name):
            if slug in known:
                break

            for ats_name, prober in PROBERS:
                time.sleep(PROBE_DELAY)
                try:
                    if prober(slug):
                        entry = {
                            "slug":   slug,
                            "name":   name,
                            "tags":   [],
                            "source": "a16z",
                        }
                        if not dry_run:
                            cache.setdefault(ats_name, []).append(entry)
                            known.add(slug)
                        print(f"  + [{ats_name:12s}] {slug:30s}  ({name})")
                        found += 1
                        break
                except Exception as e:
                    print(f"    probe error {ats_name}/{slug}: {e}", file=sys.stderr)

    if not dry_run and found:
        _save_cache(cache)

    suffix = " (dry run, not saved)" if dry_run else " added to cache"
    print(f"\nDone. {found} new companies promoted to direct ATS{suffix}.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if "--from-adzuna" in sys.argv:
        discover_from_adzuna(dry_run)
    elif "--from-forbes" in sys.argv:
        discover_from_forbes(dry_run)
    elif "--from-a16z" in sys.argv:
        discover_from_a16z(dry_run)
    else:
        discover(dry_run)
