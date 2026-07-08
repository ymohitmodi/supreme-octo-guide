"""Thoroughness reviewer — does this paper meet a world-leading conference bar?

The novelty bar-raiser (``novelty.py``) decides whether the *idea* is new enough;
this reviewer decides whether the *paper* is thorough enough to survive a program
committee. It checks the properties top venues (S&P, USENIX, CCS, NeurIPS) reward
and reviewers reject for missing: a precise threat model, a baseline comparison,
quantitative results, an ablation / trade-off, grounded related work,
reproducibility, a limitations discussion, and an ethics / disclosure statement.

Offline it inspects the generated manuscript + experiment structurally (real
properties our experiments genuinely have — multiple conditions, a defended vs
undefended baseline, a reported trade-off). Live, an LLM program-committee
reviewer refines the borderline judgment. A paper is accepted only if it clears
this bar in addition to the novelty bar and the integrity gate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .experiments import ExperimentResult
from .ideas import Idea

# Criteria and whether each is *critical* (a critical miss fails the review
# outright; non-critical misses lower the score).
_CRITERIA = (
    ("threat_model", True),
    ("baseline_comparison", True),
    ("quantitative_results", True),
    ("reproducibility", True),
    ("ablation_or_tradeoff", False),
    ("related_work", False),
    ("limitations", False),
    ("ethics", False),
)
PASS_FRACTION = 0.85


@dataclass
class ReviewReport:
    criteria: dict = field(default_factory=dict)   # name -> bool
    score: float = 0.0
    meets_bar: bool = False
    recommendation: str = "reject"
    notes: str = ""

    def failed(self) -> list[str]:
        return [k for k, ok in self.criteria.items() if not ok]


def _check(tex: str, exp: ExperimentResult, idea: Idea, n_citations: int) -> dict:
    low = tex.lower()
    n_rows = len(exp.table_rows)
    finding = exp.finding.lower()
    return {
        "threat_model": ("\\section{threat model}" in low
                         and bool(re.search(r"knowledge|capabilit|budget|adversary", low))),
        # A comparison exists when the experiment has ≥2 conditions (rows) — e.g.
        # defended vs undefended, in-distribution vs adaptive, sizes.
        "baseline_comparison": n_rows >= 2,
        "quantitative_results": bool(exp.table_rows) and any(
            re.search(r"\d", c) for row in exp.table_rows for c in row[1:]),
        "reproducibility": bool(re.search(r"seed", low) and re.search(r"reproduc|released? code|"
                                                                      r"benchmark specification", low)),
        "ablation_or_tradeoff": (n_rows >= 3
                                 or bool(re.search(r"trade-?off|gap|vs\.?|versus|collapse", finding))),
        "related_work": ("\\section{related work}" in low and n_citations >= 1),
        "limitations": "limitations" in low,
        "ethics": bool(re.search(r"ethic|responsible disclosure|coordinated disclosure", low)),
    }


def review_offline(idea: Idea, exp: ExperimentResult, tex: str, n_citations: int) -> ReviewReport:
    criteria = _check(tex, exp, idea, n_citations)
    passed = sum(1 for v in criteria.values() if v)
    score = round(passed / len(criteria), 4)
    critical_ok = all(criteria[name] for name, crit in _CRITERIA if crit)
    meets = critical_ok and score >= PASS_FRACTION
    rec = "accept" if meets else ("major-revision" if critical_ok else "reject")
    notes = "clears the conference bar" if meets else (
        "missing: " + ", ".join(k for k, ok in criteria.items() if not ok))
    return ReviewReport(criteria=criteria, score=score, meets_bar=meets,
                        recommendation=rec, notes=notes)


def review_live(idea: Idea, exp: ExperimentResult, tex: str, n_citations: int, ctx) -> ReviewReport:
    """LLM program-committee reviewer; falls back to the structural review."""
    base = review_offline(idea, exp, tex, n_citations)
    from nyx.providers.base import ChatMessage
    prompt = (
        "You are a program-committee reviewer at a top AI-security venue. Judge whether "
        "this paper is THOROUGH enough to accept. For each criterion answer yes/no: "
        "threat_model, baseline_comparison, quantitative_results, reproducibility, "
        "ablation_or_tradeoff, related_work, limitations, ethics.\n\n"
        f"TITLE: {idea.title}\nCONTRIBUTION: {idea.contribution}\n"
        f"EXPERIMENT: {exp.method}; result: {exp.finding}\n"
        f"PAPER (truncated):\n{tex[:3500]}\n\n"
        "Reply JSON ONLY: {\"criteria\":{name:true/false,...},\"recommendation\":"
        "\"accept|major-revision|reject\",\"notes\":\"one sentence\"}."
    )
    try:
        out = ctx.provider.chat(ctx.config.model("reviewer"),
                                [ChatMessage(role="user", content=prompt)],
                                temperature=0.0, max_tokens=700).text
        from .ideas import _extract_json_object
        obj = _extract_json_object(out)
        if obj and isinstance(obj.get("criteria"), dict):
            criteria = {name: bool(obj["criteria"].get(name, base.criteria.get(name, False)))
                        for name, _ in _CRITERIA}
            passed = sum(1 for v in criteria.values() if v)
            score = round(passed / len(criteria), 4)
            critical_ok = all(criteria[name] for name, crit in _CRITERIA if crit)
            meets = critical_ok and score >= PASS_FRACTION
            return ReviewReport(criteria=criteria, score=score, meets_bar=meets,
                                recommendation=str(obj.get("recommendation", "reject")),
                                notes=str(obj.get("notes", ""))[:200])
    except Exception:  # noqa: BLE001 — the reviewer must never crash a run
        pass
    return base


def review(idea: Idea, exp: ExperimentResult, tex: str, n_citations: int, ctx=None) -> ReviewReport:
    if ctx is not None and getattr(ctx, "provider", None) is not None \
            and not getattr(ctx.config, "mock_mode", True):
        return review_live(idea, exp, tex, n_citations, ctx)
    return review_offline(idea, exp, tex, n_citations)
