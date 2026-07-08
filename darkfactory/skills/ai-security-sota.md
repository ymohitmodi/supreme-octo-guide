# AI-Security State of the Art — the frontier a foundational paper must move

The operating knowledge for producing foundational AI-security research: what the
field currently knows, where the open problems are, and what separates an
incremental result from one that advances the state of the art. Pair this with the
frontier-model lifecycle skill (the systems under attack) and the reviewer rubric
(how the work is judged).

## The threat surface, by lifecycle stage

Security threads through every stage of the model lifecycle, and each stage has a
signature attack class. **Data**: poisoning and backdoors (clean-label triggers at
<1% poison rate; web-scale split-view poisoning is practical). **Training**:
privacy leakage — membership inference (measured as TPR at low FPR, not average
accuracy) and verbatim extraction of memorized data. **Model/IP**: extraction and
stealing via queries; watermarking as a provenance defense. **Inference/serving**:
adversarial examples (Lp-bounded and semantic), and for LLMs, jailbreaks and
direct/indirect prompt injection. **Agentic**: tool misuse, confused-deputy,
goal hijack, and memory poisoning in long-horizon agents. **Deploy**: content
provenance and machine-text detection under paraphrase. A foundational paper
usually reframes one of these, or connects two that were studied separately.

## What "foundational" means here

Incremental work moves a number on a fixed benchmark. Foundational work changes how
the community *thinks or measures*: a new threat model that was invisible before
(e.g. indirect prompt injection); a new evaluation methodology that exposes
over-claimed robustness (adaptive attacks; LiRA for membership inference); a
certified/provable guarantee where only empirical ones existed (randomized
smoothing); or a reusable benchmark/framework others build on (HarmBench). The test:
would a strong reviewer say "this changes how I will build or evaluate this class of
system," not "this is a better number." Aim there.

## The methodological bar (why most AI-security papers get rejected)

The field has learned, often the hard way, a set of non-negotiables. **Adaptive
evaluation**: a defense must be tested against an adversary that knows it and is
compute-matched — obfuscated-gradients showed most defenses break otherwise.
**Certified over empirical** where feasible: empirical robustness is a lower bound
adaptive attacks routinely break. **Right metric**: membership privacy is TPR@low-
FPR; robustness is the clean/robust trade-off, not robust accuracy alone; extraction
is attacker *cost*, not binary feasibility. **Contamination control**: state how
the eval set is disjoint from training. **Realistic budgets**: poisoning at a tiny
fraction; attacks with a stated query/compute budget. Internalizing these is the
difference between a submission and an acceptance.

## Open problems worth attacking (2025-era)

High-leverage directions where the field is unsettled and a contribution compounds:
robustness of LLM agents under indirect injection with *provenance-aware* defenses;
certified defenses that survive adaptive attacks at deployable false-positive rates;
membership/extraction risk in retrieval-augmented and fine-tuned models; watermark
robustness under paraphrase with bounded false positives on human text; poisoning of
web-scale and RAG corpora and cheap detection; cost-based defense metrics that shift
the attacker's curve rather than claiming prevention; and evaluation methodology that
resists contamination and gaming. Each admits a *sequence* of papers — a first
result, then tighter bounds, then generalization — which is how a research program
compounds.

## Responsible disclosure and dual-use, done right

AI-security research is dual-use by construction. The publishable stance is
defense-forward: demonstrate the attack only as far as needed to motivate and
evaluate a defense; disclose to affected vendors before publication; never target
live systems without authorization; and state the residual risk and who bears it.
This is not a compliance footnote — reviewers weigh it, and it is what makes the
contribution a net positive for the ecosystem.
