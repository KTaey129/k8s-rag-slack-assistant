"""Fetch the Kubernetes docs (markdown source) via a sparse git clone.

We pull straight from the kubernetes/website repo instead of scraping
kubernetes.io, since the source markdown is clean, versioned, and doesn't
require an HTML parser.
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/kubernetes/website.git"
SPARSE_PATH = "content/en/docs"

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data" / "k8s-docs"
TMP_CLONE = ROOT / "data" / "_website-clone"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    if DEST.exists():
        print(f"{DEST} already exists — remove it first if you want a fresh fetch.")
        sys.exit(0)

    if TMP_CLONE.exists():
        shutil.rmtree(TMP_CLONE)
    TMP_CLONE.mkdir(parents=True)

    run(["git", "init", "-q"], cwd=TMP_CLONE)
    run(["git", "remote", "add", "origin", REPO_URL], cwd=TMP_CLONE)
    run(["git", "config", "core.sparseCheckout", "true"], cwd=TMP_CLONE)
    (TMP_CLONE / ".git" / "info" / "sparse-checkout").write_text(SPARSE_PATH + "\n")
    run(["git", "pull", "--depth", "1", "origin", "main"], cwd=TMP_CLONE)

    src = TMP_CLONE / SPARSE_PATH
    shutil.move(str(src), str(DEST))
    shutil.rmtree(TMP_CLONE)

    md_count = sum(1 for _ in DEST.rglob("*.md"))
    print(f"Fetched {md_count} markdown files into {DEST}")


if __name__ == "__main__":
    main()
