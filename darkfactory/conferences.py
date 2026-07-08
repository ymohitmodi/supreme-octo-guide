"""Target venues for AI-security research, with scope and cadence.

The factory *targets* a venue when it mines an idea: it aligns the framing,
baselines, and evaluation rigor to what that community publishes, and uses the
venue's public prior art as the novelty bar. Deadlines are approximate cadences
(they shift year to year) used only to prioritize the backlog, never asserted as
fact in a paper.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Venue:
    slug: str
    name: str
    tier: str                 # "top" | "specialized" | "workshop" | "oss"
    scope: str
    cadence: str              # human-readable cadence hint
    emphasis: tuple[str, ...]  # what reviewers reward


VENUES: tuple[Venue, ...] = (
    Venue("sp", "IEEE Symposium on Security and Privacy (S&P / Oakland)", "top",
          "Systems and ML security with rigorous, adaptive evaluation.",
          "quarterly rolling deadlines",
          ("adaptive adversary", "systems realism", "measurement rigor")),
    Venue("usenix-sec", "USENIX Security Symposium", "top",
          "Practical security; strong artifact evaluation culture.",
          "multiple deadline cycles per year",
          ("reproducible artifacts", "real-world threat models", "measurement")),
    Venue("ndss", "Network and Distributed System Security (NDSS)", "top",
          "Network, systems, and ML security.",
          "summer deadline",
          ("clear threat model", "end-to-end evaluation")),
    Venue("ccs", "ACM Conference on Computer and Communications Security (CCS)", "top",
          "Broad computer security incl. ML privacy and integrity.",
          "spring/summer deadlines",
          ("formalism", "attack+defense completeness")),
    Venue("satml", "IEEE Conference on Secure and Trustworthy ML (SaTML)", "specialized",
          "Security, privacy, and trustworthiness of ML — the natural home for this work.",
          "autumn deadline",
          ("threat-model clarity", "adaptive evaluation", "reproducibility")),
    Venue("neurips-datasets", "NeurIPS Datasets & Benchmarks", "specialized",
          "New benchmarks and evaluation methodology.",
          "summer deadline",
          ("benchmark novelty", "contamination control", "documentation")),
    Venue("icml", "ICML", "top",
          "ML methods incl. robustness, privacy, and alignment.",
          "winter deadline",
          ("theory + experiment", "strong baselines")),
    Venue("acl", "ACL / EMNLP (NLP security & safety tracks)", "specialized",
          "LLM safety, jailbreaks, watermarking, and evaluation.",
          "multiple deadlines per year",
          ("linguistic rigor", "human evaluation", "reproducibility")),
    Venue("ai-village", "DEF CON AI Village / arXiv preprint", "oss",
          "Fast-turnaround practitioner findings and open-source tooling.",
          "rolling",
          ("actionable defense", "open tooling", "responsible disclosure")),
)

VENUES_BY_SLUG = {v.slug: v for v in VENUES}
# Topic slug -> the venues that most naturally host that line of work.
TOPIC_VENUES: dict[str, tuple[str, ...]] = {
    "prompt-injection": ("satml", "usenix-sec", "acl"),
    "jailbreak-robustness": ("satml", "acl", "icml"),
    "adversarial-examples": ("icml", "satml", "sp"),
    "data-poisoning": ("sp", "ccs", "usenix-sec"),
    "membership-inference": ("ccs", "sp", "satml"),
    "model-extraction": ("usenix-sec", "ccs", "satml"),
    "agentic-security": ("satml", "usenix-sec", "ai-village"),
    "rag-security": ("satml", "acl", "ai-village"),
    "safety-evaluation": ("neurips-datasets", "satml", "icml"),
    "watermarking-provenance": ("sp", "icml", "acl"),
}


def venues_for_topic(topic_slug: str) -> list[Venue]:
    return [VENUES_BY_SLUG[s] for s in TOPIC_VENUES.get(topic_slug, ("satml",))]


def primary_venue(topic_slug: str) -> Venue:
    return venues_for_topic(topic_slug)[0]
