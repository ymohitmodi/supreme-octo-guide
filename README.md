# Dark Factory — Autonomous AI-Security Research Team

An evolving, 24/7 **AI-security research dark factory** built on
[NYX](https://github.com/ymohitmodi/upgraded-palm-tree). It researches AI
security around the clock, **mines** candidate research ideas, **validates** them
against the public prior art of top venues, **iterates** until an idea clears a
strict novelty bar, **runs its own benchmarks**, and **writes conference-grade
LaTeX/PDF papers** — every publication gated by a bar-raiser and a
research-integrity constitution.

It plugs into NYX as a *capability*, so it inherits NYX's continual learning,
Darwin-Gödel evolution, least-privilege tools, and tamper-evident audit ledger.
It runs on a **GPU-less Windows 11 mini-PC** using **Ollama Cloud** models, and
runs **fully offline in deterministic MOCK mode** (no API key) so the entire
pipeline is reproducible in CI.

```
ingest SOTA → mine ideas → bar-raise vs prior art → iterate/revise → deep-dive
            → run real benchmark → write LaTeX/PDF → integrity gate → accept/reject
```

## What it actually does (and what it doesn't)

**It does, for real, today:**
- Maintains a **taxonomy of 10 AI-security frontiers** (prompt injection, jailbreak
  robustness, adversarial examples, data poisoning, membership inference, model
  extraction, agentic security, RAG security, safety evaluation, watermarking) with
  seeded research doctrine.
- **Ingests prior art** — a curated corpus of ~22 landmark AI-security papers,
  augmented live from the arXiv API when online.
- **Mines** structured research ideas (LLM-driven when live; deterministic
  recombination of threat×method×asset primitives offline).
- **Bar-raises novelty** against the prior art (TF-IDF cosine offline; an LLM
  program-committee judge live) and **iterates** ideas that fall short.
- **Runs real, self-contained experiments** — pure-Python, seeded, CPU-only —
  that produce genuine metrics: an injection detector's in-distribution vs
  adaptive generalization gap; FGSM robustness with an adversarial-training
  defense; membership-inference leakage vs training-set size. No placeholder
  numbers.
- **Writes a complete LaTeX manuscript** (abstract, threat model, related work
  grounded in the actual nearest prior art, method, experimental setup, real
  results tables + a dependency-free TikZ figure, discussion, ethics/responsible
  disclosure, and a real bibliography) and **compiles it to PDF** when a TeX
  toolchain is present; otherwise emits `.tex` + Markdown.
- **Enforces integrity gates**: no unsourced numbers, related work required,
  reproducibility required, and responsible disclosure for any offensive framing.
- **Evolves** the `researcher` doctrine with NYX's Darwin-Gödel engine against a
  fitness benchmark, so the methodology that mines better ideas is selected.

**It does not** (and no honest system can) *guarantee* acceptance at IEEE S&P,
USENIX Security, or NeurIPS. What it delivers is a disciplined, reproducible,
gated pipeline that targets those venues' standards. Offline novelty is a
deterministic proxy; the semantic bar-raiser needs a live brain. The bundled
experiments are small synthetic studies chosen so the *mechanism* is real and
reproducible — the **same harness runs unchanged on production-scale datasets**;
swap the data generator.

## Quickstart

```bash
pip install -e ".[dev]"        # pulls NYX from git
python -m darkfactory doctor   # verify NYX, brain mode, TeX availability

python -m darkfactory topics                     # the research frontier
python -m darkfactory ideas prompt-injection     # mine + bar-raise ideas
python -m darkfactory experiment adversarial-examples   # run a real benchmark
python -m darkfactory paper prompt-injection     # produce ONE full paper
python -m darkfactory serve --max 10             # the 24/7 loop: 10 gated papers
python -m darkfactory evolve -g 8                # evolve the researcher doctrine
```

Everything above runs offline. To light up the brain (live idea mining + LLM
bar-raiser + live arXiv ingestion), set `OLLAMA_API_KEY` in `.env` — see
`scripts/setup-windows11.ps1` for the mini-PC setup.

### As a NYX capability

Because it registers itself into NYX on import, the NYX operator console routes to
it automatically:

```bash
OLLAMA_API_KEY=... nyx run "publish AI security research on prompt injection" --keep-going
```

NYX's `CapabilityRunner` then drives plan → refresh knowledge → execute → reflect
→ evolve → consolidate, producing one gated paper per cycle.

## How it works

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the module map and the
evolution/bar-raiser design, and **[docs/RUNBOOK.md](docs/RUNBOOK.md)** for
running it 24/7 and going live.

| Module | Role |
| --- | --- |
| `topics.py` | AI-security taxonomy + seeded research doctrine |
| `conferences.py` | Target-venue registry (scope, cadence, what reviewers reward) |
| `ingest.py` | Prior-art corpus (curated + live arXiv) |
| `ideas.py` | Idea model + mining + revision |
| `novelty.py` | The bar-raiser: novelty/impact/feasibility/rigor scoring |
| `experiments.py` | Self-contained real benchmarks (3 families, pure Python) |
| `paper.py` | LaTeX + PDF + Markdown generation |
| `gates.py` | Research-integrity constitution gates |
| `evolution.py` | Darwinian fitness for the researcher doctrine |
| `pipeline.py` | End-to-end `produce_paper` + 24/7 `serve` |
| `capability.py` | NYX `Capability` wiring |
| `roles.py` | The `researcher` agent genome (registered into NYX) |

## License

MIT.
