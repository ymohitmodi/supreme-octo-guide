"""AISecurityResearchCapability — the dark factory as a NYX capability.

Plugs into NYX's generic CapabilityRunner so the research team gets continual
learning, Darwinian evolution, budget control, and a tamper-evident audit ledger
for free. One *cycle* = one end-to-end paper: mine → bar-raise → iterate →
experiment → write → gate. The ``researcher`` genome is evolved against the
:class:`ResearchBenchmark`, so the doctrine that mines better ideas is selected
over time.

    nyx run "publish AI security research on prompt injection" --keep-going

routes here (via keyword/LLM routing) and drives the loop autonomously.
"""
from __future__ import annotations

import re

from nyx.capabilities.base import Capability, CycleContext, CycleResult, EvalResult

from . import gates, roles  # noqa: F401 — importing roles registers the researcher role
from .evolution import RESEARCH_DIRECTIVES, ResearchBenchmark
from .pipeline import produce_paper
from .topics import TOPICS, TOPICS_BY_SLUG, seed_doctrine, topic_for

_MATCH = re.compile(
    r"\b(ai[\s-]?security|adversarial|prompt injection|jailbreak|red[\s-]?team|"
    r"model (?:extraction|stealing)|data poison|backdoor|membership inference|"
    r"watermark|agentic security|rag security|robustness|research paper|publication|"
    r"conference|arxiv|benchmark)\b", re.IGNORECASE)


class AISecurityResearchCapability(Capability):
    name = "ai-security-research"
    description = ("Autonomously research AI security, mine + validate novel ideas against "
                   "conference prior art, run real benchmarks, and write conference-grade "
                   "LaTeX/PDF papers.")

    def __init__(self, outdir: str = "output/papers"):
        self.outdir = outdir

    # --- routing ---
    def matches(self, objective: str) -> bool:
        return bool(_MATCH.search(objective))

    # --- least privilege: the researcher reads the web + long docs, nothing else ---
    def allowed_tools(self) -> set[str]:
        return {"web_fetch", "web_crawl", "read_url", "mcp.*"}

    # --- evolution wiring ---
    def evolve_role(self) -> str:
        return "researcher"

    def directives(self):
        return RESEARCH_DIRECTIVES

    def benchmark(self, ctx: CycleContext) -> ResearchBenchmark:
        return ResearchBenchmark()

    def eval(self, config, provider):
        from nyx.evolution.archive import Archive
        best = Archive(config.evolution_archive).best_for("researcher")
        genome = best.to_genome() if best else None
        res = ResearchBenchmark().evaluate(genome)
        return EvalResult(score=res.score,
                          detail=f"held-out research doctrine, strength={res.strength:.2f}, "
                                 f"{'evolved' if best else 'seed'} researcher")

    # --- governance & knowledge ---
    def constitution(self, base):
        # Extend the base the runner already loaded — never reload from disk.
        return gates.add_research_forbidden(base)

    def seed_memory(self, memory) -> int:
        return seed_doctrine(memory)

    def refresh_knowledge(self, ctx: CycleContext) -> dict:
        """Keep reading the AI-security literature into memory (best-effort)."""
        from .ingest import ingest_topic
        from .pipeline import _fetcher_from_ctx
        topic = TOPICS[ctx.cycle_index % len(TOPICS)]
        res = ingest_topic(topic, fetcher=_fetcher_from_ctx(ctx), memory=ctx.memory)
        return res.stats()

    # --- planning & acting ---
    def plan(self, objective: str, ctx: CycleContext) -> list[str]:
        """Decide which topics to write papers on. A specific topic in the objective
        focuses the backlog; otherwise sweep the whole taxonomy."""
        focus = topic_for(objective)
        if focus is not None:
            # Lead with the focus topic, then diversify across the frontier.
            others = [t.slug for t in TOPICS if t.slug != focus.slug]
            return [focus.slug, focus.slug] + others
        return [t.slug for t in TOPICS]

    def execute(self, task: str, ctx: CycleContext) -> CycleResult:
        topic_slug = task if task in TOPICS_BY_SLUG else (
            (topic_for(task) or TOPICS[0]).slug)
        result = produce_paper(topic_slug, ctx=ctx, outdir=self.outdir,
                               seed=1337 + ctx.cycle_index)
        idea, rep, art = result.idea, result.report, result.artifact
        blocked = None if result.accepted else (
            "G_RESEARCH" if (art and art.violations) else "G_NOVELTY_BAR")
        summary = (f"{'ACCEPTED' if result.accepted else 'REJECTED'}: {idea.title} "
                   f"→ {idea.target_venue}. novelty={rep.novelty:.2f} "
                   f"fitness={idea.fitness:.2f}. {result.experiment.finding}")
        # Feed the realized outcome back as a trusted track record so the factory
        # accumulates what actually clears the bar.
        lessons = [(
            f"TRACK RECORD — [{topic_slug}] '{idea.title[:50]}': "
            f"{'accepted' if result.accepted else 'rejected'} at novelty {rep.novelty:.2f}, "
            f"fitness {idea.fitness:.2f}; experiment {result.experiment.headline()}.",
            "track-record", ["ai-security", topic_slug, "publication", "realized"],
        )]
        return CycleResult(
            item=task, ok=result.accepted, summary=summary, score=idea.fitness,
            blocked_at=blocked, findings=(art.violations if art else []), lessons=lessons,
        )
