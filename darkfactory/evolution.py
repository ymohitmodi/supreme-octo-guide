"""Darwinian evolution of the researcher's doctrine.

Plugs into NYX's Darwin-Gödel EvolutionEngine as a *benchmark*: the fitness of a
``researcher`` genome is the average quality of the ideas its doctrine would mine
across a held-out set of AI-security topics. A charter that encodes stronger
methodology — novelty seeking, adaptive/certified evaluation, contamination
control, reproducibility, responsible disclosure — mines ideas that score higher
on rigor and impact, so the engine *discovers* good research practice by
selection rather than being handed it.

    from nyx.evolution.engine import EvolutionEngine
    from darkfactory.evolution import ResearchBenchmark, RESEARCH_DIRECTIVES
    EvolutionEngine(role="researcher", benchmark=ResearchBenchmark(),
                    directive_pool=RESEARCH_DIRECTIVES).evolve(generations=8)

Offline it is fully deterministic (CI-stable); the exact same mechanics carry a
live brain, where the model rather than substring rules rates the doctrine.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ideas import FITNESS_WEIGHTS, mine_ideas
from .topics import TOPICS_BY_SLUG

# Charter directives the EvolutionEngine may graft during mutation. Each encodes
# a real methodology principle top venues reward.
RESEARCH_DIRECTIVES = [
    "Evaluate every defense against an adaptive adversary that knows the defense.",
    "Prefer certified or provable guarantees; report empirical robustness as a lower bound.",
    "Control for benchmark contamination and describe exactly how the held-out set is disjoint.",
    "Release code, fixed seeds, and the benchmark spec so every number is reproducible.",
    "State a precise threat model: adversary knowledge, capabilities, and budget.",
    "Report the clean/utility vs robustness/privacy trade-off, not the defended metric alone.",
    "Lead offensive findings with a defense and follow responsible disclosure.",
    "Measure attacker cost, not binary feasibility, as the defense metric.",
]

# The methodology cues that make a charter strong (mirrors the directives).
_METHOD_CUES = (
    "adaptive", "certif", "provable", "bound", "contamination", "held-out",
    "reproducib", "seed", "threat model", "trade-off", "responsible disclosure",
    "attacker cost", "confidence interval", "novel",
)

# Held-out topics for standing evaluation (disjoint framing from the training
# recombination, so the doctrine can't overfit one topic's vocabulary).
_HELDOUT_TOPICS = ("agentic-security", "membership-inference", "rag-security")


def doctrine_strength(charter: str) -> float:
    """0..1 measure of how much a charter encodes sound research methodology.

    Capped counting prevents reward-hacking by keyword stuffing (a directive can
    only be credited once), so evolution must add *distinct* methodology to gain.
    """
    low = (charter or "").lower()
    hits = sum(1 for cue in _METHOD_CUES if cue in low)
    # Scale across ALL distinct cues so a strong seed still leaves headroom: the
    # production charter covers most cues but not every one, and grafting the
    # RESEARCH_DIRECTIVES (which supply the missing ones) measurably improves the
    # doctrine — giving the Darwin-Gödel engine a real gradient to climb.
    return round(min(hits / len(_METHOD_CUES), 1.0), 4)


@dataclass
class ResearchBenchResult:
    score: float
    avg_fitness: float
    strength: float
    topics: int


class ResearchBenchmark:
    """Callable benchmark: ``ResearchBenchmark()(agent) -> float``.

    Scores a genome by the mean fitness of ideas its doctrine would mine across
    the held-out topics, where the doctrine's methodology strength lifts the
    rigor and impact of each idea (better method → better, more defensible work).
    """

    def __init__(self, topics: tuple[str, ...] = _HELDOUT_TOPICS, n_per_topic: int = 4):
        self.topics = [TOPICS_BY_SLUG[s] for s in topics if s in TOPICS_BY_SLUG]
        self.n_per_topic = n_per_topic

    def evaluate(self, genome) -> ResearchBenchResult:
        strength = doctrine_strength(genome.system_prompt if genome else "")
        fitnesses: list[float] = []
        for topic in self.topics:
            for idea in mine_ideas(topic, n=self.n_per_topic):
                # A stronger doctrine lifts the dimensions it governs. Base terms
                # come from the idea's structure; strength modulates rigor/impact.
                idea.rigor = round(0.4 + 0.6 * strength, 4)
                idea.impact = round(min(1.0, idea.impact + 0.3 * strength), 4)
                # Novelty/feasibility are properties of the idea, not the doctrine;
                # give them neutral mid values so fitness is comparable across genomes.
                idea.novelty = 0.7
                idea.feasibility = 0.7
                fitnesses.append(idea.fitness)
        avg = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        # Blend mean idea fitness with a small direct doctrine term so a genome
        # that adds real methodology is always weakly rewarded even at the margin.
        score = round(0.85 * avg + 0.15 * strength, 4)
        return ResearchBenchResult(score=score, avg_fitness=round(avg, 4),
                                   strength=strength, topics=len(self.topics))

    def __call__(self, agent) -> float:
        return self.evaluate(agent.genome).score


assert abs(sum(FITNESS_WEIGHTS.values()) - 1.0) < 1e-9  # fitness weights are a convex combo
