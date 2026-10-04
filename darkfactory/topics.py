"""The AI-security research taxonomy the dark factory mines around the clock.

Each :class:`Topic` is a live research frontier with the *primitives* the idea
miner recombines (threat models, methods, assets) and a short doctrine the
factory seeds into NYX's long-term memory once, so every cycle recalls the state
of the art rather than re-deriving it. Coverage spans the modern AI-security
surface: adversarial ML, LLM/agentic security, privacy, alignment/evaluation,
data & supply-chain integrity, and defensive tooling.

Nothing here is offensive tradecraft — these are the *research questions* venues
like IEEE S&P, USENIX Security, NDSS, CCS, and IEEE SaTML publish on, framed for
defensive and scientific contribution with responsible disclosure assumed.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Topic:
    slug: str
    name: str
    summary: str
    threat_models: tuple[str, ...]
    methods: tuple[str, ...]
    assets: tuple[str, ...]
    doctrine: tuple[str, ...]          # durable lessons seeded into memory
    keywords: tuple[str, ...] = field(default_factory=tuple)


TOPICS: tuple[Topic, ...] = (
    Topic(
        slug="prompt-injection",
        name="Prompt Injection & Indirect Prompt Injection",
        summary=(
            "Untrusted content that reaches an LLM's context can override the "
            "developer's instructions. Indirect injection hides the payload in "
            "retrieved documents, tool outputs, or web pages the agent reads."
        ),
        threat_models=("direct injection", "indirect/retrieved injection",
                       "cross-tool contamination", "multi-agent relay"),
        methods=("instruction-hierarchy training", "content provenance tags",
                 "classifier guards", "spotlighting / delimiting", "taint tracking"),
        assets=("system prompt integrity", "tool-call authorization", "data exfiltration"),
        doctrine=(
            "Treat every tool output and retrieved document as untrusted data, never "
            "as instructions; enforce an instruction hierarchy end to end.",
            "Measure indirect injection with a held-out corpus of *unseen* payloads; "
            "in-distribution detection rates overstate real robustness.",
        ),
        keywords=("prompt injection", "indirect injection", "jailbreak of tools", "agent hijack"),
    ),
    Topic(
        slug="jailbreak-robustness",
        name="Jailbreak & Refusal Robustness",
        summary=(
            "Adversarial prompts that elicit disallowed behavior from aligned models. "
            "Research studies attack transferability and defenses that hold under "
            "adaptive, white-box adversaries rather than fixed test sets."
        ),
        threat_models=("adaptive adversary", "transfer attack", "many-shot context",
                       "encoding / obfuscation"),
        methods=("adversarial training", "circuit-level refusal analysis",
                 "input/output classifiers", "representation engineering"),
        assets=("policy compliance", "harm-refusal reliability"),
        doctrine=(
            "Only adaptive-attack evaluation is credible; report attack success under "
            "an adversary that knows the defense (Tramèr et al.'s obfuscated-gradients lesson).",
            "Robustness claims need a compute-matched attack budget, not a single template.",
        ),
        keywords=("jailbreak", "refusal", "adversarial prompt", "alignment robustness"),
    ),
    Topic(
        slug="adversarial-examples",
        name="Adversarial Examples & Certified Robustness",
        summary=(
            "Small, often imperceptible perturbations that flip model predictions, and "
            "the certified / provable defenses that bound the worst case."
        ),
        threat_models=("Lp-bounded evasion", "patch attacks", "semantic perturbation"),
        methods=("adversarial training", "randomized smoothing", "Lipschitz bounds",
                 "interval-bound propagation"),
        assets=("classifier integrity", "perception-stack safety"),
        doctrine=(
            "Empirical robustness without a certificate is a lower bound that adaptive "
            "attacks routinely break; prefer certified radii where feasible.",
            "Always report the clean/robust accuracy trade-off, not robust accuracy alone.",
        ),
        keywords=("adversarial example", "certified robustness", "randomized smoothing", "evasion"),
    ),
    Topic(
        slug="data-poisoning",
        name="Training-Data Poisoning & Backdoors",
        summary=(
            "Corrupting training or fine-tuning data to implant backdoors or degrade "
            "models, and detection / cleansing / provenance defenses."
        ),
        threat_models=("label flipping", "clean-label backdoor", "trigger injection",
                       "web-scale poisoning"),
        methods=("spectral signatures", "activation clustering", "data provenance",
                 "influence functions", "differential testing"),
        assets=("model integrity", "supply-chain trust"),
        doctrine=(
            "A realistic poisoning budget is a *tiny* fraction of the corpus; defenses "
            "must hold at <1% poison rate to matter.",
            "Backdoor detection that assumes the trigger is known is circular — evaluate "
            "against unknown triggers.",
        ),
        keywords=("data poisoning", "backdoor", "trojan", "clean-label"),
    ),
    Topic(
        slug="membership-inference",
        name="Membership Inference & Training-Data Extraction",
        summary=(
            "Attacks that decide whether a record was in the training set, or extract "
            "memorized data verbatim, and the privacy defenses (DP, dedup) that bound them."
        ),
        threat_models=("shadow-model attack", "loss-threshold attack", "extraction via prompting"),
        methods=("differential privacy (DP-SGD)", "deduplication", "per-example influence",
                 "calibrated LiRA evaluation"),
        assets=("training-data confidentiality", "regulatory compliance"),
        doctrine=(
            "Report membership inference with the LiRA-style TPR-at-low-FPR metric, not "
            "average accuracy, which hides the privacy leak on the tail.",
            "Deduplication reduces memorization more cheaply than DP for many corpora — "
            "quantify both.",
        ),
        keywords=("membership inference", "memorization", "data extraction", "differential privacy"),
    ),
    Topic(
        slug="model-extraction",
        name="Model Extraction & Stealing",
        summary=(
            "Reconstructing a black-box model's parameters or behavior through queries, "
            "and defenses like watermarking, query auditing, and output perturbation."
        ),
        threat_models=("query-based distillation", "side-channel leakage", "logit stealing"),
        methods=("watermarking", "query-pattern detection", "output rounding", "rate design"),
        assets=("model IP", "API confidentiality"),
        doctrine=(
            "Extraction cost, not mere feasibility, is the defense metric: raise queries-"
            "to-fidelity, don't claim prevention.",
            "Watermarks must survive distillation and fine-tuning to be meaningful.",
        ),
        keywords=("model extraction", "model stealing", "watermarking", "distillation attack"),
    ),
    Topic(
        slug="agentic-security",
        name="Agentic & Tool-Use Security",
        summary=(
            "Security of autonomous LLM agents that plan, call tools, and act — "
            "least privilege, human-in-the-loop gating, and containment of compromised steps."
        ),
        threat_models=("tool misuse", "confused-deputy", "goal hijack", "memory poisoning"),
        methods=("capability-scoped tools", "action gating", "provenance-aware memory",
                 "sandboxed execution", "egress control"),
        assets=("action authorization", "long-horizon goal integrity"),
        doctrine=(
            "Give each agent the least-privilege tool set; a confused-deputy attack turns "
            "over-broad credentials into an exploit.",
            "Untrusted memories must be capped and never promote to governing doctrine "
            "(memory-poisoning containment).",
        ),
        keywords=("agent security", "tool use", "autonomous agent", "confused deputy"),
    ),
    Topic(
        slug="rag-security",
        name="RAG & Retrieval-Layer Security",
        summary=(
            "Integrity and confidentiality of retrieval-augmented generation: poisoned "
            "corpora, retrieval manipulation, and context-provenance defenses."
        ),
        threat_models=("corpus poisoning", "retrieval ranking manipulation", "context leakage"),
        methods=("provenance tagging", "retrieval-time filtering", "source authentication",
                 "consistency cross-checking"),
        assets=("answer integrity", "source confidentiality"),
        doctrine=(
            "A single poisoned passage in the top-k can dominate the answer; defenses must "
            "assume the retriever *will* surface adversarial content.",
            "Attribute every generated claim to a retrieved, authenticated source.",
        ),
        keywords=("rag security", "retrieval poisoning", "corpus poisoning", "grounding"),
    ),
    Topic(
        slug="safety-evaluation",
        name="Safety Evaluation & Benchmark Integrity",
        summary=(
            "The science of measuring model safety: contamination-controlled benchmarks, "
            "adaptive red-teaming, and metrics that don't overstate robustness."
        ),
        threat_models=("benchmark contamination", "gaming / overfitting", "metric misuse"),
        methods=("held-out suites", "adaptive evaluation", "human-in-the-loop rubric",
                 "statistical power analysis"),
        assets=("evaluation validity", "reproducibility"),
        doctrine=(
            "Contamination control is a first-class result: state exactly how the held-out "
            "set is disjoint from anything the model could have trained on.",
            "Report confidence intervals; single-number leaderboards hide noise larger "
            "than the claimed gains.",
        ),
        keywords=("safety evaluation", "red teaming", "benchmark", "contamination"),
    ),
    Topic(
        slug="watermarking-provenance",
        name="Content Provenance & Watermarking",
        summary=(
            "Detecting machine-generated content and authenticating provenance under "
            "paraphrase, translation, and adversarial editing."
        ),
        threat_models=("paraphrase removal", "spoofing", "scrubbing"),
        methods=("statistical watermarking", "cryptographic signing (C2PA)",
                 "retrieval-based detection"),
        assets=("content authenticity", "attribution"),
        doctrine=(
            "A watermark is only as strong as its survival under paraphrase and its "
            "false-positive rate on human text — report both.",
            "Detection and provenance are different guarantees; don't conflate them.",
        ),
        keywords=("watermark", "provenance", "ai-generated detection", "c2pa"),
    ),
)

TOPICS_BY_SLUG = {t.slug: t for t in TOPICS}


def topic_for(text: str) -> Topic | None:
    """Best-match topic for a free-text objective (keyword overlap)."""
    low = text.lower()
    best, best_hits = None, 0
    for t in TOPICS:
        hits = sum(1 for kw in (t.keywords + (t.slug.replace("-", " "),)) if kw in low)
        if hits > best_hits:
            best, best_hits = t, hits
    return best


def seed_doctrine(memory) -> int:
    """Seed durable AI-security research doctrine into long-term memory once.

    Returns the number of principles written. Idempotent — NYX's MemoryStore
    reinforces rather than duplicates on re-seed.
    """
    n = 0
    for t in TOPICS:
        for principle in t.doctrine:
            memory.remember(
                principle,
                kind="principle",
                tags=["ai-security", t.slug, "research-doctrine"],
                source="darkfactory.topics",
                weight=1.5,
            )
            n += 1
    # Cross-cutting research-integrity doctrine.
    for principle in (
        "Novelty is measured against the *public* prior art of the target venue; an "
        "idea that a reviewer can name a close paper for is not yet a contribution.",
        "Every empirical claim in a paper must be reproducible from released code, a "
        "fixed seed, and the exact benchmark spec — no unsupported numbers.",
        "For any offensive result, lead with the defense and follow responsible "
        "disclosure; contributions must raise the security of the ecosystem.",
    ):
        memory.remember(principle, kind="principle",
                        tags=["ai-security", "research-integrity"],
                        source="darkfactory.topics", weight=2.0)
        n += 1
    return n
