"""The bar-raiser — score an idea against the public prior art of its venue.

This is the assessor the user asked for: it validates every mined idea against
existing conference publications before a single word of the paper is written,
and it is *strict* — an idea a reviewer can name a close paper for does not clear
the bar. It also estimates impact, feasibility, and rigor so the factory can rank
and iterate.

Two engines, same contract:
- **Offline / deterministic**: TF-IDF-ish cosine over the curated + ingested
  corpus gives a reproducible novelty signal (1 − max similarity to prior art),
  plus heuristic impact/feasibility/rigor from the idea's structure.
- **Live**: an LLM judge reads the idea and the nearest prior art and rates each
  dimension, naming the closest papers — the semantic bar-raiser.

The threshold is deliberately high: novelty ≥ 0.62 and fitness ≥ 0.60 to *pass*.
Selection is where quality is enforced; generation is cheap.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .ideas import Idea
from .ingest import Paper

NOVELTY_BAR = 0.62
FITNESS_BAR = 0.60

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "the a an of for to and or in on with under against via using use based is are "
    "we our that this these those it its from by as at be can new novel approach "
    "method model models attack attacks defense defenses paper study propose".split()
)


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 2]


def _tf(text: str) -> Counter:
    toks = _tokens(text)
    return Counter(toks)


def _idf(corpus_tokens: list[list[str]]) -> dict[str, float]:
    n = len(corpus_tokens) or 1
    df: Counter = Counter()
    for toks in corpus_tokens:
        df.update(set(toks))
    return {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}


def _tfidf_vec(tf: Counter, idf: dict[str, float]) -> dict[str, float]:
    return {t: c * idf.get(t, math.log(2.0)) for t, c in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


@dataclass
class NoveltyReport:
    idea_id: str
    novelty: float
    impact: float
    feasibility: float
    rigor: float
    nearest: list[tuple[str, float]] = field(default_factory=list)  # (title, similarity)
    verdict: str = "reject"           # "pass" | "revise" | "reject"
    rationale: str = ""

    @property
    def passes(self) -> bool:
        return self.verdict == "pass"


# ---------------------------------------------------------------------------
# Heuristic impact / feasibility / rigor from idea structure (offline signal).
# These reward the traits venues actually reward: a clear threat model, an
# adaptive/certified evaluation, and a defense-forward, reproducible framing.
# ---------------------------------------------------------------------------
_IMPACT_CUES = ("certif", "provable", "bound", "cost", "first", "adaptive",
                "deploy", "real-world", "benchmark", "orders of magnitude")
_RIGOR_CUES = ("adaptive", "certif", "held-out", "contamination", "false-positive",
               "clean/robust", "trade-off", "unseen", "out-of-distribution", "budget")
_FEASIBLE_CUES = ("benchmark", "detector", "train", "measure", "implement",
                  "evaluate", "instrument", "protocol")


def _cue_score(text: str, cues) -> float:
    low = text.lower()
    hits = sum(1 for c in cues if c in low)
    return min(1.0, 0.35 + 0.16 * hits)


def _heuristic_dims(idea: Idea) -> tuple[float, float, float]:
    blob = f"{idea.title} {idea.hypothesis} {idea.approach} {idea.contribution}"
    impact = round(_cue_score(blob, _IMPACT_CUES), 3)
    rigor = round(_cue_score(blob, _RIGOR_CUES), 3)
    feasibility = round(_cue_score(blob, _FEASIBLE_CUES), 3)
    return impact, feasibility, rigor


def assess_offline(idea: Idea, corpus: list[Paper], bar: float = NOVELTY_BAR) -> NoveltyReport:
    idea_text = f"{idea.title}. {idea.hypothesis} {idea.approach} {idea.contribution}"
    docs = [p.text for p in corpus] + [idea_text]
    corpus_tokens = [_tokens(d) for d in docs]
    idf = _idf(corpus_tokens)
    idea_vec = _tfidf_vec(_tf(idea_text), idf)
    sims: list[tuple[str, float]] = []
    for p in corpus:
        s = _cosine(idea_vec, _tfidf_vec(_tf(p.text), idf))
        sims.append((p.title, round(s, 4)))
    sims.sort(key=lambda x: x[1], reverse=True)
    max_sim = sims[0][1] if sims else 0.0
    novelty = round(max(0.0, 1.0 - max_sim), 4)
    impact, feasibility, rigor = _heuristic_dims(idea)
    report = NoveltyReport(
        idea_id=idea.id, novelty=novelty, impact=impact,
        feasibility=feasibility, rigor=rigor, nearest=sims[:5],
    )
    _finalize(report, idea, bar)
    return report


def assess_live(idea: Idea, corpus: list[Paper], ctx, bar: float = NOVELTY_BAR) -> NoveltyReport:
    """LLM bar-raiser. Falls back to the deterministic assessor on any failure."""
    from nyx.providers.base import ChatMessage

    # Seed the judge with the offline nearest-neighbors so it reasons about the
    # genuinely closest prior art rather than hallucinating comparisons.
    base = assess_offline(idea, corpus, bar)
    prior = "\n".join(f"- {t} (sim {s})" for t, s in base.nearest) or "(none)"
    prompt = (
        "You are a bar-raising program-committee reviewer for a top AI-security venue. "
        "Rate this idea on four axes from 0.0 to 1.0.\n\n"
        f"IDEA: {idea.title}\nHYPOTHESIS: {idea.hypothesis}\nAPPROACH: {idea.approach}\n"
        f"CLAIMED CONTRIBUTION: {idea.contribution}\n\n"
        f"NEAREST PRIOR ART:\n{prior}\n\n"
        "novelty = how much it goes beyond the prior art; impact = importance if true; "
        "feasibility = can it be built+measured with modest compute; rigor = does the "
        "framing demand adaptive/certified, contamination-controlled evaluation.\n"
        "Reply as JSON ONLY: {\"novelty\":..,\"impact\":..,\"feasibility\":..,\"rigor\":..,"
        "\"nearest\":[\"title\",..],\"rationale\":\"one sentence\"}."
    )
    try:
        out = ctx.provider.chat(ctx.config.model("reviewer"),
                                [ChatMessage(role="user", content=prompt)],
                                temperature=0.0, max_tokens=600).text
        from .ideas import _extract_json_object
        obj = _extract_json_object(out)
        if obj:
            def g(k, d):
                try:
                    return max(0.0, min(1.0, float(obj.get(k, d))))
                except (TypeError, ValueError):
                    return d
            report = NoveltyReport(
                idea_id=idea.id,
                novelty=round(g("novelty", base.novelty), 4),
                impact=round(g("impact", base.impact), 4),
                feasibility=round(g("feasibility", base.feasibility), 4),
                rigor=round(g("rigor", base.rigor), 4),
                nearest=base.nearest,
                rationale=str(obj.get("rationale", ""))[:200],
            )
            _finalize(report, idea, bar)
            return report
    except Exception:  # noqa: BLE001 — the bar-raiser must never crash a run
        pass
    return base


def _finalize(report: NoveltyReport, idea: Idea, bar: float = NOVELTY_BAR) -> None:
    """Write scores back onto the idea and set the verdict against the (dynamic) bar.

    ``bar`` defaults to the base novelty bar but rises over time via the
    compounding ledger's ratchet, so later cycles must be more novel to pass."""
    idea.novelty = report.novelty
    idea.impact = report.impact
    idea.feasibility = report.feasibility
    idea.rigor = report.rigor
    idea.nearest_prior = [t for t, _ in report.nearest]
    if report.novelty >= bar and idea.fitness >= FITNESS_BAR:
        report.verdict = "pass"
    elif report.novelty >= max(0.45, bar - 0.17) and idea.fitness >= 0.5:
        report.verdict = "revise"
    else:
        report.verdict = "reject"
    if not report.rationale:
        closest = report.nearest[0][0] if report.nearest else "no close prior art"
        report.rationale = (
            f"novelty {report.novelty:.2f} (closest: {closest}); "
            f"fitness {idea.fitness:.2f} → {report.verdict}"
        )


def assess(idea: Idea, corpus: list[Paper], ctx=None, bar: float = NOVELTY_BAR) -> NoveltyReport:
    """Bar-raise an idea against a novelty ``bar`` (live LLM judge when available)."""
    if ctx is not None and getattr(ctx, "provider", None) is not None \
            and not getattr(ctx.config, "mock_mode", True):
        return assess_live(idea, corpus, ctx, bar)
    return assess_offline(idea, corpus, bar)
