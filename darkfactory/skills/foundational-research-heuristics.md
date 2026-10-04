# Foundational-Research Heuristics — finding unique, high-impact AI-security directions

How the factory finds directions that are *unique, foundational, and impactful* —
the kind that open a research program rather than close a gap. Novelty alone is
cheap; foundational novelty compounds. Use these heuristics when mining and when the
critic asks "is this a point result or a foundation?"

## Foundational beats incremental — the four generative moves

Most high-impact AI-security papers come from one of four moves. **(1) Name a new
threat model** the field couldn't see before (indirect prompt injection made a whole
class of app compromises legible). **(2) Break an evaluation everyone trusted** —
show that a standard method overstates robustness under adaptive attack, and give the
correct methodology. **(3) Certify what was only empirical** — turn a heuristic
defense into a provable guarantee (randomized smoothing). **(4) Build the reusable
substrate** — a benchmark, metric, or framework others must cite to work in the area
(HarmBench, LiRA). When mining, deliberately aim a candidate at one of these moves;
a candidate that fits none is probably incremental.

## Uniqueness test: the one-sentence delta

A direction is unique only if you can state, in one sentence, the thing it does that
the *nearest* prior work cannot — and design an experiment that isolates exactly
that. If the delta needs a paragraph of hedging, it's thin. Run the "reviewer can
name a close paper" test against the ingested prior art: if the nearest neighbor is
too close, either sharpen the delta or pivot the threat model. The novelty
bar-raiser makes this quantitative, but the sentence must exist first.

## Impact test: the "so what, if true" chain

Trace the consequence. If the result holds, what changes — who builds differently,
what gets measured differently, what attack becomes cheap or what defense becomes
deployable? A direction whose best case is "a slightly better number on a toy set"
has low impact regardless of novelty. Prefer directions where success shifts a
*curve* (attacker cost, clean/robust trade-off, privacy leakage vs data scale)
rather than a single point, because a curve invites the next paper.

## Compounding: design a program, not a paper

Foundational directions admit a *sequence*: a first result, then a tighter bound,
then generalization to new threat models, then detection→prevention. When choosing a
direction, prefer one where the obvious next three papers are visible — that is what
lets the factory build one step at a time and have each contribution stand on the
last. A direction with no visible sequel is a dead end even if the first paper lands.
Record each shipped result as the platform for the next.

## Avoiding the false-novelty traps

Reject directions that *feel* new but aren't foundational: re-running a known attack
on a new dataset; a marginal architecture tweak with no threat-model change; a
defense evaluated only against the attack it was designed to stop; a benchmark that
duplicates an existing one. These pass a shallow novelty check but a reviewer will
recognize them instantly. The critic should flag "not foundational" whenever the
contribution lacks a reusable artifact or a stated principle — and the remedy is to
add one, not to reword the claim.
