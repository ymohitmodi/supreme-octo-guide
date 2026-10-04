"""Reviewer rubric corpus — what world-leading conference reviewers actually judge.

This is the calibration data that "trains" the judge and the critic. It is NOT
private review text (which no one may redistribute); it encodes the **public**
review dimensions and score anchors that top venues publish in their reviewer
guidelines (IEEE S&P, USENIX Security, NDSS, ACM CCS, NeurIPS/ICML, IEEE SaTML),
together with the **recurring rejection archetypes** those reviewers apply — the
critiques that appear over and over in public OpenReview discussions and PC
statements. Grounding the internal critic and the external judge in these makes
their feedback match how real committees actually reason.

Two structures:

- :data:`DIMENSIONS` — the axes a paper is scored on, each with concrete anchors
  for a weak/borderline/strong score. This is the judge's rubric.
- :data:`ARCHETYPES` — the recurring reasons AI-security papers get rejected,
  each with a lightweight detector over the (idea, experiment, paper) and a
  *constructive remedy* that turns the criticism into a concrete revision. This
  is the critic's attack surface — and how negative feedback becomes actionable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReviewDimension:
    key: str
    name: str
    weight: float                 # contribution to the overall judge score
    question: str                 # the question a reviewer asks
    weak: str                     # anchor for a low score
    strong: str                   # anchor for a high score


# The dimensions top venues score on (harmonized across S&P/USENIX/NeurIPS forms).
DIMENSIONS: tuple[ReviewDimension, ...] = (
    ReviewDimension(
        "soundness", "Soundness / Validity", 0.28,
        "Are the claims supported by the evidence, under an adaptive adversary?",
        "claims exceed the evidence; non-adaptive or single-setting evaluation",
        "claims are precisely scoped and hold under adaptive, compute-matched attacks"),
    ReviewDimension(
        "novelty", "Novelty", 0.20,
        "Is the core idea new relative to the public prior art?",
        "an incremental delta a reviewer can name a close paper for",
        "a genuinely new problem framing or mechanism, clearly delta'd from prior art"),
    ReviewDimension(
        "significance", "Significance / Impact", 0.20,
        "If true, does it matter — does it advance the security of real systems?",
        "a narrow result on a toy setting with unclear real-world stakes",
        "changes how the community should build or evaluate a class of systems"),
    ReviewDimension(
        "reproducibility", "Reproducibility", 0.14,
        "Can an independent team reproduce every number?",
        "no code/seed/spec; numbers cannot be regenerated",
        "released code, fixed seeds, and an exact benchmark spec; artifact-ready"),
    ReviewDimension(
        "clarity", "Clarity / Presentation", 0.10,
        "Is the threat model precise and the write-up self-contained?",
        "vague threat model; results hard to interpret",
        "crisp threat model (knowledge/capability/budget), readable, well-structured"),
    ReviewDimension(
        "ethics", "Ethics / Responsible disclosure", 0.08,
        "Is offensive work paired with defense and coordinated disclosure?",
        "offense with no defense or disclosure; dual-use unaddressed",
        "defense-forward, disclosure stated, dual-use risk explicitly managed"),
)
DIMENSIONS_BY_KEY = {d.key: d for d in DIMENSIONS}
assert abs(sum(d.weight for d in DIMENSIONS) - 1.0) < 1e-9


@dataclass(frozen=True)
class RejectionArchetype:
    id: str
    dimension: str                # which review dimension it hits
    severity: str                 # "major" (reject) | "minor" (revision)
    reviewer_says: str            # the criticism in a real reviewer's voice
    remedy: str                   # the constructive fix — negative → actionable
    # A detector over a bundle dict {tex, finding, n_rows, n_citations, idea, title}.
    detect: "callable" = field(default=None)


def _has(text: str, *pats: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in pats)


# The recurring, real reasons AI-security papers get rejected — each with a
# detector and a constructive remedy. Detectors are deliberately conservative
# (flag only clear misses) so the critic is credible, not noisy.
ARCHETYPES: tuple[RejectionArchetype, ...] = (
    RejectionArchetype(
        "non-adaptive-eval", "soundness", "major",
        "The defense is only evaluated against a fixed/known attack; a reviewer will "
        "assume it breaks under an adaptive adversary that targets it directly.",
        "Add an adaptive-attack evaluation: an adversary with full knowledge of the "
        "defense, compute-matched to the attack budget, and report the worst case.",
        lambda b: not _has(b["tex"] + " " + b["finding"], r"adaptive", r"worst[- ]case",
                           r"knows the defense", r"white[- ]box")),
    RejectionArchetype(
        "weak-baselines", "soundness", "major",
        "Missing strong baselines — without a comparison to the obvious prior defense/"
        "attack, the result's value cannot be judged.",
        "Compare head-to-head against the strongest published baseline and an ablated "
        "variant of your own method; report the delta, not just your number.",
        lambda b: b["n_rows"] < 2),
    RejectionArchetype(
        "single-seed", "reproducibility", "minor",
        "Results come from a single run with no variance — reviewers can't tell signal "
        "from noise.",
        "Report mean ± std (or CIs) over multiple seeds; state the seed and release code.",
        lambda b: not _has(b["tex"], r"seed", r"reproduc", r"released? code", r"confidence interval")),
    RejectionArchetype(
        "unrealistic-threat-model", "clarity", "major",
        "The threat model is vague or unrealistic — the adversary's knowledge, "
        "capability, and budget aren't pinned down, so the contribution is ambiguous.",
        "State the threat model explicitly: what the adversary knows, can do, and how "
        "much compute/queries it has; justify it against a real deployment.",
        lambda b: not _has(b["tex"], r"threat model") or
                  not _has(b["tex"], r"knowledge|capabilit|budget|adversary")),
    RejectionArchetype(
        "overclaiming", "soundness", "major",
        "The conclusions overgeneralize beyond what the (often synthetic/small) "
        "experiment supports.",
        "Scope every claim to the evaluated setting; add a limitations paragraph that "
        "states exactly where the result does and does not hold.",
        lambda b: _has(b["finding"], r"\balways\b", r"\bany model\b", r"\bguarantee",
                       r"\bcompletely\b", r"\bfully\b")),
    RejectionArchetype(
        "thin-novelty", "novelty", "major",
        "The delta over prior art is thin — a reviewer can name a close paper this "
        "largely reproduces.",
        "Sharpen the delta: state the one thing this does that the nearest prior work "
        "cannot, and design an experiment that isolates exactly that.",
        lambda b: b.get("novelty", 1.0) < 0.6),
    RejectionArchetype(
        "no-ablation", "significance", "minor",
        "No ablation — it's unclear which component drives the result, so the "
        "contribution can't be attributed.",
        "Add an ablation that removes each component in turn and reports the effect, "
        "or a sweep that shows the trend.",
        lambda b: b["n_rows"] < 3 and not _has(b["finding"], r"trade-?off", r"vs\.?", r"gap")),
    RejectionArchetype(
        "contaminated-eval", "reproducibility", "minor",
        "Possible benchmark contamination — no statement that the eval set is disjoint "
        "from anything the model/system trained on.",
        "Add a decontamination statement: how the held-out/eval set is provably "
        "disjoint from training data (n-gram/hash check).",
        lambda b: _has(b["tex"], r"benchmark|dataset") and
                  not _has(b["tex"], r"contamination|held[- ]out|disjoint|decontam")),
    RejectionArchetype(
        "offense-no-defense", "ethics", "major",
        "Offensive result with no defense or disclosure — a PC will flag the dual-use "
        "risk and the missing responsible-disclosure statement.",
        "Lead with a defense/mitigation, add an ethics section, and state coordinated "
        "disclosure for anything that could enable misuse.",
        lambda b: _has(b["tex"], r"attack|exploit|jailbreak|poison|evasion|backdoor") and
                  not _has(b["tex"], r"defen[cs]e|mitigation|responsible disclosure|ethics")),
    RejectionArchetype(
        "not-foundational", "significance", "minor",
        "Reads as a point result rather than a foundational contribution — no reusable "
        "benchmark, framework, or principle the community can build on.",
        "Ship a reusable artifact (a benchmark, a metric, or a general defense recipe) "
        "and state the principle it establishes, so others compound on it.",
        # Judge the CONTRIBUTION claim itself (not the boilerplate body), so a point
        # result whose stated contribution promises no reusable artifact is caught.
        lambda b: not _has(b.get("contribution", "") + " " + b.get("title", ""),
                           r"benchmark|framework|protocol|metric|\bfirst\b|principle|"
                           r"reusable|certif|methodology")),
)
ARCHETYPES_BY_ID = {a.id: a for a in ARCHETYPES}


def detect_weaknesses(bundle: dict) -> list[RejectionArchetype]:
    """Return the archetypes whose detector fires on a paper bundle."""
    out = []
    for a in ARCHETYPES:
        try:
            if a.detect and a.detect(bundle):
                out.append(a)
        except Exception:  # noqa: BLE001 — a detector must never crash a run
            continue
    return out


def dimension_anchor(key: str, score: float) -> str:
    d = DIMENSIONS_BY_KEY[key]
    return d.strong if score >= 0.66 else (d.weak if score < 0.5 else "borderline")
