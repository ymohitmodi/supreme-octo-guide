"""Auto-evolve — recurring critique weaknesses trigger self-improvement.

The internal critic emits a constructive directive for every weakness it finds.
When a weakness *recurs* across papers, that is a gap in the researcher's doctrine,
not a per-paper fix — so on a schedule (every N papers) the factory folds the
accumulated critique directives into the evolution pool and runs a Darwin-Gödel
round, adopting the improved ``researcher`` genome if it scores higher. The
feedback provider thus drives the factory's self-improvement automatically.

Deterministic offline (NYX's engine runs on the mock brain against the
``ResearchBenchmark``), so the loop is exercised without a key.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .evolution import RESEARCH_DIRECTIVES, ResearchBenchmark


@dataclass
class EvolveEvent:
    at_paper: int
    directives_added: int
    score_before: float | None
    score_after: float | None
    admitted: int

    @property
    def gain(self) -> float:
        if self.score_before is None or self.score_after is None:
            return 0.0
        return round(self.score_after - self.score_before, 4)


@dataclass
class AutoEvolver:
    """Watches paper results, accumulates critique pressure, and evolves on schedule."""
    every: int = 4                       # evolve every N papers
    generations: int = 6
    directives: set = field(default_factory=set)
    weakness_counts: Counter = field(default_factory=Counter)
    events: list = field(default_factory=list)
    _seen: int = 0

    def observe(self, result) -> None:
        """Absorb one paper's critique feedback (directives + recurring weaknesses)."""
        self._seen += 1
        for d in getattr(result, "critique_directives", []) or []:
            self.directives.add(d)
        crit = getattr(result, "critique", None)
        if crit is not None:
            for w in crit.weaknesses:
                self.weakness_counts[w.archetype_id] += 1

    def recurring(self, min_count: int = 2) -> list[str]:
        """Weakness archetypes that have recurred — the doctrine gaps to close."""
        return [a for a, c in self.weakness_counts.most_common() if c >= min_count]

    def should_evolve(self) -> bool:
        # Fire on the schedule so the doctrine self-improves regularly; when the
        # critic has surfaced directives they enrich the pool, but even without new
        # ones an evolution round explores more genomes against the benchmark.
        return self._seen > 0 and self._seen % self.every == 0

    def evolve(self, config) -> EvolveEvent:
        """Run one evolution round with the base + critique-derived directive pool."""
        from nyx.evolution.engine import EvolutionEngine

        from . import gates, roles  # noqa: F401 — ensure researcher role registered
        pool = list(RESEARCH_DIRECTIVES) + sorted(self.directives)
        engine = EvolutionEngine(
            config=config, role="researcher", benchmark=ResearchBenchmark(),
            directive_pool=pool,
            constitution=gates.research_constitution(mode=config.constitution_mode))
        report = engine.evolve(generations=self.generations)
        event = EvolveEvent(
            at_paper=self._seen, directives_added=len(self.directives),
            score_before=report.best_score_before, score_after=report.best_score_after,
            admitted=report.admitted)
        self.events.append(event)
        return event

    def maybe_evolve(self, config) -> EvolveEvent | None:
        """Evolve if the schedule + pressure conditions are met, else None."""
        return self.evolve(config) if self.should_evolve() else None

    def summary(self) -> str:
        lines = [f"auto-evolve: {len(self.events)} round(s), "
                 f"{len(self.directives)} learned directive(s)"]
        rec = self.recurring()
        if rec:
            lines.append(f"  recurring weaknesses → doctrine: {', '.join(rec)}")
        for e in self.events:
            lines.append(f"  @paper {e.at_paper}: +{e.directives_added} directives, "
                         f"score {e.score_before}→{e.score_after} (gain {e.gain}, "
                         f"admitted {e.admitted})")
        return "\n".join(lines)
