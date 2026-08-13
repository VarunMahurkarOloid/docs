# docs-nav

`docs.json` navigation and the `overview.mdx` card pages are **generated** from
the frontmatter already present on each page. Edit the mapping tables in
`03_build_nav.py` and re-run it — do not hand-edit `navigation` in `docs.json`,
it will be overwritten.

## Where structure comes from

| Frontmatter field | Becomes |
| --- | --- |
| `primaryCategory` | tab + menu item (via the `TABS` table) |
| `source.section`  | group, after cleaning and super-grouping |
| `title`           | page label and generated `sidebarTitle` |

Two normalizations make the raw Intercom sections usable:

1. Product tokens redundant inside their own category are stripped
   (`"Videos-Supervisor App"` → `"Videos"` inside the Supervisor menu item).
2. Video sections nest as a `Videos` subgroup under their base topic
   (`"Create and Manage Users - Video Tutorials"` under `"Create and Manage Users"`).

Super-groups are classified on the **raw** section name, because cleaning strips
the very tokens the patterns match on.

## Scripts

Run from the repo root. All are idempotent.

| Script | Purpose |
| --- | --- |
| `00_backup.py` | Copy every `.mdx` to `C:\mdxbk` (short path — long filenames overflow `MAX_PATH` under a deep temp dir). Run before any bulk edit. |
| `02_recategorize.py` | One-shot: retired the `_review/uncategorized` staging bucket. Kept for reference. |
| `03_build_nav.py` | **Main generator.** Rewrites `navigation` in `docs.json` and regenerates every `overview.mdx`. |
| `04_components.py` | Mechanical MDX component pass over article bodies. |
| `05_escape_angles.py` | Escapes bare `<placeholder>` prose that MDX parses as JSX. `--check` to dry-run. |
| `06_sidebar_titles.py` | Makes `sidebarTitle` unique within each nav group. Run **after** `03`. |
| `07_redirects.py` | Redirects for URLs that were live under the previous docs.json. |
| `verify.py` | Link/image/nav integrity. Must print `ALL CLEAN`. |
| `mdxcheck.py` | JSX tag balance and frontmatter sanity. |

Typical loop after adding or re-migrating content:

```
python scripts/docs-nav/00_backup.py
python scripts/docs-nav/04_components.py
python scripts/docs-nav/05_escape_angles.py
python scripts/docs-nav/03_build_nav.py
python scripts/docs-nav/06_sidebar_titles.py
python scripts/docs-nav/07_redirects.py
python scripts/docs-nav/verify.py && python scripts/docs-nav/mdxcheck.py
```

`ROOT` is derived from each script's own location. The one remaining absolute
path is `DEST = C:\mdxbk` in `00_backup.py` — deliberately short, because the
migrated filenames overflow Windows' 260-char `MAX_PATH` under a deeper root.
Change it to any other short path if `C:\` is not writable.

Generated overview pages carry a marker comment; `03_build_nav.py` sweeps and
recreates them, so stale ones never linger. Anything without that marker is
treated as hand-written and is never deleted.

## Known false positive: `mint broken-links`

`mint broken-links` (CLI v4.2.800) reports ~7.4k broken links here. It is wrong.
It cannot resolve any link whose target lives in a **subdirectory**, even when
the file exists and is listed in `docs.json`. Minimal reproduction — three pages,
all in nav:

```
root-page.mdx
administration/admin-portal/x.mdx   ->  [a](/root-page)                      OK
                                        [b](/administration/admin-portal/y)  "broken"
administration/admin-portal/y.mdx
```

Relative (`y`, `./y`) and prefix-less forms are rejected too. Use `verify.py`
instead, which resolves every link against the files on disk and the navigation
tree. `mint broken-links` is still useful for its MDX **syntax** errors, which
are real — that is how the unescaped `<placeholder>` bugs were found.
