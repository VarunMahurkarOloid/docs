"""Phase 8: add redirects for URLs that were live under the previous docs.json.

The committed docs.json was the deployed configuration, so these 12 paths were
real URLs. Their files were deleted during the migration and nothing pointed
them anywhere, so they 404 today.

Where the old path maps cleanly onto one new page it redirects there. Where the
old structure (per-platform "connect" / "vault" sub-products) has no single
successor, it redirects to the nearest overview rather than guessing a page -
those are marked AMBIGUOUS below and are worth a human decision.

03_build_nav.py replaces only the `navigation` key, so this block survives
regeneration. Idempotent.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

REDIRECTS = [
    # --- clean successors ---
    ("/passwordless/windows/overview", "/passwordless/windows/passwordless/overview"),
    ("/passwordless/ios/overview", "/passwordless/ios/connect/overview"),
    ("/passwordless/ios/connect/getting-started", "/passwordless/ios/connect/overview"),
    ("/passwordless/android/overview", "/passwordless/android/devicelock/overview"),
    ("/passwordless/web/vault/getting-started", "/passwordless/web/chrome-vault/overview"),
    ("/passwordless/web/connect/getting-started", "/passwordless/web/webkey/overview"),
    # --- AMBIGUOUS: no single successor, sent to the nearest overview ---
    ("/passwordless/windows/connect/getting-started", "/passwordless/windows/passwordless/overview"),
    ("/passwordless/windows/vault/getting-started", "/passwordless/windows/passwordless/overview"),
    ("/passwordless/android/connect/getting-started", "/passwordless/android/devicelock/overview"),
    ("/passwordless/android/vault/getting-started", "/passwordless/android/devicelock/overview"),
    ("/passwordless/ios/vault/getting-started", "/passwordless/ios/connect/overview"),
    ("/passwordless/web/overview", "/passwordless/overview"),   # webkey vs chrome-vault
]

cfg = json.load(open("docs.json", encoding="utf-8"))
existing = {r["source"]: r for r in cfg.get("redirects", [])}
for src, dst in REDIRECTS:
    existing[src] = {"source": src, "destination": dst}
cfg["redirects"] = [existing[s] for s in sorted(existing)]

missing = [d for _, d in REDIRECTS if not os.path.exists(d.lstrip("/") + ".mdx")]
if missing:
    raise SystemExit(f"ABORT: redirect destinations do not exist: {missing}")

with open("docs.json", "w", encoding="utf-8", newline="\n") as fh:
    json.dump(cfg, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

print(f"docs.json now declares {len(cfg['redirects'])} redirects; "
      "all destinations resolve to real pages")
