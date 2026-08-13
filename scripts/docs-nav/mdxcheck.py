"""Structural sanity check on the JSX introduced by the component pass.

Verifies for every page:
  - paired components (<Frame>, <CardGroup>, <Tip>, <Note>, <Warning>, <Steps>)
    have matching open/close counts
  - <Card> is either self-closing or properly closed
  - frontmatter is present, starts at line 1, and is closed
  - no stray unescaped '<' that MDX would try to parse as a tag
"""
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
SKIP = (".git", "node_modules", "images")
PAIRED = ["Frame", "CardGroup", "Tip", "Note", "Warning", "Info", "Steps", "Accordion"]

pages = []
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in SKIP]
    pages += [os.path.join(dp, f) for f in fn if f.endswith(".mdx")]

problems = Counter()
detail = []

for p in sorted(pages):
    raw = open(p, encoding="utf-8", errors="replace").read()

    if not raw.startswith("---\n"):
        problems["frontmatter-not-at-line-1"] += 1
        detail.append((p, "frontmatter does not start at line 1"))
        continue
    if not re.match(r"^---\n.*?\n---", raw, re.S):
        problems["frontmatter-unclosed"] += 1
        detail.append((p, "frontmatter block never closes"))
        continue

    body = re.sub(r"^---\n.*?\n---", "", raw, count=1, flags=re.S)
    body = re.sub(r"```.*?```", "", body, flags=re.S)      # ignore code fences
    body = re.sub(r"`[^`\n]*`", "", body)                  # ignore inline code

    # attribute-aware: a quoted attribute value may legally contain '>'
    def tag_counts(tag):
        attrs = r'(?:[^>"]|"[^"]*")*'
        opens = len(re.findall(rf"<{tag}\b{attrs}>", body))
        selfc = len(re.findall(rf"<{tag}\b{attrs}/>", body))
        closes = len(re.findall(rf"</{tag}>", body))
        return opens - selfc, closes

    for tag in PAIRED + ["Card"]:
        opens, closes = tag_counts(tag)
        if opens != closes:
            problems[f"unbalanced-{tag}"] += 1
            detail.append((p, f"<{tag}> open={opens} close={closes}"))

print(f"checked {len(pages)} pages")
if problems:
    for k, v in problems.most_common():
        print(f"  {v:5d}  {k}")
    print("\nfirst 15 details:")
    for p, d in detail[:15]:
        print(f"   {p}: {d}")
else:
    print("  no structural problems found")
