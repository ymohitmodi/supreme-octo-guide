"""Generate one conference-grade AI-security paper, end to end, offline.

    python examples/generate_paper.py prompt-injection

Runs the full dark-factory pipeline for a topic — ingest prior art, mine and
bar-raise ideas against it, run a real benchmark, and write a LaTeX (+ PDF if a
TeX toolchain is present) and Markdown paper — then prints where the artifacts
landed. No API key required; the whole thing is deterministic in mock mode.
"""
from __future__ import annotations

import os
import sys

# Allow running from a fresh checkout without `pip install` (adds the repo root).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from darkfactory.pipeline import produce_paper  # noqa: E402
from darkfactory.topics import TOPICS  # noqa: E402


def main() -> int:
    topic = sys.argv[1] if len(sys.argv) > 1 else "prompt-injection"
    if topic in ("-h", "--help"):
        print(__doc__)
        print("Topics:", ", ".join(t.slug for t in TOPICS))
        return 0
    result = produce_paper(topic, outdir="output/papers")
    print(result.summary())
    if result.artifact:
        print(f"\nLaTeX : {result.artifact.tex_path}")
        print(f"Markdown: {result.artifact.md_path}")
        if result.artifact.compiled:
            print(f"PDF   : {result.artifact.pdf_path}")
        else:
            print("PDF   : (install a TeX toolchain — e.g. MiKTeX — to compile)")
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
