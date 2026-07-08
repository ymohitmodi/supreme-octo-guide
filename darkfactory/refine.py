"""Feedback-driven internal refinement — improve before the external judge sees it.

The critique-and-revise loop: draft → internal critic attacks it → apply each
criticism's constructive remedy → re-draft → re-critique, until no major weakness
remains or the budget is spent. Only then does the paper go to the external judge
(novelty bar-raiser + conference reviewer). This is what makes even harsh, negative
feedback *compounding*: every weakness becomes a revision, so the paper that reaches
the external judge is already the strongest version the factory can produce.

Recurring weaknesses are also fed back to the factory's evolution (as directives)
and memory (as track record), so the doctrine learns to avoid them — the paper
improves this cycle, and the *researcher* improves across cycles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .critique import CritiqueReport, Weakness, critique
from .experiments import ExperimentResult
from .ideas import Idea, revise_idea
from .novelty import NOVELTY_BAR, assess
from .paper import build_latex
from .topics import Topic

MAX_REFINE_ROUNDS = 3

# Weaknesses the refiner can resolve by revising the idea itself (as opposed to
# structural ones the paper generator/experiment already handle). The loop keeps
# running while any of these remain, even if only "minor".
_ACTIONABLE = {"thin-novelty", "not-foundational", "overclaiming"}

# Map a rejection-archetype (or dimension) to a durable evolution directive, so a
# weakness that recurs across papers upgrades the researcher's doctrine.
_ARCHETYPE_DIRECTIVE = {
    "non-adaptive-eval": "Evaluate every defense against an adaptive adversary that knows it.",
    "weak-baselines": "Always compare head-to-head against the strongest baseline and ablate.",
    "single-seed": "Report mean ± std over multiple seeds and release code.",
    "unrealistic-threat-model": "State a precise threat model: adversary knowledge, capability, budget.",
    "overclaiming": "Scope every claim to the evaluated setting; add explicit limitations.",
    "thin-novelty": "Sharpen the one-sentence delta over the nearest prior work.",
    "no-ablation": "Include an ablation or a trend sweep that attributes the effect.",
    "contaminated-eval": "State how the eval set is disjoint from training (decontamination).",
    "offense-no-defense": "Lead offense with a defense and coordinated disclosure.",
    "not-foundational": "Ship a reusable artifact and state the principle it establishes.",
}

# A foundational clause the refiner grafts to answer a 'not-foundational' critique.
_FOUNDATIONAL_CLAUSE = (" We release a reusable benchmark and state the general "
                        "principle this establishes so the community can build on it.")


@dataclass
class RefineResult:
    idea: Idea
    report: object                        # final NoveltyReport for the refined idea
    tex: str
    initial: CritiqueReport
    final: CritiqueReport
    rounds: int = 0
    resolved: list[str] = field(default_factory=list)      # archetype ids resolved
    directives: list[str] = field(default_factory=list)    # for evolution
    lessons: list = field(default_factory=list)            # (text, kind, tags) for memory

    @property
    def improved(self) -> bool:
        return self.final.overall >= self.initial.overall

    def summary(self) -> str:
        return (f"refine: {self.rounds} round(s), overall "
                f"{self.initial.overall:.2f} → {self.final.overall:.2f}, "
                f"major {len(self.initial.major)} → {len(self.final.major)}"
                f"{'; resolved ' + ', '.join(self.resolved) if self.resolved else ''}")


def _apply_remedy(idea: Idea, w: Weakness, topic: Topic, corpus, ctx, bar: float):
    """Turn one criticism into a concrete revision of the idea. Returns (idea, report|None)."""
    aid = w.archetype_id
    if aid == "thin-novelty":
        revised = revise_idea(idea, w.remedy, topic, ctx)
        revised.nearest_prior = idea.nearest_prior
        rep = assess(revised, corpus, ctx, bar=bar)
        # Keep the revision only if it is actually more novel.
        if rep.novelty > idea.novelty:
            return revised, rep
        return idea, None
    if aid == "not-foundational":
        if "reusable" not in idea.contribution.lower():
            idea.contribution = idea.contribution.rstrip(".") + "." + _FOUNDATIONAL_CLAUSE
        return idea, None
    if aid == "overclaiming":
        for word in (" always ", " any model ", " completely ", " fully "):
            idea.contribution = idea.contribution.replace(word, " ")
        return idea, None
    # Structural remedies (threat model, baselines, ethics, seed, contamination,
    # ablation) are already satisfied by the paper generator and experiment design;
    # if a detector still fires, the loop records it for evolution rather than
    # silently ignoring it.
    return idea, None


def refine(idea: Idea, report, exp: ExperimentResult, corpus, topic: Topic,
           ctx=None, builds_on_titles=None, bar: float = NOVELTY_BAR,
           max_rounds: int = MAX_REFINE_ROUNDS) -> RefineResult:
    """Run the internal critique→revise loop and return the hardened paper draft."""
    tex = build_latex(idea, exp, report, corpus, builds_on_titles=builds_on_titles)
    initial = critique(idea, exp, tex, ctx)
    current = initial
    resolved: list[str] = []
    directives: set[str] = set()
    rounds = 0

    def _needs_work(crit: CritiqueReport) -> bool:
        return bool(crit.major) or any(w.archetype_id in _ACTIONABLE for w in crit.weaknesses)

    while _needs_work(current) and rounds < max_rounds:
        rounds += 1
        # Address every weakness we can act on this round (majors first).
        ordered = sorted(current.weaknesses, key=lambda w: 0 if w.is_major() else 1)
        for w in ordered:
            directive = _ARCHETYPE_DIRECTIVE.get(w.archetype_id)
            if directive:
                directives.add(directive)
            new_idea, new_report = _apply_remedy(idea, w, topic, corpus, ctx, bar)
            if new_idea is not idea or new_report is not None:
                idea = new_idea
                if new_report is not None:
                    report = new_report
        tex = build_latex(idea, exp, report, corpus, builds_on_titles=builds_on_titles)
        new_crit = critique(idea, exp, tex, ctx)
        # Record which archetypes we cleared this round.
        before = {w.archetype_id for w in current.weaknesses}
        after = {w.archetype_id for w in new_crit.weaknesses}
        resolved.extend(sorted(before - after))
        if new_crit.overall <= current.overall and len(new_crit.major) >= len(current.major):
            current = new_crit
            break     # no further progress; stop polishing a stuck draft
        current = new_crit

    # Feedback → evolution + memory: what recurred, what we learned.
    lessons = []
    for w in current.weaknesses:
        directives.add(_ARCHETYPE_DIRECTIVE.get(w.archetype_id, ""))
    directives.discard("")
    if resolved:
        lessons.append((
            f"CRITIQUE FEEDBACK — resolved {', '.join(sorted(set(resolved)))} on "
            f"'{idea.title[:50]}'; internal overall {initial.overall:.2f}→{current.overall:.2f}.",
            "track-record", ["ai-security", "critique", "refined", topic.slug]))
    if current.major:
        lessons.append((
            f"CRITIQUE GAP — unresolved {[w.archetype_id for w in current.major]} on "
            f"'{idea.title[:50]}'; doctrine should address this.",
            "risk", ["ai-security", "critique", "recurring-weakness", topic.slug]))

    return RefineResult(
        idea=idea, report=report, tex=tex, initial=initial, final=current,
        rounds=rounds, resolved=sorted(set(resolved)),
        directives=sorted(directives), lessons=lessons,
    )
