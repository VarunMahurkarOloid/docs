"""Phase 6: escape bare angle-bracket prose that MDX would parse as a JSX tag.

The migrated content contains placeholders written as <installation script file
name>, <tenant-id>, <your-domain> and so on. MDX tries to open a JSX element and
fails with "Expected a closing tag". The source is inconsistent - the same line
often escapes one occurrence (\\<...>) and not the next.

Fix: escape the opening '<' of any angle-bracket run that is not a known
component/HTML tag, outside of code fences and inline code.

Usage: python 05_escape_angles.py [--check]
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
SKIP = (".git", "node_modules", "images")
CHECK = "--check" in sys.argv

KNOWN = {
    # Mintlify components
    "frame", "card", "cardgroup", "tip", "note", "warning", "info", "steps",
    "step", "accordion", "accordiongroup", "tabs", "tab", "icon", "columns",
    "expandable", "responsefield", "paramfield", "update", "check", "snippet",
    "tooltip", "banner", "codegroup",
    # HTML
    "a", "b", "br", "code", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "iframe", "img", "li", "ol", "p", "pre", "span", "strong",
    "sub", "sup", "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
    "video", "source", "picture", "figure", "figcaption", "blockquote",
}

# a run like <foo bar baz> or <foo-bar> that is not a known tag
CAND = re.compile(r"<(?!/)\s*([A-Za-z][A-Za-z0-9._\- ]*?)\s*>")


def already_escaped(text, pos):
    """True if the '<' at `pos` is markdown-escaped.

    Count consecutive backslashes immediately before it: an ODD count means the
    '<' itself is escaped; an EVEN count means the backslashes escape each other
    and the '<' is live. `.\\\\<installation script file name>` is the real case
    that broke the build - two backslashes, so the '<' was NOT escaped.
    """
    n = 0
    i = pos - 1
    while i >= 0 and text[i] == "\\":
        n += 1
        i -= 1
    return n % 2 == 1


def protect(text):
    """Blank out code fences / inline code so offsets stay stable."""
    spans = []
    for m in re.finditer(r"```.*?```|`[^`\n]*`", text, re.S):
        spans.append(m.span())
    return spans


def in_spans(pos, spans):
    return any(a <= pos < b for a, b in spans)


files = []
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in SKIP]
    files += [os.path.join(dp, f) for f in fn if f.endswith(".mdx")]
files.sort()

found = Counter()
touched = 0
for p in files:
    raw = open(p, encoding="utf-8", errors="replace").read()
    m = re.match(r"^(---\n.*?\n---)(.*)$", raw, re.S)
    if not m:
        continue
    head, body = m.group(1), m.group(2)
    spans = protect(body)

    out, last, changed = [], 0, False
    for mm in CAND.finditer(body):
        tag = mm.group(1).split()[0].lower() if mm.group(1).split() else ""
        if (tag in KNOWN or in_spans(mm.start(), spans)
                or already_escaped(body, mm.start())):
            continue
        found[mm.group(1).strip()] += 1
        out.append(body[last:mm.start()])
        out.append("\\<" + mm.group(0)[1:])   # escape only the opening '<'
        last = mm.end()
        changed = True
    if changed:
        out.append(body[last:])
        if not CHECK:
            open(p, "w", encoding="utf-8", newline="").write(head + "".join(out))
        touched += 1

print(f"{'would fix' if CHECK else 'fixed'} {sum(found.values())} "
      f"occurrences in {touched} files")
for k, v in found.most_common(20):
    print(f"  {v:4d}  <{k}>")
