#!/usr/bin/env python3
"""
add_company.py — probe a single company across all three ATSs and add it to
verified_companies.json if a slug resolves.

Usage:
    python3 add_company.py "Company Name"
    python3 add_company.py "Company Name" --dry-run
"""

import json, sys, time
from datetime import date
from pathlib import Path
from discover import _guess_slug, _probe_greenhouse, _probe_ashby, _probe_lever, _load_cache, _known_slugs

CACHE_FILE = Path("verified_companies.json")
PROBERS = [
    ("greenhouse", _probe_greenhouse),
    ("ashby",      _probe_ashby),
    ("lever",      _probe_lever),
]

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_company.py \"Company Name\" [--dry-run]")
        sys.exit(1)

    name    = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    slugs   = _guess_slug(name)

    cache = _load_cache()
    known = _known_slugs(cache)

    print(f"Probing '{name}'…")
    print(f"  Slug candidates: {slugs}")

    for slug in slugs:
        if slug in known:
            print(f"  '{slug}' is already in verified_companies.json — nothing to add.")
            sys.exit(0)

        for ats_name, prober in PROBERS:
            time.sleep(0.1)
            try:
                if prober(slug):
                    entry = {"slug": slug, "name": name, "tags": ["manually-added"]}
                    print(f"\n  FOUND on {ats_name}: slug = '{slug}'")
                    if dry_run:
                        print(f"  (dry-run) Would add: {json.dumps(entry)}")
                    else:
                        cache[ats_name].append(entry)
                        total = sum(
                            len(v) for k, v in cache.items()
                            if isinstance(v, list) and k != "yc"
                        )
                        cache.setdefault("_meta", {}).update({
                            "last_updated": date.today().isoformat(),
                            "total": total,
                        })
                        CACHE_FILE.write_text(json.dumps(cache, indent=2))
                        print(f"  Added to verified_companies.json (total: {total})")
                        print(f"  Tip: edit the 'tags' field to add sector/geo labels.")
                    sys.exit(0)
            except Exception as e:
                print(f"  probe error {ats_name}/{slug}: {e}", file=sys.stderr)

    print(f"\n  Not found on Greenhouse, Ashby, or Lever with any slug variant.")
    print(f"  Try a custom slug: python3 add_company.py \"{name}\" (then edit slug manually)")
    sys.exit(1)

if __name__ == "__main__":
    main()
