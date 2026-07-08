# Runbook — running the dark factory 24/7

## 0. Prerequisites

- Python 3.10+ (3.11 recommended).
- Internet access for install (NYX is pulled from git) and for live mode.
- Optional: a TeX toolchain (MiKTeX on Windows, TeX Live on Linux) for PDF output.
  Without it, papers are emitted as `.tex` + `.md`.

## 1. Install

```bash
pip install -e ".[dev]"
python -m darkfactory doctor
```

`doctor` should report NYX importable, the `researcher` role and
`ai-security-research` capability registered, the brain mode (MOCK vs Ollama
Cloud), and whether TeX is available.

On a Windows 11 mini-PC use the bundled script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-windows11.ps1
```

## 2. Offline smoke test (no key)

```bash
python -m darkfactory paper prompt-injection
python -m darkfactory serve --max 5
```

Artifacts land in `output/papers/` (`.tex`, `.md`, `.pdf` if TeX present, plus an
`INDEX.md`). Everything is deterministic.

## 3. Go live (Ollama Cloud brain)

Create `.env` (the setup script writes a template):

```
OLLAMA_API_KEY=sk-...                 # from https://ollama.com
OLLAMA_HOST=https://ollama.com
NYX_MODEL_ARCHITECT=qwen3.5-coder:480b-cloud
NYX_MODEL_REVIEWER=glm-5.1:cloud
NYX_MODEL_FAST=gemma4:cloud
NYX_USER_AGENT=dark-factory/0.1 (+research; you@example.com)
```

Cloud models run server-side, so the GPU-less 12 GB mini-PC only orchestrates.
The factory pins the latest high-accuracy models (GLM-5.2, DeepSeek-V4-Pro)
automatically unless you override `NYX_MODEL_*`. Re-run `doctor`; the brain line
should read `Ollama Cloud` and show the models. Now idea mining, the novelty
bar-raiser, thoroughness review, and build-on extension all use the model.

### arXiv MCP server (SOTA ingestion + citation graph)

For live literature ingestion and citation-graph-driven "build on this" targeting,
register the arXiv MCP server once:

```bash
uv tool install "arxiv-mcp-server[pro]"   # needs uv: https://astral.sh/uv
python -m darkfactory mcp-init            # writes it into NYX's MCP manifest
```

NYX launches it via `uvx`/stdio and exposes it as `mcp.arxiv-mcp-server`. Without
it, ingestion falls back to the direct arXiv API and the curated corpus.

### Internal critic, rubric, and SOTA skills

The factory hardens every paper internally before external judgment:

```bash
python -m darkfactory critique prompt-injection   # adversarial+constructive critique + refine
python -m darkfactory rubric                       # the review dimensions + rejection archetypes
python -m darkfactory skills-sync                  # load the SOTA skill packs into NYX memory
```

The critic and judge are calibrated to the **public** review rubrics and recurring
reviewer critique patterns of top venues (from their published reviewer guidelines
and public OpenReview discussions) — not private review text, which is not
redistributable. Live (`OLLAMA_API_KEY` set), the critic and judge additionally
recall the skill packs and reason with the frontier model for sharper, venue-matched
feedback. `skills-sync` runs automatically when the NYX capability seeds memory.

### Long artifacts, OSS bundles, and auto-evolve

```bash
python -m darkfactory limits                        # model context/output budgets
python -m darkfactory artifact prompt-injection     # paper + runnable OSS artifact bundle
python -m darkfactory serve --max 10 --auto-evolve-every 4   # auto-evolve from critique feedback
python -m darkfactory autoevolve --max 8 --every 4  # same, standalone
```

`limits` shows each model's context (~1M) and single-completion output ceiling.
Long papers and code repos are generated section-by-section and continued as
needed, so they never truncate regardless of the ceiling. Each accepted paper's
`output/artifacts/<id>/` bundle is a standalone repo — `cd` into it and run
`python run_benchmark.py` to reproduce the paper's numbers with zero dependencies.
With `--auto-evolve-every N`, recurring critic weaknesses trigger a doctrine
evolution round every N papers automatically.

### Compounding across cycles

Quality compounds through the offline research ledger. Inspect it any time:

```bash
python -m darkfactory ledger                         # capital, bar, recent contributions
python -m darkfactory ledger --lineage prompt-injection   # the build-on chain
```

`serve` and the NYX mission share one ledger, so each paper builds on the last and
the novelty bar ratchets up. The ledger persists at
`.darkfactory/contributions.jsonl` — commit it (or back it up) to keep compounding
across ephemeral environments.

## 4. Continuous operation

The `serve` command produces a bounded batch per invocation. For always-on
operation, schedule it:

**Windows (Task Scheduler):** create a task that runs, on a repeating trigger,

```
<venv>\Scripts\python.exe -m darkfactory serve --max 10 --outdir output\papers
```

Targeting ~5–10 papers/month means a small daily/weekly batch — keep `--max`
modest so each paper gets real iteration and the novelty bar stays meaningful.

**As a NYX mission (recommended for the full learning loop):**

```bash
nyx run "publish AI security research across the frontier" --keep-going --evolve-every 2
```

This drives the CapabilityRunner: each cycle produces one gated paper, evolves the
researcher doctrine every 2 cycles, and consolidates lessons into long-term
memory — so the factory gets better over time.

## 5. Evolving the researcher

```bash
python -m darkfactory evolve -g 8
```

Runs the Darwin-Gödel engine against `ResearchBenchmark`. The best genome is
archived under `.nyx/evolution_archive` and adopted automatically by later runs.

## 6. Inspecting output

- `output/papers/INDEX.md` — every produced paper, accepted (✅) or not (❌), with
  its novelty score and experiment headline.
- `output/papers/paper-*.tex` / `.md` / `.pdf` — the manuscripts.
- `.nyx/audit.ledger.jsonl` — NYX's tamper-evident audit trail (verify with
  `nyx ledger --verify`).
- `nyx memory --recall "prompt injection"` — the accumulated doctrine + track
  record.

## 7. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `doctor` shows brain = MOCK | No `OLLAMA_API_KEY`; fine for offline, set it to go live. |
| No PDF, only `.tex`/`.md` | No TeX toolchain; install MiKTeX / TeX Live. |
| Every paper accepted offline | Offline novelty is a deterministic proxy; the strict semantic bar-raiser needs the live brain. |
| arXiv not augmenting corpus | Network/allowlist; the factory falls back to the curated corpus by design. |
| Papers on a topic look similar | Increase `--max` spread across topics, or run live where mining is semantic; offline uses `variant` rotation for diversity. |
