"""Phase 5: mechanical MDX component pass over every article body.

Transforms (all idempotent - re-running changes nothing):
  T1  [![alt](/images/x.png)](https://downloads.intercomcdn.com/...)
        block-level -> <Frame><img/></Frame>
        inline      -> ![alt](/images/x.png)      (drops the expiring CDN anchor)
  T2  bare block-level ![alt](/images/x.png) -> <Frame><img/></Frame>
  T3  bare <iframe> video embeds -> wrapped in <Frame>
  T4  "Keywords" blocks (table form and inline pipe form) -> <Tip>
  T5  "Related Articles" link lists -> <CardGroup> of <Card>
  T6  "## **Heading**" -> "## Heading"
  T7  **Note:** / **Important:** / **Warning:** leading callouts -> <Note>/<Warning>
  T8  add a short `sidebarTitle` to frontmatter (long Intercom titles read badly
      in the sidebar)

Deliberately NOT converting numbered lists to <Steps>: the source lists are
inconsistently formatted and inline images live inside list items, so a blind
conversion would corrupt them.

Usage:  python 04_components.py [--sample N]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
SKIP = (".git", "node_modules", "images")

CDN = r"https?://downloads\.intercomcdn\.com/[^\s)]*"
IMG = r"/images/[^\s)\"]+"


def esc(s):
    """Prepare markdown text for use inside a JSX attribute value.

    Markdown backslash-escapes (\\< , \\* ...) are meaningless inside a JSX
    attribute and would render as a literal backslash, so undo them first.
    """
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!<>|])", r"\1", s)
    return s.replace('"', "&quot;").strip()


# --- T1/T2 images -----------------------------------------------------------
def images(text):
    # block-level linked image: whole line is [![alt](/images/..)](cdn)
    def block_linked(m):
        alt, src = esc(m.group(1)), m.group(2)
        return f'<Frame>\n  <img src="{src}" alt="{alt or "Screenshot"}" />\n</Frame>'

    text = re.sub(
        rf"^[ \t]*\[!\[([^\]]*)\]\(({IMG})\)\]\({CDN}\)[ \t]*$",
        block_linked, text, flags=re.M)

    # inline linked image -> plain markdown image (drops the expiring CDN anchor)
    text = re.sub(rf"\[!\[([^\]]*)\]\(({IMG})\)\]\({CDN}\)",
                  lambda m: f"![{m.group(1)}]({m.group(2)})", text)

    # bare block-level image -> Frame
    def block_bare(m):
        alt, src = esc(m.group(1)), m.group(2)
        return f'<Frame>\n  <img src="{src}" alt="{alt or "Screenshot"}" />\n</Frame>'

    text = re.sub(rf"^[ \t]*!\[([^\]]*)\]\(({IMG})\)[ \t]*$",
                  block_bare, text, flags=re.M)
    return text


# --- T3 video embeds --------------------------------------------------------
def videos(text):
    def wrap(m):
        block = m.group(0)
        return block if "<Frame>" in block else f"<Frame>\n{block}\n</Frame>"

    return re.sub(r"(?<!<Frame>\n)<iframe\b[^>]*>\s*</iframe>", wrap, text)


# --- T4 keywords ------------------------------------------------------------
def keywords(text):
    def to_tip(words):
        parts = [w.strip() for w in words.split("|") if w.strip()]
        if not parts:
            return ""
        return "<Tip>\n  **Keywords:** " + " · ".join(parts) + "\n</Tip>"

    # table form:  #### Keywords \n\n | a | b |
    text = re.sub(
        r"^#{2,6}[ \t]*\*{0,2}Keywords\*{0,2}[ \t]*$\n+^\|(.+)\|[ \t]*$",
        lambda m: to_tip(m.group(1)), text, flags=re.M)
    # inline form: **Keywords**| a| b|
    text = re.sub(
        r"\*\*Keywords\*\*[ \t]*\|(.+?)\|[ \t]*$",
        lambda m: "\n\n" + to_tip(m.group(1)), text, flags=re.M)
    return text


# --- T5 related articles ----------------------------------------------------
def related(text):
    pat = re.compile(
        r"^(?:---\s*\n+)?Related Articles\s*\n+((?:[ \t]*-[ \t]*\[[^\]]+\]\([^)]+\)[ \t]*\n?)+)",
        re.M)

    def build(m):
        links = re.findall(r"-[ \t]*\[([^\]]+)\]\(([^)]+)\)", m.group(1))
        if not links:
            return m.group(0)
        cards = "\n".join(
            f'  <Card title="{esc(t)}" icon="arrow-right" href="{h.strip()}" />'
            for t, h in links)
        return ("## Related Articles\n\n<CardGroup cols={2}>\n" + cards
                + "\n</CardGroup>\n")

    return pat.sub(build, text)


# --- T6/T7 headings and callouts -------------------------------------------
def headings(text):
    # [ \t]* not \s* - \s matches newlines and would swallow the blank line
    # that separates the heading from the paragraph below it
    return re.sub(r"^(#{1,6})[ \t]*\*\*(.+?)\*\*[ \t]*$", r"\1 \2", text, flags=re.M)


CALLOUT = {"note": "Note", "tip": "Tip", "important": "Warning",
           "warning": "Warning", "caution": "Warning"}


def callouts(text):
    def sub(m):
        kind = CALLOUT[m.group(1).lower()]
        return f"<{kind}>\n  {m.group(2).strip()}\n</{kind}>"

    return re.sub(r"^\*\*(Note|Tip|Important|Warning|Caution)\*\*[ \t]*:?[ \t]*(.+?)[ \t]*$",
                  sub, text, flags=re.M)


# --- T8 sidebar titles ------------------------------------------------------
NOISE = [
    r"\s*[-–]?\s*Video Tutorials?\s*$",
    r"\s+in the Tenant Admin Portal\b", r"\s+in Tenant Admin Portal\b",
    r"\s+in the Supervisor Portal\b", r"\s+in the Oloid Platform\b",
    r"^How to\s+", r"^How the\s+", r"^How\s+do\s+I\s+", r"^Guide to\s+",
    r"^Steps to\s+",
]


def short_title(title):
    s = title.strip().strip('"')
    for rx in NOISE:
        s = re.sub(rx, " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -–:")
    if len(s) > 58:                       # trim on a word boundary
        s = s[:58].rsplit(" ", 1)[0].rstrip(" ,-–:") + "…"
    return (s[:1].upper() + s[1:]) if s else title


def sidebar_title(head):
    if re.search(r"^sidebarTitle:", head, re.M):
        return head
    m = re.search(r'^title:\s*"?(.+?)"?\s*$', head, re.M)
    if not m:
        return head
    st = short_title(m.group(1))
    if st.lower() == m.group(1).strip().lower():
        return head
    return head.replace(m.group(0), m.group(0) + f'\nsidebarTitle: "{esc(st)}"', 1)


# --- driver -----------------------------------------------------------------
MARKER = "auto-generated overview"
sample = None
if "--sample" in sys.argv:
    sample = int(sys.argv[sys.argv.index("--sample") + 1])

files = []
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in SKIP]
    files += [os.path.join(dp, f) for f in fn if f.endswith(".mdx")]
files.sort()
if sample:
    files = files[:sample]

stats = {k: 0 for k in
         ("frames", "cdn_dropped", "tips", "cardgroups", "callouts", "sidebar")}
changed = 0

for p in files:
    original = open(p, encoding="utf-8", errors="replace").read()
    if MARKER in original:
        continue
    m = re.match(r"^(---\n.*?\n---)(.*)$", original, re.S)
    if not m:
        continue
    head, body = m.group(1), m.group(2)

    new_head = sidebar_title(head)
    before_cdn = len(re.findall(CDN, body))
    before_frames = body.count("<Frame>")

    body = images(body)
    body = videos(body)
    body = keywords(body)
    body = related(body)
    body = headings(body)
    body = callouts(body)

    stats["frames"] += body.count("<Frame>") - before_frames
    stats["cdn_dropped"] += before_cdn - len(re.findall(CDN, body))
    stats["tips"] += body.count("<Tip>") - original.count("<Tip>")
    stats["cardgroups"] += body.count("<CardGroup") - original.count("<CardGroup")
    stats["callouts"] += (body.count("<Note>") + body.count("<Warning>")
                          - original.count("<Note>") - original.count("<Warning>"))
    stats["sidebar"] += 1 if new_head != head else 0

    out = new_head + body
    if out != original:
        open(p, "w", encoding="utf-8", newline="").write(out)
        changed += 1

print(f"files scanned {len(files)}, modified {changed}")
for k, v in stats.items():
    print(f"  {k:14s} {v}")
