# Architecture

The dark factory is a NYX **capability** — a self-contained goal handler that
NYX's generic `CapabilityRunner` drives autonomously. Everything below is a plain
Python module under `darkfactory/`; the only external contract is NYX's
`Capability` base class and its provider / memory / evolution / tools interfaces.

## The loop

NYX's `CapabilityRunner` runs, for each cycle:

```
plan → refresh_knowledge → (assemble context) → execute → reflect
     → evolve (every N) → consolidate (every M) → repeat
```

Our capability maps those hooks to research work:

- **`plan(objective)`** → a backlog of topics. A specific topic named in the
  objective leads the backlog, then the frontier is swept for diversity.
- **`refresh_knowledge(ctx)`** → ingest a rotating topic's prior art into NYX
  long-term memory (curated corpus ∪ live arXiv), marked `trusted=False` so
  external text can never become governing doctrine (memory-poisoning
  containment).
- **`execute(task)`** → run `pipeline.produce_paper` for one topic: **one cycle =
  one paper**. The realized outcome (accepted/rejected, novelty, experiment
  headline) is written back as a *track record* memory.
- **`benchmark(ctx)`** → the `ResearchBenchmark` the evolution engine selects
  against.

## The pipeline (`pipeline.produce_paper`)

1. **Ingest** (`ingest.ingest_topic`) — build the prior-art corpus for the topic.
2. **Mine** (`ideas.mine_ideas`) — generate candidate ideas. Live: the brain
   proposes ideas grounded in the recalled prior art. Offline: deterministic
   recombination of the topic's `threat_models × methods × assets` through four
   research *frames* (certify / adaptively-evaluate / provenance-defend /
   cost-measure), rotated by a `variant` so successive runs on a topic explore
   different directions.
3. **Bar-raise** (`novelty.assess`) — score each idea's novelty against the
   corpus (TF-IDF cosine offline; an LLM PC-reviewer live) plus heuristic
   impact/feasibility/rigor. Ideas below the bar (`novelty ≥ 0.62` **and**
   `fitness ≥ 0.60`) are **iterated** (`ideas.revise_idea`) up to three times.
4. **Deep-dive + experiment** (`experiments.run_experiment`) — run the real
   benchmark for the topic family and collect metrics.
5. **Write** (`paper.write_paper`) — assemble LaTeX/Markdown from the idea, the
   bar-raiser's report, and the experiment; compile PDF if TeX is present.
6. **Gate** (`gates.check_research`) — the integrity constitution must pass;
   acceptance requires clearing both the novelty bar and the gate.

## The bar-raiser (`novelty.py`)

The assessor is deliberately strict — selection, not generation, is where quality
is enforced. Novelty is `1 − max cosine similarity` to any prior-art abstract
(offline), or an LLM judge's rating seeded with the offline nearest-neighbors
(live). The verdict (`pass` / `revise` / `reject`) drives the iteration loop and
the final accept/reject. This is the "validate against existing conference
publications" and "all publications must go through" requirement, made mechanical.

## Real experiments (`experiments.py`)

Pure-Python, seeded, CPU-only — so the numbers are honest and reproducible in CI,
and the same harness scales to real data by swapping the data generator. Three
families cover the taxonomy:

- **injection-detection** — trains a detector on benign-vs-injection prompts and
  reports the **in-distribution vs adaptive (unseen-payload) generalization gap**.
- **robustness** — trains a classifier, attacks with FGSM across ε, then
  **adversarially trains** it (adv examples recrafted against the model each
  epoch) and reports the clean/robust trade-off.
- **membership-inference** — measures the loss-threshold attack's AUC and
  TPR@FPR=0.1 **as training-set size grows**, isolating memorization as the root
  cause and data scale as the mitigation.

A subtle correctness point baked into the harness: train and test splits share
one ground-truth boundary, so effects are real and not distribution-shift
artifacts.

## Evolution (`evolution.py` + `roles.py`)

The `researcher` genome (a charter/system-prompt + params) is the unit of
selection. `ResearchBenchmark.evaluate(genome)` scores a genome by the mean
fitness of the ideas its doctrine would mine across held-out topics, where the
doctrine's *methodology strength* (adaptive evaluation, certified bounds,
contamination control, reproducibility, responsible disclosure, attacker-cost
metrics) lifts the rigor and impact of each idea. The NYX Darwin-Gödel engine
mutates charters by grafting `RESEARCH_DIRECTIVES` and admits a variant only if
it empirically outscores its predecessor — so good research method is *discovered*
by selection, not hand-coded. Keyword credit is capped to prevent reward-hacking
by stuffing.

## Governance (`gates.py`)

Four forbidden rules extend NYX's constitution: no fabricated results, related
work required, reproducibility required, and responsible disclosure for offensive
framing. They are enforced both as callable checks (`check_research`) and as
constitution `forbidden` lines, so a paper cannot ship past them.

## Offline vs live

| Stage | Offline (MOCK, deterministic) | Live (Ollama Cloud) |
| --- | --- | --- |
| Ingest | curated corpus | + arXiv API |
| Mine | primitive recombination | LLM proposes grounded ideas |
| Bar-raise | TF-IDF cosine + heuristics | LLM PC-reviewer judge |
| Revise | frame/threat pivot | LLM differentiates vs prior art |
| Experiment | real (pure Python) | real (identical) |
| Paper | LaTeX/MD (+PDF if TeX) | identical |

The offline path is what CI exercises; the live path swaps generation and judging
for the brain while keeping the same gates and experiments.
