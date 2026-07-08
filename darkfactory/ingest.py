"""SOTA ingestion — keep reading the AI-security literature, 24/7.

Live, it queries the public arXiv API (cs.CR + cs.LG + cs.AI) for each topic and
digests abstracts through NYX's polite, cached web fetcher. Offline (or with no
network), it falls back to a curated corpus of landmark AI-security papers so the
novelty bar-raiser always has *real* prior art to compare against and the whole
pipeline is deterministic in CI.

Ingested abstracts are written to NYX memory as ``trusted=False`` (external
content never becomes governing doctrine — OWASP Agentic memory-poisoning
containment), and returned as a corpus the novelty assessor scores ideas against.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, field

from .topics import Topic

ARXIV_API = "http://export.arxiv.org/api/query"


@dataclass
class Paper:
    title: str
    abstract: str
    topic: str = ""
    source: str = "corpus"
    year: int = 0
    authors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def text(self) -> str:
        return f"{self.title}. {self.abstract}"


# ---------------------------------------------------------------------------
# Curated offline prior-art corpus: real, well-known AI-security papers. This is
# the deterministic novelty baseline; live arXiv ingestion augments it.
# ---------------------------------------------------------------------------
_CORPUS: tuple[Paper, ...] = (
    Paper("Intriguing properties of neural networks",
          "Neural networks are vulnerable to small adversarial perturbations that are "
          "imperceptible to humans yet cause confident misclassification.",
          "adversarial-examples", "corpus", 2014, ("Szegedy", "et al.")),
    Paper("Explaining and Harnessing Adversarial Examples",
          "Introduces the fast gradient sign method (FGSM) and argues adversarial "
          "examples arise from the linear nature of models in high dimensions.",
          "adversarial-examples", "corpus", 2015, ("Goodfellow", "et al.")),
    Paper("Towards Deep Learning Models Resistant to Adversarial Attacks",
          "Frames robustness as a min-max problem and proposes projected gradient "
          "descent (PGD) adversarial training as a strong empirical defense.",
          "adversarial-examples", "corpus", 2018, ("Madry", "et al.")),
    Paper("Certified Adversarial Robustness via Randomized Smoothing",
          "Turns any classifier into a certifiably robust one under an L2 ball by "
          "smoothing predictions with Gaussian noise and deriving a radius.",
          "adversarial-examples", "corpus", 2019, ("Cohen", "et al.")),
    Paper("Obfuscated Gradients Give a False Sense of Security",
          "Shows many defenses rely on gradient masking and break under adaptive "
          "attacks; establishes adaptive evaluation as the standard.",
          "safety-evaluation", "corpus", 2018, ("Athalye", "et al.")),
    Paper("Membership Inference Attacks Against Machine Learning Models",
          "Shadow-model attack that infers whether a record was in the training set "
          "of a black-box classifier.",
          "membership-inference", "corpus", 2017, ("Shokri", "et al.")),
    Paper("Membership Inference Attacks From First Principles",
          "The likelihood-ratio attack (LiRA); argues privacy leakage must be measured "
          "as true-positive rate at low false-positive rate.",
          "membership-inference", "corpus", 2022, ("Carlini", "et al.")),
    Paper("Extracting Training Data from Large Language Models",
          "Demonstrates verbatim memorization can be extracted from LLMs by prompting, "
          "with risk scaling in duplication and model size.",
          "membership-inference", "corpus", 2021, ("Carlini", "et al.")),
    Paper("Deep Learning with Differential Privacy",
          "DP-SGD: trains models with differential privacy by clipping per-example "
          "gradients and adding calibrated noise, with a moments accountant.",
          "membership-inference", "corpus", 2016, ("Abadi", "et al.")),
    Paper("BadNets: Identifying Vulnerabilities in the Machine Learning Supply Chain",
          "Backdoor attacks where a trigger implanted at training time causes targeted "
          "misclassification while clean accuracy is preserved.",
          "data-poisoning", "corpus", 2017, ("Gu", "et al.")),
    Paper("Spectral Signatures in Backdoor Attacks",
          "Detects poisoned examples via spectral signatures in learned representations.",
          "data-poisoning", "corpus", 2018, ("Tran", "et al.")),
    Paper("Poisoning Web-Scale Training Datasets is Practical",
          "Shows split-view and frontrunning poisoning of real web-scale corpora is "
          "feasible at low cost.",
          "data-poisoning", "corpus", 2023, ("Carlini", "et al.")),
    Paper("Stealing Machine Learning Models via Prediction APIs",
          "Query-based model extraction reconstructs black-box models through their "
          "prediction interface.",
          "model-extraction", "corpus", 2016, ("Tramèr", "et al.")),
    Paper("Universal and Transferable Adversarial Attacks on Aligned Language Models",
          "Gradient-based suffixes (GCG) jailbreak aligned LLMs and transfer across "
          "models, revealing shared vulnerability.",
          "jailbreak-robustness", "corpus", 2023, ("Zou", "et al.")),
    Paper("Jailbroken: How Does LLM Safety Training Fail?",
          "Attributes jailbreaks to competing objectives and mismatched generalization "
          "between capability and safety training.",
          "jailbreak-robustness", "corpus", 2023, ("Wei", "et al.")),
    Paper("Not what you've signed up for: Compromising Real-World LLM-Integrated "
          "Applications with Indirect Prompt Injection",
          "Introduces indirect prompt injection: adversarial instructions embedded in "
          "content the model retrieves compromise LLM-integrated apps.",
          "prompt-injection", "corpus", 2023, ("Greshake", "et al.")),
    Paper("Prompt Injection attack against LLM-integrated Applications",
          "Systematizes prompt-injection attacks against deployed LLM applications and "
          "their defenses.",
          "prompt-injection", "corpus", 2023, ("Liu", "et al.")),
    Paper("Poisoning Retrieval Corpora by Injecting Adversarial Passages",
          "A few adversarial passages inserted into a retrieval corpus are retrieved "
          "for many queries and corrupt RAG answers.",
          "rag-security", "corpus", 2023, ("Zhong", "et al.")),
    Paper("A Watermark for Large Language Models",
          "A statistical watermark biases token sampling into a detectable green-list "
          "signal without hurting quality.",
          "watermarking-provenance", "corpus", 2023, ("Kirchenbauer", "et al.")),
    Paper("On the Reliability of Watermarks for Large Language Models",
          "Evaluates watermark robustness under paraphrase and human editing, and the "
          "false-positive trade-off.",
          "watermarking-provenance", "corpus", 2023, ("Kirchenbauer", "et al.")),
    Paper("Identifying and Mitigating the Security Risks of Generative AI",
          "Surveys the security and safety risks of generative AI including agentic "
          "tool use, and open research problems.",
          "agentic-security", "corpus", 2023, ("Barrett", "et al.")),
    Paper("HarmBench: A Standardized Evaluation Framework for Automated Red Teaming",
          "A standardized, contamination-aware benchmark for red-teaming and refusal "
          "robustness across attacks and models.",
          "safety-evaluation", "corpus", 2024, ("Mazeika", "et al.")),
)

CORPUS_BY_TOPIC: dict[str, list[Paper]] = {}
for _p in _CORPUS:
    CORPUS_BY_TOPIC.setdefault(_p.topic, []).append(_p)


def corpus_for(topic_slug: str) -> list[Paper]:
    """The curated prior art for a topic (always available, offline-safe)."""
    return list(CORPUS_BY_TOPIC.get(topic_slug, []))


# ---------------------------------------------------------------------------
# Live arXiv ingestion (best-effort). Uses NYX's WebFetcher when a fetcher is
# supplied; parses the Atom feed with the stdlib. Any failure degrades silently
# to the curated corpus so the factory never blocks on the network.
# ---------------------------------------------------------------------------
_ENTRY_RE = re.compile(r"<entry>(.*?)</entry>", re.DOTALL)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
_SUMMARY_RE = re.compile(r"<summary>(.*?)</summary>", re.DOTALL)
_PUB_RE = re.compile(r"<published>(\d{4})")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_arxiv_atom(xml: str, topic_slug: str) -> list[Paper]:
    papers: list[Paper] = []
    for entry in _ENTRY_RE.findall(xml):
        t = _TITLE_RE.search(entry)
        s = _SUMMARY_RE.search(entry)
        y = _PUB_RE.search(entry)
        if not t or not s:
            continue
        papers.append(Paper(
            title=_clean(t.group(1)), abstract=_clean(s.group(1)),
            topic=topic_slug, source="arxiv", year=int(y.group(1)) if y else 0,
        ))
    return papers


def arxiv_query_url(topic: Topic, max_results: int = 12) -> str:
    terms = " OR ".join(f'"{kw}"' for kw in (topic.keywords or (topic.name,)))
    q = f"({terms}) AND (cat:cs.CR OR cat:cs.LG OR cat:cs.AI)"
    params = {
        "search_query": q,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(max_results),
    }
    return f"{ARXIV_API}?{urllib.parse.urlencode(params)}"


def fetch_arxiv(topic: Topic, fetcher=None, max_results: int = 12) -> list[Paper]:
    """Fetch recent arXiv papers for a topic; [] on any failure (caller falls back)."""
    if fetcher is None:
        return []
    try:
        doc = fetcher.fetch(arxiv_query_url(topic, max_results))
        body = getattr(doc, "raw", None) or getattr(doc, "text", "") or ""
        if getattr(doc, "status", 200) >= 400 or not body:
            return []
        return parse_arxiv_atom(body, topic.slug)
    except Exception:  # noqa: BLE001 — ingestion is best-effort, never fatal
        return []


@dataclass
class IngestResult:
    topic: str
    corpus: list[Paper]
    live: int = 0
    cached: int = 0

    def stats(self) -> dict:
        return {"topic": self.topic, "papers": len(self.corpus),
                "live": self.live, "curated": self.cached}


def ingest_topic(topic: Topic, fetcher=None, memory=None, max_results: int = 12) -> IngestResult:
    """Build the prior-art corpus for a topic: curated ∪ live arXiv (best-effort)."""
    curated = corpus_for(topic.slug)
    live = fetch_arxiv(topic, fetcher=fetcher, max_results=max_results)
    seen = {p.title.lower() for p in curated}
    merged = list(curated)
    for p in live:
        if p.title.lower() not in seen:
            merged.append(p)
            seen.add(p.title.lower())
    if memory is not None:
        for p in merged:
            memory.remember(
                f"PRIOR ART [{topic.slug}] {p.title} ({p.year or 'n/a'}): {p.abstract[:300]}",
                kind="research", tags=["ai-security", topic.slug, "prior-art", p.source],
                source=p.source, weight=1.0, trusted=False,
            )
    return IngestResult(topic=topic.slug, corpus=merged, live=len(live), cached=len(curated))


def to_json(papers: list[Paper]) -> str:
    return json.dumps([p.__dict__ for p in papers], indent=2, default=list)
