# Frontier-Model Lifecycle — the SOTA methods a security researcher must reuse

Distilled from *The Frontier Model Field Manual*. A frontier model flows through
seven stages — data → architecture → pretraining → post-training → evaluation →
inference → deploy/learn — and safety threads through every node. An AI-security
researcher attacks and defends this whole machine, and reuses its own methods
(self-critique, verifiable rewards, LLM-as-judge) to build a research factory that
improves itself. These are the load-bearing ideas.

## Constitutional AI and the critique-and-revise loop

The single most important method for self-improvement: a model improves its own
output by **critiquing it against explicit principles, then revising** — no human
label in the inner loop (RLAIF). The pattern is *draft → critique against a
constitution → revise → repeat*. Applied to research, this is exactly how a paper
should be hardened *before* an external judge sees it: an internal adversarial
critic attacks the draft against a rubric, a reviser turns each criticism into a
concrete fix, and the cycle repeats until the critic is satisfied. Negative
feedback is not a verdict — it is the input to the next revision. The constitution
(the rubric) must be explicit and stable so critique is consistent, not vibes.

## RLVR and the verify-or-collapse flywheel

Reasoning models exploded because of **RL from Verifiable Rewards**: reward the
model only when an answer is *programmatically checkable* (code runs and passes
tests; math checks out). The synthetic-data flywheel is the same idea — generate →
**verify/filter** → train on the survivors → generate better → repeat. The lesson
that transfers to a research factory: *the verify step is load-bearing*. Remove it
and you get the photocopy-of-a-photocopy failure (model collapse); ideas drift,
numbers inflate, quality decays. So every research cycle must ground its claims in
a real, runnable experiment (a verifier), and every self-generated improvement must
pass an objective check before it is kept. Compounding without verification is
collapse; compounding *with* verification is capability.

## LLM-as-judge, and why judges must be calibrated

Frontier evaluation increasingly uses an LLM to judge outputs — cheap and scalable,
but only trustworthy when the judge is **calibrated against a rubric and checked
for bias** (position bias, verbosity bias, self-preference). A good judge scores on
explicit dimensions with concrete anchors, not a gestalt number, and its
agreement with strong human raters is measured. For a research factory this means:
the paper judge must score on the *same dimensions real committees use* (soundness,
novelty, significance, reproducibility, clarity, ethics), with anchors, and it must
be distinct from the author so it can be adversarial.

## The eval problem: contamination and Goodhart

Two failure modes dominate evaluation. **Contamination**: benchmark data leaks into
training, so scores are memorized, not earned — the most common embarrassing
mistake; decontamination (n-gram/hash disjointness) is mandatory for any credible
claim. **Goodhart**: once a metric is a target it stops measuring what you care
about — leaderboard-chasing produces gains smaller than the noise. Defenses:
held-out, contamination-controlled suites; adaptive evaluation; confidence
intervals; and metrics that resist gaming (real-world/agentic tasks over
multiple-choice). A security paper that ignores these will be rejected for exactly
these reasons.

## Red-teaming and scalable oversight

Safety is engineered as **defense-in-depth across the lifecycle**, capability-
proportionate, and stress-tested by **red-teaming** — adversaries actively trying
to break the system, not a fixed test set. When the system is too capable to check
directly, **scalable oversight** (AI-assisted review, debate, task decomposition,
weak-to-strong generalization) supervises it. The research analogue: an internal
red-team critic that adversarially attacks each paper, and a decomposition of the
review into checkable dimensions so a weaker judge can still catch strong papers'
flaws.

## Preference optimization: PPO, DPO, GRPO

Behavior is shaped by preference optimization. **DPO** is offline, simple, and
stable — learn directly from (preferred, rejected) pairs. Online RL (**PPO/GRPO**)
has a higher ceiling and is required for verifiable rewards. The transferable idea:
accumulate a dataset of (better, worse) research artifacts — accepted vs rejected
drafts, pre- vs post-critique versions — and let the factory's doctrine evolve
toward what the judge prefers. The critic's paired (weakness → remedy) outputs are
exactly this preference signal.

## Dangerous-capability evals and responsible scaling

Frontier labs gate deployment on **dangerous-capability evaluations** and
if-then **responsible scaling policies** — safeguards tied to measured capability.
For AI-security research this sets the ethics bar: offensive capability must be
measured, disclosed responsibly, and paired with a defense proportionate to the
risk. A paper that demonstrates an attack without this framing is not publishable
at a top venue.
