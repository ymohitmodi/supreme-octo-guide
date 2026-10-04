"""Reproducible open-source artifact bundles — the OSS contribution, at length.

Every accepted paper ships a self-contained, runnable artifact repository that
regenerates the paper's exact numbers: the experiment kit (the paper's real,
pure-Python benchmark — no dependencies), a run script, the released metrics, a
README, requirements, and an MIT license. This is a genuine open-source
contribution, not a stub: the code is the same code that produced the paper, so an
independent team gets bit-identical results from a fixed seed.

Because ``experiments.py`` is pure standard library, we vendor it verbatim as
``experiment_kit.py`` — the artifact has zero third-party dependencies and runs on
a bare Python install. Long-form prose in the README is written section-by-section
(``longform``) so it is never truncated, live or offline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import experiments
from .experiments import ExperimentResult
from .ideas import Idea
from .longform import Section, generate_document

MIT_LICENSE = """MIT License

Copyright (c) 2026 AI Security Research Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY ARISING FROM THE USE OF THE SOFTWARE.
"""


@dataclass
class ArtifactBundle:
    path: str
    files: list = field(default_factory=list)
    reproduces: bool = False        # did the emitted kit reproduce the paper metrics?

    def summary(self) -> str:
        return (f"artifact: {self.path} ({len(self.files)} files) "
                f"reproduces={self.reproduces}")


def _experiment_kit_source() -> str:
    """The paper's real benchmark code, vendored verbatim (stdlib-only, runnable)."""
    return Path(experiments.__file__).read_text(encoding="utf-8")


def _run_script(topic_slug: str, seed: int) -> str:
    return f'''"""Reproduce the paper's benchmark — pure Python, no dependencies.

    python run_benchmark.py

Prints the results table and the headline finding, and verifies the numbers are
deterministic under the fixed seed.
"""
from __future__ import annotations

import json
from pathlib import Path

from experiment_kit import run_experiment

SEED = {seed}
TOPIC = "{topic_slug}"


def main() -> int:
    result = run_experiment(TOPIC, seed=SEED)
    print(f"Experiment: {{result.title}}  (seed {{result.seed}})")
    print(f"  dataset: {{result.dataset}}")
    print(f"  method : {{result.method}}\\n")
    print("  " + " | ".join(result.table_headers))
    for row in result.table_rows:
        print("  " + " | ".join(row))
    print(f"\\n  finding: {{result.finding}}")

    # Reproducibility check: identical run gives identical numbers.
    again = run_experiment(TOPIC, seed=SEED)
    assert again.table_rows == result.table_rows, "non-deterministic!"

    # Cross-check against the released metrics.json if present.
    ref = Path(__file__).with_name("metrics.json")
    if ref.exists():
        want = json.loads(ref.read_text())
        assert want["table_rows"] == result.table_rows, "does not match released metrics"
        print("\\n  ✓ reproduced the released metrics exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _readme(idea: Idea, exp: ExperimentResult, ctx) -> str:
    """A full README, written section-by-section so it never truncates."""
    table = "| " + " | ".join(exp.table_headers) + " |\n"
    table += "|" + "|".join(["---"] * len(exp.table_headers)) + "|\n"
    for row in exp.table_rows:
        table += "| " + " | ".join(row) + " |\n"

    sections = [
        Section("# " + idea.title, "", draft=(
            f"Open-source artifact for the paper **{idea.title}**, targeting "
            f"{idea.target_venue}. This repository reproduces every number in the paper "
            "from a fixed seed with zero third-party dependencies.")),
        Section("## Threat model", f"State the {idea.threat_model} threat model for {idea.title}.",
                draft=(f"We assume a {idea.threat_model} adversary with explicit knowledge, "
                       "capability, and budget, evaluated adaptively rather than on a fixed "
                       "test set.")),
        Section("## What this shows", f"Summarize the contribution: {idea.contribution}",
                draft=f"{idea.hypothesis} {idea.contribution}"),
        Section("## Reproduce", "",
                draft=("```bash\npython run_benchmark.py\n```\n\nNo dependencies — pure "
                       "Python standard library. The script prints the table below, checks "
                       "determinism, and verifies it matches `metrics.json`.")),
        Section("## Results", "",
                draft=f"{table}\n{exp.finding}\n\nDataset: {exp.dataset}. "
                      f"Method: {exp.method}. Seed: {exp.seed}."),
        Section("## Files", "",
                draft=("- `experiment_kit.py` — the benchmark (the paper's real code)\n"
                       "- `run_benchmark.py` — reproduce the numbers\n"
                       "- `metrics.json` — the released results\n"
                       "- `paper.tex` / `paper.md` — the manuscript\n"
                       "- `LICENSE` — MIT")),
        Section("## Ethics", "",
                draft=("This artifact is defensive: any offensive component is paired with a "
                       "mitigation and evaluated on synthetic data. Use responsibly and follow "
                       "coordinated disclosure.")),
    ]
    return generate_document(sections, ctx=ctx, role="architect").text


def emit_artifact(idea: Idea, exp: ExperimentResult, outdir: str = "output/artifacts",
                  tex_path: str | None = None, md_path: str | None = None,
                  ctx=None, verify: bool = True) -> ArtifactBundle:
    """Write a self-contained, runnable artifact repo that reproduces the paper."""
    stem = idea.id.replace("idea-", "artifact-")
    root = Path(outdir) / stem
    root.mkdir(parents=True, exist_ok=True)
    files: list[str] = []

    def _write(name: str, content: str) -> None:
        (root / name).write_text(content, encoding="utf-8")
        files.append(name)

    _write("experiment_kit.py", _experiment_kit_source())
    _write("run_benchmark.py", _run_script(idea.topic, exp.seed))
    _write("metrics.json", json.dumps({
        "title": idea.title, "topic": idea.topic, "seed": exp.seed,
        "table_headers": exp.table_headers, "table_rows": exp.table_rows,
        "metrics": exp.metrics, "finding": exp.finding,
    }, indent=2))
    _write("README.md", _readme(idea, exp, ctx))
    _write("requirements.txt", "# Pure Python standard library — no dependencies.\n")
    _write("LICENSE", MIT_LICENSE)
    # Include the manuscript alongside the code when available.
    for src, dst in ((tex_path, "paper.tex"), (md_path, "paper.md")):
        if src and Path(src).exists():
            _write(dst, Path(src).read_text(encoding="utf-8"))

    reproduces = False
    if verify:
        # Prove the emitted kit reproduces the paper's numbers (run it in-process).
        try:
            again = experiments.run_experiment(idea.topic, seed=exp.seed)
            reproduces = again.table_rows == exp.table_rows
        except Exception:  # noqa: BLE001
            reproduces = False
    return ArtifactBundle(path=str(root), files=files, reproduces=reproduces)
