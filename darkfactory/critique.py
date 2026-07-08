"""The internal critic — an adversarial, constructive, bar-raising reviewer.

This runs *before* any external judge. It is the harshest reviewer the paper will
face: it assumes rejection, finds the strongest reason a real committee would
reject (calibrated to the public review dimensions and rejection archetypes in
``reviewer_corpus``), and — crucially — turns every criticism into a concrete
remedy the refine loop can execute. Negative feedback becomes a to-do list, not a
verdict. This is the Constitutional-AI critique-and-revise pattern applied to
research.

Offline it is deterministic: the archetype detectors fire on the paper bundle and
each firing lowers the dimension it hits. Live, an LLM critic equipped with the
factory's SOTA skill packs refines the judgment — but always seeded by the
deterministic pass so it reasons about real, detected weaknesses.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .experiments import ExperimentResult
from .ideas import Idea
from .reviewer_corpus import (
    DIMENSIONS,
    DIMENSIONS_BY_KEY,
    RejectionArchetype,
    detect_weaknesses,
)

ACCEPT_BAR = 0.72   # internal overall score to be "ready" for the external judge


@dataclass
class Weakness:
    archetype_id: str
    dimension: str
    severity: str            # "major" | "minor"
    reviewer_says: str
    remedy: str

    def is_major(self) -> bool:
        return self.severity == "major"


@dataclass
class CritiqueReport:
    dimension_scores: dict = field(default_factory=dict)   # key -> 0..1
    weaknesses: list = field(default_factory=list)          # list[Weakness]
    overall: float = 0.0
    verdict: str = "reject"                                  # reject | revise | accept
    headline: str = ""

    @property
    def major(self) -> list:
        return [w for w in self.weaknesses if w.is_major()]

    @property
    def remedies(self) -> list[str]:
        return [w.remedy for w in self.weaknesses]

    def summary(self) -> str:
        dims = " ".join(f"{k}={v:.2f}" for k, v in self.dimension_scores.items())
        lines = [f"internal critic: {self.verdict.upper()} overall={self.overall:.2f} "
                 f"({len(self.major)} major, {len(self.weaknesses)} total)",
                 f"  dimensions: {dims}"]
        for w in self.weaknesses:
            lines.append(f"  [{w.severity}] {w.dimension}: {w.reviewer_says}")
            lines.append(f"        ↳ fix: {w.remedy}")
        return "\n".join(lines)


def _bundle(idea: Idea, exp: ExperimentResult, tex: str) -> dict:
    return {
        "tex": tex, "finding": exp.finding, "n_rows": len(exp.table_rows),
        "n_citations": len(idea.nearest_prior[:6]), "novelty": idea.novelty,
        "title": idea.title, "contribution": idea.contribution,
    }


def _score_dimensions(idea: Idea, fired: list[RejectionArchetype]) -> dict:
    """Deterministic per-dimension scores: start high, penalize each fired archetype.

    Novelty and significance also fold in the idea's own novelty/impact so the
    internal judge tracks the external bar-raiser."""
    scores = {d.key: 0.85 for d in DIMENSIONS}
    for a in fired:
        penalty = 0.35 if a.severity == "major" else 0.15
        scores[a.dimension] = max(0.0, scores[a.dimension] - penalty)
    # Blend in idea-level signals where they apply.
    scores["novelty"] = round(0.5 * scores["novelty"] + 0.5 * idea.novelty, 4) if idea.novelty \
        else scores["novelty"]
    scores["significance"] = round(0.6 * scores["significance"] + 0.4 * idea.impact, 4) \
        if idea.impact else scores["significance"]
    return {k: round(v, 4) for k, v in scores.items()}


def _overall(scores: dict) -> float:
    return round(sum(DIMENSIONS_BY_KEY[k].weight * v for k, v in scores.items()), 4)


def critique_offline(idea: Idea, exp: ExperimentResult, tex: str) -> CritiqueReport:
    fired = detect_weaknesses(_bundle(idea, exp, tex))
    weaknesses = [Weakness(a.id, a.dimension, a.severity, a.reviewer_says, a.remedy)
                  for a in fired]
    scores = _score_dimensions(idea, fired)
    overall = _overall(scores)
    majors = [w for w in weaknesses if w.is_major()]
    if majors:
        verdict = "reject"            # a committee would reject; must revise internally
    elif overall >= ACCEPT_BAR and not weaknesses:
        verdict = "accept"
    else:
        verdict = "revise"
    if majors:
        headline = f"would be rejected: {majors[0].reviewer_says}"
    elif weaknesses:
        headline = f"revision needed: {weaknesses[0].reviewer_says}"
    else:
        headline = "no blocking weaknesses found; ready for external review"
    return CritiqueReport(dimension_scores=scores, weaknesses=weaknesses,
                          overall=overall, verdict=verdict, headline=headline)


def critique_live(idea: Idea, exp: ExperimentResult, tex: str, ctx) -> CritiqueReport:
    """LLM critic equipped with the factory's skill packs. Seeds on the offline pass
    so it reasons about really-detected weaknesses; falls back to it on any failure."""
    base = critique_offline(idea, exp, tex)
    from nyx.providers.base import ChatMessage

    # Recall the critique playbook + rubric from long-term memory when available.
    doctrine = ""
    mem = getattr(ctx, "memory", None)
    if mem is not None:
        try:
            lessons = mem.recall("adversarial critique reviewer rubric foundational", k=4)
            doctrine = "\n".join(f"- {getattr(l, 'text', str(l))[:240]}" for l in lessons)
        except Exception:  # noqa: BLE001
            doctrine = ""
    detected = "\n".join(f"- [{w.severity}] {w.dimension}: {w.reviewer_says}"
                         for w in base.weaknesses) or "- (none auto-detected)"
    prompt = (
        "You are the harshest, most constructive reviewer this AI-security paper will "
        "face, applying a top-venue rubric. Assume rejection and find the strongest "
        "reason; for EACH weakness give a concrete remedy the authors can execute.\n\n"
        f"RUBRIC + PLAYBOOK:\n{doctrine}\n\n"
        f"AUTO-DETECTED WEAKNESSES:\n{detected}\n\n"
        f"TITLE: {idea.title}\nCONTRIBUTION: {idea.contribution}\n"
        f"EXPERIMENT: {exp.method}; finding: {exp.finding}\nPAPER (truncated):\n{tex[:3000]}\n\n"
        "Reply JSON ONLY: {\"dimension_scores\":{soundness,novelty,significance,"
        "reproducibility,clarity,ethics: 0..1},\"weaknesses\":[{\"dimension\":..,"
        "\"severity\":\"major|minor\",\"reviewer_says\":..,\"remedy\":..}],"
        "\"headline\":\"one sentence\"}."
    )
    try:
        out = ctx.provider.chat(ctx.config.model("reviewer"),
                                [ChatMessage(role="user", content=prompt)],
                                temperature=0.2, max_tokens=1600).text
        from .ideas import _extract_json_object
        obj = _extract_json_object(out)
        if obj and isinstance(obj.get("dimension_scores"), dict):
            scores = {}
            for d in DIMENSIONS:
                try:
                    scores[d.key] = max(0.0, min(1.0, float(obj["dimension_scores"].get(
                        d.key, base.dimension_scores[d.key]))))
                except (TypeError, ValueError):
                    scores[d.key] = base.dimension_scores[d.key]
            weaknesses = []
            for w in obj.get("weaknesses", []) or []:
                if not isinstance(w, dict):
                    continue
                dim = str(w.get("dimension", "soundness"))
                weaknesses.append(Weakness(
                    archetype_id="llm", dimension=dim if dim in DIMENSIONS_BY_KEY else "soundness",
                    severity="major" if str(w.get("severity")) == "major" else "minor",
                    reviewer_says=str(w.get("reviewer_says", ""))[:240],
                    remedy=str(w.get("remedy", ""))[:240]))
            overall = _overall(scores)
            majors = [x for x in weaknesses if x.is_major()]
            verdict = "reject" if majors else ("accept" if overall >= ACCEPT_BAR and not weaknesses
                                               else "revise")
            return CritiqueReport(dimension_scores={k: round(v, 4) for k, v in scores.items()},
                                  weaknesses=weaknesses, overall=overall, verdict=verdict,
                                  headline=str(obj.get("headline", base.headline))[:200])
    except Exception:  # noqa: BLE001 — the critic must never crash a run
        pass
    return base


def critique(idea: Idea, exp: ExperimentResult, tex: str, ctx=None) -> CritiqueReport:
    """Adversarial + constructive internal critique (live LLM critic when available)."""
    if ctx is not None and getattr(ctx, "provider", None) is not None \
            and not getattr(ctx.config, "mock_mode", True):
        return critique_live(idea, exp, tex, ctx)
    return critique_offline(idea, exp, tex)
