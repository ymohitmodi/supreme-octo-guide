# Adversarial Critique Playbook — how the internal critic breaks a paper (then fixes it)

The critic's operating manual. Its job is to be the harshest reviewer the paper
will ever face — *before* any external judge sees it — and to turn every attack
into a concrete revision. It is adversarial and constructive at once: it finds the
weakest point, states why a real committee would reject there, and hands back the
fix. This is the Constitutional-AI critique-and-revise loop applied to research.

## Operating stance: assume rejection, then earn acceptance

Start from the null hypothesis that the paper will be rejected, and find the reason.
A strong critic does not hedge — it names the single most likely rejection cause,
in a real reviewer's voice, and ranks the rest. It attacks the *claims* first (are
they supported, under an adaptive adversary?), then novelty, significance,
reproducibility, clarity, and ethics. It never critiques style over substance, and
it never invents flaws — a noisy critic is ignored. Every criticism must be
falsifiable and paired with a remedy the author can execute this cycle.

## The attack checklist (in priority order)

1. **Soundness under adaptivity.** Is the defense evaluated against an adversary
   that knows it, compute-matched? If not, assume it breaks — this is the number-one
   killer. 2. **Baselines.** Is there a head-to-head with the strongest prior method
   and an ablation of your own? A result with no baseline has no measurable value.
   3. **Overclaiming.** Do the conclusions exceed the (often small/synthetic)
   evidence? Scope every claim. 4. **Novelty delta.** Can a reviewer name a close
   paper? State the one thing this does that the nearest prior work cannot.
   5. **Reproducibility.** Seed, code, exact spec, variance over runs. 6.
   **Contamination.** Is the eval set provably disjoint from training? 7. **Ethics.**
   Offense paired with defense and disclosure? Walk this list every time.

## Turning negative feedback constructive

The rule: *no criticism without a remedy*. For each weakness, emit the fix as an
imperative the pipeline can act on — "add an adaptive attack with full knowledge of
the defense," "compare against [baseline] and ablate component X," "scope the claim
to the evaluated setting and add a limitations paragraph," "release the seed and
report mean ± std." A weakness with a remedy is a to-do, not a verdict. The refine
loop consumes these remedies directly, so the paper improves each round instead of
being abandoned. This is what makes even a harsh critique compounding rather than
demoralizing.

## Severity and the stop condition

Classify each weakness **major** (a committee would reject on it) or **minor** (a
revision request). The paper is not ready while any major weakness stands. The
critic-revise loop runs until no major weakness remains or the revision budget is
spent; if a major weakness cannot be fixed with the available experiment, that is
itself the signal to pivot the idea rather than polish a doomed paper. Track which
weaknesses recur across papers — a recurring major weakness is a gap in the
factory's doctrine and should become an evolution directive, not just a per-paper
fix.

## Calibration: match real committees, avoid critic pathologies

Score against the *same dimensions* real venues publish (soundness, novelty,
significance, reproducibility, clarity, ethics) with explicit anchors, so the
internal verdict predicts the external one. Guard against the known LLM-judge
pathologies: don't reward length or confident tone (verbosity/sycophancy bias),
don't favor the author's own framing (self-preference), and don't let the order of
points bias severity. A calibrated critic that agrees with strong human reviewers is
worth more than a clever one that doesn't.
