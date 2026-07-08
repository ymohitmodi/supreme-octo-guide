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

## Compounding (`memory.py`)

Every accepted paper is recorded as a `Contribution` in an offline, append-only
ledger (`.darkfactory/contributions.jsonl`) with the lineage of what it builds on.
Two mechanisms turn accumulation into *rising* quality:

- **Build-on lineage** — before mining, `produce_paper` looks up the most impactful
  prior contribution on the topic and asks `ideas.extend_idea` for candidates that
  take it one concrete step further (tighter bound, detection→prevention, new
  threat model). These compete with fresh ideas and are preferred when they clear
  the bar, so contributions form a deepening chain (`depth` grows each cycle).
- **Ratcheting bar** — `ResearchLedger.current_bar()` raises the novelty threshold
  as `research_capital()` (sum of impact scores, amplified by lineage depth) grows,
  bounded at 0.80. Later cycles must be more novel/impactful than earlier ones to
  be accepted.

The accepted paper self-cites the prior contribution it extends (`paper.py`
`builds_on_titles`) and reports a head-to-head comparison. The ledger persists
across runs, so the factory never starts cold.

## The pipeline (`pipeline.produce_paper`)

0. **Compound** — load the ledger, compute this cycle's ratcheting novelty bar,
   and build extension candidates from the best prior contribution on the topic.
1. **Ingest** (`ingest.ingest_topic`) — build the prior-art corpus: curated ∪
   arXiv MCP server ∪ arXiv API (see below).
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
5b. **Internal critique → refine** (`critique.py`, `refine.py`) — BEFORE any
   external judge, an adversarial+constructive critic attacks the draft and a
   feedback loop applies each remedy until no major weakness stands (see below).
6. **Gate + review** — `gates.check_research` (integrity) and `review.review`
   (conference-bar thoroughness) must both pass. Acceptance requires clearing the
   **internal critic** (no unresolved major) **and** the ratcheting novelty bar
   **and** the integrity gate **and** the thoroughness review.
7. **Record + learn** — an accepted paper is written to the ledger with its
   build-on edge; recurring critique weaknesses become evolution directives.

## The internal critic and feedback-driven refinement

The critic (`critique.py`) is calibrated by `reviewer_corpus.py` — the **public**
review dimensions (soundness 28%, novelty 20%, significance 20%, reproducibility
14%, clarity 10%, ethics 8%) and the recurring **rejection archetypes** top venues
apply, each with a detector and a *constructive remedy*. Offline it is a
deterministic detector pass; live, an LLM critic equipped with the skill packs
refines it, seeded by the deterministic weaknesses so it reasons about real flaws.

`refine.py` runs the Constitutional-AI **critique → revise** loop: draft → critic →
apply each remedy to the idea/paper → re-critique, until no major weakness remains
or the budget is spent. This is why negative feedback is *compounding*, not a
verdict — every criticism becomes a revision, so the paper reaching the external
judge is already the hardened version. Recurring weaknesses are emitted as
**evolution directives** (fed into the researcher genome's mutation pool) and
written to memory, so the doctrine improves across cycles — feedback-driven
evolution. Acceptance gates on the internal critic first, so the internal verdict
predicts and precedes the external one.

## SOTA skill packs (`skills/`, `knowledge.py`)

Five in-depth markdown packs encode the state of the art: AI-security SOTA (threat
surface, what's foundational, the methodological bar), the frontier-model lifecycle
(Constitutional AI, RLVR's verify-or-collapse flywheel, LLM-as-judge,
contamination/Goodhart, red-teaming — distilled from *The Frontier Model Field
Manual*), the adversarial-critique playbook, the conference reviewer rubric, and
foundational-research heuristics. `knowledge.sync_skills` ingests them via NYX's
`sync_skills` (one long-term memory lesson per `##` section), so the live critic,
judge, and researcher recall exactly the relevant guidance while they work. The
capability seeds them automatically; `darkfactory skills-sync` does it manually.

## arXiv MCP + SOTA ingestion (`arxiv_mcp.py`, `ingest.py`)

NYX's MCP support (`nyx.tools.mcp`) registers external tool servers from a
manifest and exposes each as `mcp.<name>`; this capability is allowed `mcp.*`.
`arxiv_mcp.write_arxiv_manifest` adds the
[arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server) (launched via
`uvx`/stdio). When it is registered, `ingest_topic` calls its `search_papers` for
SOTA, and the pipeline can use `citation_graph` (the server's `[pro]` extra) to
find the exact prior work to build on. Everything is best-effort: with no MCP
server, uv, or network, ingestion falls back to the direct arXiv API and then the
curated corpus, so runs never block.

## The conference-bar reviewer (`review.py`)

Distinct from the novelty bar-raiser (which judges the *idea*), this judges the
*paper*'s thoroughness against what a program committee rejects for: a precise
threat model, a baseline comparison, quantitative results, reproducibility (all
critical), plus ablation/trade-off, grounded related work, limitations, and ethics.
Offline it inspects the manuscript + experiment structurally; live, an LLM
PC-reviewer refines the borderline call. A critical miss fails the paper outright.

## Latest models (`models.py`)

`apply_models(cfg)` upgrades a NYX `Config` to the highest-accuracy Ollama Cloud
models (GLM-5.2 for reasoning/writing, DeepSeek-V4-Pro for the strict reviewer)
without clobbering an explicit `NYX_MODEL_*` override. Applied by the CLI's live
context and shown by `doctor`.

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
