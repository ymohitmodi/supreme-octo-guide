# Conference Reviewer Rubric — how top venues actually score AI-security papers

The judge's calibration. This encodes the **public** review dimensions and the
recurring rejection patterns of IEEE S&P, USENIX Security, NDSS, ACM CCS, and
NeurIPS/ICML/SaTML — from their published reviewer guidelines and public
OpenReview discussions, not any private review text. Score on these dimensions with
these anchors and the internal verdict will track the external one.

## The scoring dimensions and their weights

Reviewers score on roughly six axes. **Soundness/validity (~28%)** — are claims
supported, under an adaptive adversary? This dominates; a soundness failure is
usually fatal. **Novelty (~20%)** — new relative to public prior art. **Significance/
impact (~20%)** — if true, does it change how systems are built or evaluated?
**Reproducibility (~14%)** — can every number be regenerated from released code,
seeds, and spec? **Clarity (~10%)** — precise threat model, self-contained.
**Ethics/disclosure (~8%)** — offense paired with defense and coordinated
disclosure. A paper clears the bar when soundness is strong AND the weighted total
is high AND no single dimension is disqualifying.

## Score anchors (weak → strong)

For each dimension, calibrate to concrete anchors. **Soundness**: weak = non-adaptive
or single-setting evaluation, claims exceed evidence; strong = precise claims that
hold under adaptive, compute-matched attacks. **Novelty**: weak = an increment a
reviewer can name a close paper for; strong = a new framing or mechanism, clearly
delta'd. **Significance**: weak = a toy result with unclear stakes; strong = changes
practice for a class of systems. **Reproducibility**: weak = no code/seed; strong =
artifact-ready. **Clarity**: weak = vague threat model; strong = crisp
knowledge/capability/budget threat model. **Ethics**: weak = offense with no defense;
strong = defense-forward with disclosure.

## The recurring rejection archetypes

These reasons appear again and again; a paper that trips a *major* one is rejected.
Major: **non-adaptive evaluation** (defense only tested against a known/fixed
attack); **missing strong baselines** (no head-to-head, no ablation); **unrealistic
or vague threat model**; **overclaiming** beyond the evidence; **thin novelty** (a
nameable close paper); **offense without defense/disclosure**. Minor (revision):
**single-seed/no-variance** results; **no ablation**; **possible contamination** (no
disjointness statement); **not foundational** (a point result with no reusable
artifact). The judge should name which archetype a paper triggers, because that is
the language of the actual decision.

## How a committee reaches a decision

Reviews are discussed, not averaged blindly: a single confident, well-argued
soundness objection can sink a paper three reviewers liked. Champions matter — a
paper needs a reviewer who will argue *for* it, which requires a crisp, defensible
core contribution. Rebuttals can fix minor issues (add a seed, an ablation, a
disclosure statement) but rarely a major one (a broken threat model or non-adaptive
evaluation). The implication for the factory: fix all *major* weaknesses internally
before submission, and make the core contribution sharp enough that a champion could
defend it in one sentence.

## Calibration discipline

Judge on the rubric, not on gestalt or prose polish. Resist LLM-judge biases:
length and confident tone are not quality; the author's own framing is not evidence;
name the specific dimension and archetype behind every score. Report per-dimension
scores plus the overall, and state the single reason for the accept/reject decision
— the way a real meta-review does.
