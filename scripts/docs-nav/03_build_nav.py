"""Phase 3+4: generate docs.json navigation and card-based overview pages.

Structure comes from frontmatter already on disk:
  primaryCategory -> tab / menu item
  source.section  -> group (cleaned, then super-grouped for large categories)

Two normalizations make the raw Intercom sections usable as nav groups:
  1. redundant product tokens are stripped inside their own category
     ("Videos-Supervisor App" -> "Videos" inside the Supervisor menu item)
  2. video sections are nested as a "Videos" subgroup under their base topic
     ("Create and Manage Users - Video Tutorials" nests under "Create and Manage Users")

Idempotent: regenerates docs.json navigation and every overview page from disk.
"""
import json
import os
import re
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
SKIP = (".git", "node_modules", "images")


class MI:
    """One menu item: a label, an icon, and the categories it covers."""

    def __init__(self, label, icon, cats, index=None, extra=None, only=None):
        self.label, self.icon, self.cats = label, icon, cats
        self.index = index          # explicit overview page path (else generated)
        self.extra = extra or []    # standalone pages appended after the groups
        self.only = only or []      # menu item made purely of standalone pages


TABS = OrderedDict([
    ("Passwordless", [
        MI("Windows Login", "windows", ["passwordless/windows/passwordless"]),
        MI("Supervisor", "user-shield", ["passwordless/windows/supervisor"]),
        MI("Android DeviceLock", "android", ["passwordless/android/devicelock"]),
        MI("iOS - Oloid Connect", "apple", ["passwordless/ios/connect"]),
        MI("Web - WebKey", "globe", ["passwordless/web/webkey"]),
        MI("Web - Chrome Vault", "chrome", ["passwordless/web/chrome-vault"]),
        MI("Oloid Verify", "shield-check", ["passwordless/verify"]),
        MI("Oloid CloudKey", "cloud", ["passwordless/cloudkey"]),
    ]),
    ("Administration", [
        MI("Admin Portal", "gauge", ["administration/admin-portal"]),
        MI("User Portal", "user", ["administration/user-portal"]),
        MI("Device Admin Apps", "mobile-screen", ["administration/device-admin-apps"]),
    ]),
    ("Workflow", [
        MI("Workflow", "diagram-project", ["workflow/workflow"], index="workflow/overview"),
    ]),
    ("Resources", [
        MI("Integrations", "plug",
           ["resources/integrations/sso", "resources/integrations/hrms",
            "resources/integrations/pacs"],
           index="resources/integrations/overview"),
        MI("Industry", "building",
           ["resources/industry/healthcare", "resources/industry/retail"],
           index="resources/industry/overview"),
        MI("Guides & Troubleshooting", "life-ring", ["resources/guides"]),
    ]),
    ("TimeClock", [
        MI("Android", "android", ["timeclock/android"],
           extra=["timeclock/android/getting-started/introduction"]),
        MI("iOS", "apple", [], only=["timeclock/ios/overview",
                                     "timeclock/ios/getting-started/introduction"]),
    ]),
    ("API Reference", [
        MI("API Documentation", "code", ["api-reference"],
           extra=["api-reference/introduction", "api-reference/authentication"]),
    ]),
    ("Changelog", [
        # explicit index: the category dir *is* the tab root, so the default
        # "changelog/overview" would collide with the tab-level overview page.
        MI("Release Notes", "clock-rotate-left", ["changelog"],
           index="changelog/release-notes"),
        MI("iOS", "apple", [], only=["changelog/ios/overview"]),
        MI("Android", "android", [], only=["changelog/android/overview"]),
        MI("Admin Portal", "user-gear", [], only=["changelog/admin-portal/overview"]),
    ]),
])

CAT_LABEL = {
    "resources/integrations/sso": "SSO & Identity",
    "resources/integrations/hrms": "HRMS & Agents",
    "resources/integrations/pacs": "PACS & Access Control",
    "resources/industry/healthcare": "Healthcare",
    "resources/industry/retail": "Retail",
}

# tokens stripped from section names inside a given category (redundant there)
STRIP_TOKENS = {
    "passwordless/windows/passwordless": ["Windows Login", "Oloid Windows Passwordless Authenticator"],
    "passwordless/windows/supervisor": ["Supervisor App", "Supervisor Portal"],
    "passwordless/android/devicelock": ["Device Lock", "Oloid Android Passwordless Authenticator -DeviceLock"],
    "passwordless/ios/connect": ["Oloid Connect for Passwordless", "Oloid Connect", "Oloid Verify/Connect",
                                 "Oloid iOS Passwordless Authenticator-"],
    "passwordless/web/webkey": ["WebKey", "Webkey", "Oloid Web Passwordless Login -WebKey"],
    "passwordless/web/chrome-vault": ["Chrome Vault"],
    "passwordless/verify": ["Oloid Verify"],
    "passwordless/cloudkey": ["Oloid CloudKey"],
    "administration/user-portal": ["Oloid User Portal"],
}

# super-groups for categories with too many sections to sit flat.
SUPERGROUPS = {
    "administration/admin-portal": [
        ("Getting Started", r"^(Getting Started|Oloid Platform)"),
        ("Users & Groups", r"Create and Manage (Users|Groups)"),
        ("Credentials & Passwords", r"(Shared Credentials|Shared Passwords|Credential Management|Factor Sequence)"),
        ("Applications & Connections", r"Create and Manage (Applications|Connections)"),
        ("Endpoints & Locations", r"Create and Manage (Endpoints|Locations)"),
        ("Consent Documents", r"Consent Documents"),
        ("Reports & Insights", r"(Reports|Insights|Reporting)"),
        ("SSO & User Sync", r"(SSO Setup|Advanced User Sync|IDP Provider)"),
        ("Accounts & Settings", r"(Accounts and Settings|Security, Encryption)"),
        ("Application Administration", r"(Chrome Vault|Oloid Connect|Oloid Verify|Device Lock|WebKey|Supervisor|CloudKey|Passwordless Authenticator)"),
    ],
    "passwordless/windows/passwordless": [
        ("Windows Login v2.0", r"v2\.0"),
        ("Windows Login v1.0", r"v1\.0|v1 - Installation"),
        ("Admin Guides", r"^Admin Guides"),
        ("User Guides", r"^User Guides"),
        ("Presence Detection", r"Presence Detection"),
        ("Healthcare", r"Healthcare"),
        ("Multi-Factor Authentication", r"MFA"),
        ("Platform Administration", r"(Create and Manage|Accounts and Settings|API Guides)"),
    ],
    "passwordless/windows/supervisor": [
        ("Supervisor App", r"Supervisor App|Enroll Badge"),
        ("Supervisor Portal", r"Supervisor Portal"),
        ("Platform Administration", r"(Create and Manage|Accounts and Settings|Windows Login)"),
    ],
    "passwordless/ios/connect": [
        ("Getting Started", r"Getting [Ss]tarted|Installation"),
        ("User Guides", r"User Guides|Credential Management|for iPhone"),
        ("Admin Guides", r"Admin Guides|Platform Configuration"),
        ("FAQs & Supporting Docs", r"FAQs|Supporting"),
    ],
    "administration/user-portal": [
        ("Getting Started", r"Getting Started"),
        ("Credential Management", r"(Face|PIN|Password|Badge|NFC|QR Code) ?Management|Credential Management"),
        ("Accounts & Settings", r"Accounts and Settings"),
        ("SSO Setup", r"SSO Setup"),
        ("Platform Administration", r"Create and Manage"),
    ],
    "resources/integrations/sso": [
        ("Identity Providers", r"(SSO Setup|IDP Provider)"),
        ("User Sync & SCIM", r"(Advanced User Sync|SCIM|Data Tables)"),
        ("Application SSO", r"(Oloid Connect|Oloid Verify|WebKey|Supervisor|Passwordless Authenticator)"),
    ],
}

# Every super-grouped category gets a catch-all Videos bucket as its LAST rule,
# so standalone video collections surface as their own group instead of landing
# in "More". Placed last so topic-specific rules (Healthcare, Presence
# Detection, ...) still claim their own video sections first.
for _rules in SUPERGROUPS.values():
    _rules.append(("Videos", r"video"))

VIDEO_RE = re.compile(r"(video tutorials?|videos)", re.I)

# Sentinel for "a video section with no parent topic". Must not collide with any
# real cleaned label - using the literal "Other" previously caused 32 Windows
# Login video pages to be nested under an unrelated 1-page "Other" group.
UNSCOPED = "\x00unscoped"


def clean_section(cat, s):
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("( QRG)", "(QRG)").replace("(Healthcare )", "(Healthcare)")
    for tok in STRIP_TOKENS.get(cat, []):
        s = re.sub(r"[-–:]?\s*" + re.escape(tok) + r"\s*[-–:]?", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -–:")
    # stripping a product token can leave a dangling preposition on either end
    # ("Getting Started with WebKey" -> "Getting Started with";
    #  "Oloid Connect for iPhone" -> "for iPhone")
    s = re.sub(r"\s+(with|for|of|on|in|to|the|and)$", "", s, flags=re.I)
    s = re.sub(r"^(with|for|of|on|in|to|the|and|Oloid)\s+", "", s, flags=re.I)
    s = re.sub(r"^(Using|the)\s*$", "Usage", s, flags=re.I)
    return s.strip(" -–:") or "Other"


def base_topic(s):
    t = re.sub(r"[-–]?\s*(video tutorials?|videos)\s*[-–]?", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -–:")


def supergroup(cat, section):
    for label, rx in SUPERGROUPS.get(cat, []):
        if re.search(rx, section, re.I):
            return label
    return "More" if cat in SUPERGROUPS else None


def frontmatter(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def field(fm, name, indent=r"\s*"):
    m = re.search(rf'^{indent}{name}:\s*"?([^"\n]+)"?', fm, re.M)
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------------- gather --
MARKER = "{/* auto-generated overview - regenerated by 03_build_nav.py */}"


def sweep_generated():
    """Delete overview pages from a previous run so stale ones never linger,
    and so generated pages are never re-ingested as content on a re-run.

    Only files carrying MARKER are touched, so hand-written pages are safe.
    """
    removed = 0
    for dp, dn, fn in os.walk("."):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            if not f.endswith(".mdx"):
                continue
            p = os.path.join(dp, f)
            # read and close before removing - Windows refuses to delete an
            # open file handle
            with open(p, encoding="utf-8", errors="replace") as fh:
                marked = MARKER in fh.read()
            if marked:
                os.remove(p)
                removed += 1
    print(f"swept {removed} previously generated overview pages")


sweep_generated()

STANDALONE = {p for mi in [m for v in TABS.values() for m in v]
              for p in list(mi.extra) + list(mi.only)}

pages = defaultdict(lambda: defaultdict(list))
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in SKIP]
    for f in fn:
        if not f.endswith(".mdx"):
            continue
        p = os.path.join(dp, f)
        url = os.path.relpath(p, ".").replace("\\", "/")[:-4]
        if url.endswith("/overview") or url in STANDALONE:
            continue
        fm = frontmatter(p)
        cat = field(fm, "primaryCategory", r"")
        if not cat:
            continue
        title = field(fm, "title") or os.path.basename(url)
        pages[cat][field(fm, "section") or "General"].append((title, url))

ORDER_FIRST = ("overview", "introduction", "getting-started")


def sort_pages(items):
    return [u for _, u in sorted(
        items, key=lambda tu: (
            0 if any(k in tu[1].rsplit("/", 1)[-1] for k in ORDER_FIRST) else 1,
            tu[0].lower()))]


def build_groups(cat):
    raw = pages.get(cat, {})
    cleaned = defaultdict(list)
    origins = defaultdict(set)      # cleaned label -> raw section names
    for sec, items in raw.items():
        label = clean_section(cat, sec)
        cleaned[label] += items
        origins[label].add(sec)

    topics, videos = {}, defaultdict(list)
    vid_origins = defaultdict(set)
    for sec, items in cleaned.items():
        if VIDEO_RE.search(sec):
            bt = base_topic(sec) or UNSCOPED
            videos[bt] += items
            vid_origins[bt] |= origins[sec]
        else:
            topics[sec] = topics.get(sec, []) + items

    nodes, node_origins = {}, {}
    for sec, items in topics.items():
        g = {"group": sec, "pages": sort_pages(items)}
        if sec in videos:
            g["pages"].append({"group": "Videos", "pages": sort_pages(videos.pop(sec))})
            vid_origins.pop(sec, None)
        nodes[sec] = g
        node_origins[sec] = origins[sec]
    for bt, items in videos.items():
        label = "Videos" if bt == UNSCOPED else f"{bt} Videos".strip()
        nodes[label] = {"group": label, "pages": sort_pages(items)}
        node_origins[label] = vid_origins[bt]

    if cat in SUPERGROUPS:
        buckets = defaultdict(list)
        for sec, g in nodes.items():
            # classify on the RAW section names: clean_section() strips the very
            # product tokens the super-group patterns match on.
            bucket = next(
                (b for b in (supergroup(cat, o) for o in sorted(node_origins[sec]))
                 if b and b != "More"),
                None) or supergroup(cat, sec)
            buckets[bucket].append(g)
        out = []
        for label in [l for l, _ in SUPERGROUPS[cat]] + ["More"]:
            if not buckets.get(label):
                continue
            kids = sorted(buckets[label], key=lambda g: g["group"].lower())
            if len(kids) == 1 and kids[0]["group"] == label:
                out.append(kids[0])
            else:
                out.append({"group": label, "pages": kids})
        return out
    return [nodes[k] for k in sorted(nodes, key=str.lower)]


def count_pages(node):
    return 1 if isinstance(node, str) else sum(count_pages(p) for p in node.get("pages", []))


def first_page(node):
    if isinstance(node, str):
        return node
    for p in node.get("pages", []):
        r = first_page(p)
        if r:
            return r
    return None


made = []


def write_page(path, title, sidebar, desc, icon, intro, cards):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    head = ["---", f'title: "{title}"', f'sidebarTitle: "{sidebar}"',
            f'description: "{desc}"']
    if icon:
        head.append(f'icon: "{icon}"')
    head.append("---")
    # marker goes after the frontmatter block - frontmatter must start at line 1
    body = "\n".join(head) + f"\n{MARKER}\n\n{intro}\n\n"
    if cards:
        body += '<CardGroup cols={2}>\n' + "\n".join(cards) + "\n</CardGroup>\n"
    open(path, "w", encoding="utf-8", newline="").write(body)
    made.append(path)


def card(title, icon, href, sub):
    return (f'  <Card title="{title}" icon="{icon}" href="{href}">\n'
            f"    {sub}\n  </Card>")


def plural(n):
    return f"{n} article{'s' if n != 1 else ''}"


# -------------------------------------------------------------------- build --
tabs_out = []
for tab, items in TABS.items():
    menu = []
    for mi in items:
        if mi.only:
            menu.append({"item": mi.label, "icon": mi.icon, "pages": list(mi.only)})
            continue

        # one menu item may cover several categories -> each becomes a group
        if len(mi.cats) == 1:
            body = build_groups(mi.cats[0])
        else:
            body = []
            for c in mi.cats:
                g = build_groups(c)
                if g:
                    body.append({"group": CAT_LABEL.get(c, c), "pages": g})
        if not body and not mi.extra:
            continue

        idx = mi.index or f"{mi.cats[0]}/overview"
        cards = [card(g["group"], mi.icon, "/" + first_page(g), plural(count_pages(g)))
                 for g in body if isinstance(g, dict) and first_page(g)]
        write_page(idx + ".mdx", mi.label, "Overview",
                   f"Browse all {mi.label} documentation.", mi.icon,
                   f"Documentation for **{mi.label}**, grouped by topic.", cards)

        menu.append({"item": mi.label, "icon": mi.icon,
                     "pages": [idx] + body + list(mi.extra)})

    if not menu:
        continue
    if len(menu) == 1:
        tabs_out.append({"tab": tab, "groups": [
            {"group": menu[0]["item"], "icon": menu[0]["icon"], "pages": menu[0]["pages"]}]})
    else:
        root = items[0].cats[0].split("/")[0] if items[0].cats else items[0].only[0].split("/")[0]
        tcards = []
        for mi in items:
            n = (sum(len(v) for c in mi.cats for v in pages.get(c, {}).values())
                 + len(mi.extra) + len(mi.only))
            href = "/" + (mi.only[0] if mi.only else (mi.index or f"{mi.cats[0]}/overview"))
            tcards.append(card(mi.label, mi.icon, href, plural(n)))
        write_page(f"{root}/overview.mdx", tab, "Overview",
                   f"Explore the {tab} documentation.", "book-open",
                   f"Everything under **{tab}**.", tcards)
        menu.insert(0, {"item": "Overview", "icon": "book-open",
                        "pages": [f"{root}/overview"]})
        tabs_out.append({"tab": tab, "menu": menu})

cfg = json.load(open("docs.json", encoding="utf-8"))
cfg["navigation"] = {"tabs": tabs_out}
with open("docs.json", "w", encoding="utf-8", newline="\n") as fh:
    json.dump(cfg, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

print(f"wrote docs.json: {len(tabs_out)} tabs, {len(made)} overview pages generated")
