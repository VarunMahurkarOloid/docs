"""Phase 2: retire the `_review/uncategorized` staging bucket (205 files).

Destination is derived from the Intercom `source.collection` + `source.section`
already present in each file's frontmatter. Files are moved, their frontmatter
taxonomy fields are rewritten, and every internal link across the whole corpus
that pointed into /_review/uncategorized/ is repointed to the new location.
"""
import os
import re
import shutil
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

SRC = "_review/uncategorized"

# category -> human nav path used in frontmatter
NAVPATH = {
    "administration/admin-portal": "Administration > Admin Portal",
    "administration/user-portal": "Administration > User Portal",
    "administration/device-admin-apps": "Administration > Device Admin Apps",
    "passwordless/ios/connect": "Passwordless > iOS > Oloid Connect",
    "passwordless/verify": "Passwordless > Oloid Verify",
    "passwordless/cloudkey": "Passwordless > Oloid CloudKey",
    "api-reference": "API Reference",
    "resources/guides": "Resources > Guides & Troubleshooting",
}
TAGS = {
    "administration/admin-portal": ["Administration", "Admin Portal"],
    "administration/user-portal": ["Administration", "User Portal"],
    "administration/device-admin-apps": ["Administration", "Device Admin Apps"],
    "passwordless/ios/connect": ["Passwordless", "iOS", "Oloid Connect"],
    "passwordless/verify": ["Passwordless", "Oloid Verify"],
    "passwordless/cloudkey": ["Passwordless", "Oloid CloudKey"],
    "api-reference": ["API Reference"],
    "resources/guides": ["Resources", "Guides"],
}


def destination(collection, section):
    c, s = collection.strip(), section.strip()
    if c == "Oloid Platform - Enterprise Features":
        return "api-reference" if s == "API Guides" else "administration/admin-portal"
    if c == "Oloid Platform Videos":
        return "administration/admin-portal"
    if c in ("Oloid Verify/Connect", "Oloid Connect", "Oloid Connect for iPhone"):
        return "passwordless/ios/connect"
    if c == "Oloid Verify":
        return "passwordless/verify"
    if c == "Oloid CloudKey":
        return "passwordless/cloudkey"
    if c == "Passwordless Authenticator":
        if s == "Credential Management":
            return "administration/user-portal"
        if "Reporting" in s:
            return "administration/admin-portal"
        return "resources/guides"
    if c in ("Supporting Documents", "Quick Reference Guides ( QRG)", "Troubleshooting"):
        return "resources/guides"
    return None


def field(fm, name):
    m = re.search(rf'^\s*{name}:\s*"?([^"\n]+)"?', fm, re.M)
    return m.group(1).strip() if m else ""


# --- classify ---------------------------------------------------------------
moves = {}          # old_url -> new_url
plan = []           # (src_path, dst_path, category)
unplaced = []
counts = Counter()

for f in sorted(os.listdir(SRC)):
    if not f.endswith(".mdx"):
        continue
    path = f"{SRC}/{f}"
    text = open(path, encoding="utf-8").read()
    fm = re.search(r"^---\n(.*?)\n---", text, re.S).group(1)
    dest = destination(field(fm, "collection"), field(fm, "section"))
    if dest is None:
        unplaced.append((f, field(fm, "collection"), field(fm, "section")))
        continue
    plan.append((path, f"{dest}/{f}", dest))
    moves[f"/{SRC}/{f[:-4]}"] = f"/{dest}/{f[:-4]}"
    counts[dest] += 1

print("planned destinations:")
for k, v in counts.most_common():
    print(f"  {v:4d}  {k}")
print(f"  total planned: {sum(counts.values())}   unplaced: {len(unplaced)}")
for u in unplaced:
    print("   UNPLACED:", u)
if unplaced:
    raise SystemExit("ABORT: unplaced files -- extend the mapping table")

# collision check against existing destination files
coll = [d for _, d, _ in plan if os.path.exists(d)]
if coll:
    raise SystemExit(f"ABORT: {len(coll)} destination collisions: {coll[:10]}")

# --- move + rewrite frontmatter --------------------------------------------
for src, dst, cat in plan:
    text = open(src, encoding="utf-8").read()
    head, body = text.split("\n---", 1)
    head = head.replace(
        'tags:\n  - "_review/uncategorized"',
        "tags:\n" + "\n".join(f'  - "{t}"' for t in TAGS[cat]),
    )
    head = head.replace(
        'categories:\n  - "_review/uncategorized"', f'categories:\n  - "{cat}"'
    )
    head = head.replace(
        'primaryCategory: "_review/uncategorized"', f'primaryCategory: "{cat}"'
    )
    head = head.replace(
        'navPath: "_review/uncategorized"', f'navPath: "{NAVPATH[cat]}"'
    )
    if "_review" in head:
        raise SystemExit(f"ABORT: leftover _review in frontmatter of {src}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8", newline="").write(head + "\n---" + body)
    os.remove(src)
print(f"moved + retagged {len(plan)} files")

# --- rewrite links corpus-wide ---------------------------------------------
SKIP = (".git", "node_modules", "images")
pages = []
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in SKIP]
    pages += [os.path.join(dp, f) for f in fn if f.endswith(".mdx")]

pattern = re.compile(r"/_review/uncategorized/[A-Za-z0-9._-]+")
rewritten = files_touched = unresolved = 0
for p in pages:
    text = open(p, encoding="utf-8").read()
    if "/_review/" not in text:
        continue

    def sub(m):
        global rewritten, unresolved
        old = m.group(0)
        if old in moves:
            rewritten += 1
            return moves[old]
        unresolved += 1
        return old

    new = pattern.sub(sub, text)
    if new != text:
        open(p, "w", encoding="utf-8", newline="").write(new)
        files_touched += 1

print(f"rewrote {rewritten} links across {files_touched} files; unresolved {unresolved}")

if os.path.isdir("_review"):
    left = sum(len(f) for _, _, f in os.walk("_review"))
    if left:
        raise SystemExit(f"ABORT: {left} files left under _review/")
    shutil.rmtree("_review")
    print("removed empty _review/ scaffold")
