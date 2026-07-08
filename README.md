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
It runs on a **GPU-less Windows 11 mini-PC** using the **latest Ollama Cloud**
models (GLM-5.2, DeepSeek-V4-Pro) for highest accuracy, and runs **fully offline
in deterministic MOCK mode** (no API key) so the entire pipeline is reproducible
in CI.

```
ingest SOTA (arXiv MCP) → build on prior contributions → mine foundational ideas
    → bar-raise vs prior art → run real benchmark → write LaTeX/PDF
    → INTERNAL CRITIC attacks + refine loop hardens it  (before any external judge)
    → integrity gate → conference-bar review (calibrated to real rubrics)
    → accept → record contribution → feed weaknesses back into evolution
```

## Internal critic before the external judge

Every draft is first attacked by an **internal adversarial + constructive critic**
— the harshest reviewer it will ever face — *before* any external judge sees it.
The critic is calibrated to the **public review dimensions and rejection archetypes
of top venues** (IEEE S&P, USENIX, NDSS, CCS, NeurIPS/SaTML): it assumes rejection,
names the strongest reason a committee would reject (non-adaptive evaluation, weak
baselines, thin novelty, overclaiming, unrealistic threat model, offense without
defense…), and turns **every criticism into a concrete remedy**. A feedback-driven
**refine loop** then applies those remedies and re-critiques until no major weakness
stands — so negative feedback becomes compounding revisions, not a verdict. Only the
hardened paper reaches the external novelty bar-raiser and conference reviewer, and a
paper is accepted only if it clears the internal critic **and** all external judges.
Recurring weaknesses become **evolution directives**, so the researcher's doctrine
learns to avoid them across cycles.

The critic, judge, and researcher are equipped with **in-depth SOTA skill packs**
(`darkfactory/skills/`) — AI-security state of the art, the frontier-model lifecycle
(Constitutional-AI critique-and-revise, RLVR's verify-or-collapse flywheel,
LLM-as-judge, contamination/Goodhart), the adversarial-critique playbook, the
conference reviewer rubric, and foundational-research heuristics — synced into NYX
long-term memory and recalled while they work.

## Compounding: quality rises every cycle

The factory keeps an **offline research ledger** (`.darkfactory/contributions.jsonl`)
of every accepted paper and what it builds on. Each cycle stands on that
accumulated body of work instead of starting cold, so contributions form a
**deepening lineage** rather than a flat pile — and the **novelty bar ratchets up**
with the factory's accumulated *research capital*, so later papers must be more
impactful than earlier ones to be accepted. Six cycles on one topic, offline:

```
✓ Measuring the cost of indirect injection on tool-call authorization      (depth 0, bar 0.62)
✓ Tightening the certified bound on system-prompt integrity                (depth 1, bar 0.63)
✓ From detection to prevention of multi-agent relay                        (depth 2, bar 0.64)
✓ Cross-threat generalization of content-provenance tags                   (depth 3, bar 0.66)
✓ Tightening the certified bound … (indirect/retrieved)                    (depth 4, bar 0.67)
✓ Cross-threat generalization of taint tracking                            (depth 5, bar 0.68)
research capital 0.00 → 6.45   novelty bar 0.620 → 0.695
```

Each build-on paper **self-cites** the prior contribution it extends and reports a
head-to-head comparison — one concrete step further, every cycle.

## What it actually does (and what it doesn't)

**It does, for real, today:**
- Maintains a **taxonomy of 10 AI-security frontiers** (prompt injection, jailbreak
  robustness, adversarial examples, data poisoning, membership inference, model
  extraction, agentic security, RAG security, safety evaluation, watermarking) with
  seeded research doctrine.
- **Ingests prior art** — a curated corpus of ~22 landmark AI-security papers,
  augmented live from the **[arXiv MCP server](https://github.com/blazickjp/arxiv-mcp-server)**
  (search + `citation_graph` to find exactly what to build on) via NYX's MCP
  support, falling back to the direct arXiv API.
- **Compounds** — records every accepted paper in an offline ledger and builds the
  next paper on the most impactful prior one, with a novelty bar that rises as
  research capital accumulates.
- **Reviews for thoroughness** — a conference-bar reviewer checks each manuscript
  for a precise threat model, baseline comparison, ablation/trade-off,
  reproducibility, grounded related work, limitations, and ethics before accepting.
- **Self-critiques adversarially, then improves** — an internal critic calibrated to
  real venue rubrics attacks each draft and a refine loop applies the fixes before
  external judgment; recurring weaknesses feed back into evolution.
- **Is equipped with SOTA skills** — five in-depth skill packs (AI-security SOTA,
  frontier-model lifecycle, critique playbook, reviewer rubric, foundational
  heuristics) synced into memory so live agents reason from the state of the art.
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
python -m darkfactory serve --max 10             # the 24/7 loop: 10 compounding papers
python -m darkfactory ledger --lineage prompt-injection   # the compounding lineage
python -m darkfactory critique prompt-injection  # internal adversarial+constructive critique
python -m darkfactory rubric                     # the reviewer rubric + rejection archetypes
python -m darkfactory skills-sync                # load SOTA skill packs into memory
python -m darkfactory evolve -g 8                # evolve the researcher doctrine
python -m darkfactory mcp-init                   # register the arXiv MCP server
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
| `ingest.py` | Prior-art corpus (curated + arXiv MCP + arXiv API) |
| `arxiv_mcp.py` | arXiv MCP server integration (search + citation graph) |
| `ideas.py` | Idea model + mining + revision + **build-on extension** |
| `novelty.py` | The bar-raiser: novelty/impact/feasibility/rigor scoring |
| `reviewer_corpus.py` | Real-venue review dimensions + rejection archetypes (judge/critic calibration) |
| `critique.py` | **Internal adversarial+constructive critic** |
| `refine.py` | **Feedback-driven critique→revise loop** (before external judge) |
| `skills/` + `knowledge.py` | SOTA skill packs synced into NYX memory |
| `memory.py` | **Compounding ledger**: contributions, lineage, ratcheting bar |
| `review.py` | Conference-bar thoroughness reviewer |
| `experiments.py` | Self-contained real benchmarks (3 families, pure Python) |
| `paper.py` | LaTeX + PDF + Markdown generation (+ self-citation) |
| `gates.py` | Research-integrity constitution gates |
| `evolution.py` | Darwinian fitness for the researcher doctrine |
| `models.py` | Latest Ollama Cloud model selection |
| `pipeline.py` | End-to-end compounding `produce_paper` + 24/7 `serve` |
| `capability.py` | NYX `Capability` wiring |
| `roles.py` | The `researcher` agent genome (registered into NYX) |

## License

MIT.
