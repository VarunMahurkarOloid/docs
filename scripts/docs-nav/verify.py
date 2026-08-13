"""Verification harness. Re-run after every phase.

Asserts:
  A. every internal absolute link resolves to an .mdx on disk
  B. every referenced local image exists
  C. every nav path in docs.json resolves to an .mdx
  D. every .mdx on disk appears in nav exactly once (orphans AND duplicates)
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

SKIP = (".git", "node_modules", "images")


def all_mdx():
    out = []
    for dp, dn, fn in os.walk("."):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            if f.endswith(".mdx"):
                out.append(os.path.relpath(os.path.join(dp, f), ".").replace("\\", "/"))
    return sorted(out)


pages = all_mdx()
pageset = {p[:-4] for p in pages}  # strip .mdx -> URL path

# --- A. internal links ------------------------------------------------------
bad_links = Counter()
bad_link_files = set()
total_links = 0
for p in pages:
    body = open(p, encoding="utf-8", errors="replace").read()
    # markdown links AND Card/anchor href="" attributes - the component pass
    # moved Related Articles links out of markdown and into <Card href="...">
    targets = (re.findall(r"\]\((/[^)\s#]+)", body)
               + re.findall(r'href="(/[^"#]+)', body))
    for target in targets:
        if target.startswith("/images/"):
            continue
        total_links += 1
        if target.lstrip("/") not in pageset:
            bad_links[target] += 1
            bad_link_files.add(p)

# --- B. images --------------------------------------------------------------
bad_imgs = Counter()
total_imgs = 0
for p in pages:
    body = open(p, encoding="utf-8", errors="replace").read()
    for target in re.findall(r"(?:\]\(|src=\")(/images/[^)\"\s]+)", body):
        total_imgs += 1
        if not os.path.exists(target.lstrip("/")):
            bad_imgs[target] += 1

# --- B2. no surviving expiring Intercom CDN references -----------------------
cdn_left = sum(len(re.findall(r"downloads\.intercomcdn\.com",
                              open(p, encoding="utf-8", errors="replace").read()))
               for p in pages)

# --- C/D. navigation --------------------------------------------------------
nav_paths = []
if os.path.exists("docs.json"):
    cfg = json.load(open("docs.json", encoding="utf-8"))

    def walk(node):
        if isinstance(node, str):
            nav_paths.append(node)
        elif isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ("pages", "groups", "tabs", "menu", "anchors", "navigation"):
                    walk(v)

    walk(cfg.get("navigation", {}))

nav_counts = Counter(nav_paths)
nav_missing = [p for p in nav_paths if p not in pageset]
nav_dupes = {p: c for p, c in nav_counts.items() if c > 1}
orphans = sorted(pageset - set(nav_paths))

print("=" * 62)
print(f"pages on disk           : {len(pages)}")
print(f"internal links          : {total_links}   BROKEN: {sum(bad_links.values())} "
      f"({len(bad_links)} unique, in {len(bad_link_files)} files)")
print(f"image refs (local)      : {total_imgs}   BROKEN: {sum(bad_imgs.values())}")
print(f"expiring CDN refs left  : {cdn_left}")
print(f"nav entries             : {len(nav_paths)}  MISSING FILE: {len(nav_missing)}  "
      f"DUPLICATED: {len(nav_dupes)}")
print(f"orphans (on disk, no nav): {len(orphans)}")
print("=" * 62)

if bad_links:
    print("\ntop broken link targets:")
    for t, c in bad_links.most_common(12):
        print(f"  {c:5d}  {t}")
if bad_imgs:
    print("\ntop broken image refs:")
    for t, c in bad_imgs.most_common(8):
        print(f"  {c:5d}  {t}")
if nav_missing:
    print("\nnav entries with no file (first 20):")
    for t in nav_missing[:20]:
        print("  ", t)
if nav_dupes:
    print("\nduplicated nav entries (first 20):")
    for t, c in list(nav_dupes.items())[:20]:
        print(f"  {c}x  {t}")
if orphans:
    print(f"\norphans (first 15 of {len(orphans)}):")
    for t in orphans[:15]:
        print("  ", t)

clean = not (bad_links or bad_imgs or nav_missing or nav_dupes or orphans or cdn_left)
print("\nRESULT:", "ALL CLEAN" if clean else "ISSUES REMAIN")
sys.exit(0)
