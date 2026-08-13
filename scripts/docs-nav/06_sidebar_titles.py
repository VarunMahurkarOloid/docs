"""Phase 7: rewrite `sidebarTitle` so it is unique within each navigation group.

The first pass truncated long Intercom titles to a fixed width, which cut off the
distinguishing tail and produced 66 sidebar entries that read identically to
their siblings ("Windows Login v2.0 - How to Deploy Windows Login v2.0…" x3).

This pass is navigation-aware:
  1. group pages by their leaf nav group (siblings in the sidebar)
  2. drop the word-prefix the siblings share - it is redundant once the group
     heading already says it
  3. strip boilerplate noise, then shorten
  4. if two siblings still collide, lengthen only the colliding ones until they
     are distinct, falling back to the full title

Run AFTER 03_build_nav.py. Idempotent.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

NOISE = [
    r"\s*[-–—]?\s*Video Tutorials?\s*$",
    r"\s+in the Tenant Admin Portal\b", r"\s+in Tenant Admin Portal\b",
    r"\s+in the Supervisor Portal\b", r"\s+in the Oloid Platform\b",
    r"^How to\s+", r"^How the\s+", r"^How\s+do\s+I\s+", r"^Guide to\s+",
    r"^Steps to\s+",
]
SOFT = 58


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def title_of(url):
    m = re.search(r'^title:\s*"?(.+?)"?\s*$', read(url + ".mdx"), re.M)
    return m.group(1).strip() if m else url.rsplit("/", 1)[-1]


def denoise(s):
    for rx in NOISE:
        s = re.sub(rx, " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" -–—:")


def shorten(s, cap):
    s = s.strip()
    if len(s) <= cap:
        return s
    return s[:cap].rsplit(" ", 1)[0].rstrip(" ,-–—:") + "…"


def common_prefix_words(titles):
    """Longest leading word sequence shared by every sibling title."""
    if len(titles) < 2:
        return 0
    splits = [t.split() for t in titles]
    n = 0
    while n < min(len(s) for s in splits) - 2:      # always keep >=3 words
        w = splits[0][n].lower()
        if all(s[n].lower() == w for s in splits):
            n += 1
        else:
            break
    return n


# ---------------------------------------------------------------- nav walk --
cfg = json.load(open("docs.json", encoding="utf-8"))
sibling_sets = []


def walk(node):
    if not isinstance(node, dict):
        return
    kids = node.get("pages") or node.get("groups") or node.get("menu") or []
    leaves = [k for k in kids if isinstance(k, str)]
    if leaves:
        sibling_sets.append(leaves)
    for k in kids:
        if isinstance(k, dict):
            walk(k)


for tab in cfg["navigation"]["tabs"]:
    for mi in tab.get("menu", []) or tab.get("groups", []):
        walk(mi)

# --------------------------------------------------------------- resolve ----
final = {}
for group in sibling_sets:
    full = {u: title_of(u) for u in group}
    strip_n = common_prefix_words(list(full.values()))
    base = {}
    for u, t in full.items():
        words = t.split()
        stripped = " ".join(words[strip_n:]) if strip_n and len(words) > strip_n else t
        base[u] = denoise(stripped) or denoise(t) or t

    cap = SOFT
    chosen = {u: shorten(b, cap) for u, b in base.items()}
    # lengthen only while some siblings remain indistinguishable
    while cap < 220:
        seen = {}
        for u, v in chosen.items():
            seen.setdefault(v, []).append(u)
        dupes = [us for us in seen.values() if len(us) > 1]
        if not dupes:
            break
        cap += 24
        for us in dupes:
            for u in us:
                chosen[u] = shorten(base[u], cap)
    for u, v in chosen.items():
        final[u] = v[:1].upper() + v[1:] if v else full[u]

# ----------------------------------------------------------------- write ----
changed = 0
for url, st in final.items():
    p = url + ".mdx"
    raw = read(p)
    m = re.match(r"^(---\n.*?\n---)(.*)$", raw, re.S)
    if not m:
        continue
    head, body = m.group(1), m.group(2)
    val = st.replace('"', "&quot;")
    if re.search(r"^sidebarTitle:", head, re.M):
        new = re.sub(r'^sidebarTitle:.*$', f'sidebarTitle: "{val}"', head,
                     count=1, flags=re.M)
    else:
        new = re.sub(r'^(title:.*)$', rf'\1\nsidebarTitle: "{val}"', head,
                     count=1, flags=re.M)
    if new != head:
        open(p, "w", encoding="utf-8", newline="").write(new + body)
        changed += 1

# ------------------------------------------------------------------ report --
collisions = 0
for group in sibling_sets:
    seen = {}
    for u in group:
        seen.setdefault(final.get(u, u), []).append(u)
    collisions += sum(len(v) for v in seen.values() if len(v) > 1)

print(f"groups {len(sibling_sets)}, pages titled {len(final)}, files changed {changed}")
print(f"remaining sidebarTitle collisions within a group: {collisions}")
