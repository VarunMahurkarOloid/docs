"""Back up every .mdx to a SHORT destination root.

The migrated filenames are long; nesting them under the deep scratchpad path
blows Windows' 260-char MAX_PATH and silently skips files.
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEST = r"C:\mdxbk"
SKIP = (".git", "node_modules", "images")

os.chdir(ROOT)
if os.path.isdir(DEST):
    shutil.rmtree(DEST)

copied = failed = 0
longest = 0
for dp, dn, fn in os.walk("."):
    dn[:] = [d for d in dn if d not in SKIP]
    for f in fn:
        if not f.endswith(".mdx"):
            continue
        src = os.path.join(dp, f)
        dst = os.path.join(DEST, os.path.relpath(src, "."))
        longest = max(longest, len(os.path.abspath(dst)))
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        except OSError as e:
            failed += 1
            print("FAILED", src, e)

total = sum(len([f for f in fn if f.endswith(".mdx")])
            for dp, dn, fn in os.walk(".")
            if not any(s in dp for s in SKIP))
print(f"copied {copied} / {total} mdx  (failed {failed}), longest dest path {longest}")
