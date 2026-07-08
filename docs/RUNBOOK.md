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
Re-run `doctor`; the brain line should read `Ollama Cloud`. Now idea mining, the
novelty bar-raiser, and revision use the model, and ingestion augments the corpus
from live arXiv.

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
