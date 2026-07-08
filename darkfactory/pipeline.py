"""The dark-factory pipeline — one validated paper, end to end.

    ingest SOTA → mine ideas → bar-raise vs prior art → iterate/revise toward the
    bar → deep-dive the survivor → run a real experiment → write LaTeX/PDF →
    enforce the integrity gate → accept or reject.

``produce_paper`` runs the whole thing for one topic and returns a
:class:`PaperResult`. ``serve`` drives it continuously across the taxonomy — the
24/7 loop that targets a monthly paper cadence. Both work offline (deterministic)
and light up the brain automatically when a NYX ``CycleContext`` with a live
provider is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import gates
from .experiments import ExperimentResult, run_experiment
from .ideas import Idea, extend_idea, mine_ideas, revise_idea
from .ingest import IngestResult, Paper, ingest_topic
from .memory import Contribution, ResearchLedger
from .novelty import FITNESS_BAR, NoveltyReport, assess
from .paper import PaperArtifact, write_paper
from .review import ReviewReport, review
from .topics import TOPICS, TOPICS_BY_SLUG, Topic

MAX_REVISIONS = 3
CANDIDATES_PER_TOPIC = 6


def _contribution_id(topic: str, cycle: int) -> str:
    return f"contrib-{topic}-{cycle:04d}"


def _fetcher_from_ctx(ctx):
    if ctx is None:
        return None
    try:
        from nyx.tools import WebFetcher
        cfg = ctx.config
        return WebFetcher(cache_dir=cfg.web_cache_dir, user_agent=cfg.user_agent,
                          allowed_domains=cfg.allowed_domains,
                          rate_limit_seconds=cfg.web_rate_limit_seconds)
    except Exception:  # noqa: BLE001 — ingestion is best-effort
        return None


@dataclass
class PaperResult:
    topic: str
    idea: Idea
    report: NoveltyReport
    experiment: ExperimentResult
    artifact: PaperArtifact | None
    accepted: bool
    revisions: int = 0
    considered: int = 0
    ingest: IngestResult | None = None
    reason: str = ""
    cycle: int = 0
    bar: float = 0.0
    review: ReviewReport | None = None
    depth: int = 0
    builds_on: list[str] = field(default_factory=list)
    capital: float = 0.0

    def summary(self) -> str:
        a = "ACCEPTED" if self.accepted else "REJECTED"
        pdf = " (+PDF)" if self.artifact and self.artifact.compiled else ""
        built = (f"\n  builds on: {', '.join(t[:40] for t in self.builds_on)} (depth {self.depth})"
                 if self.builds_on else "")
        rev = (f"{self.review.recommendation} ({self.review.score:.2f})"
               if self.review else "n/a")
        return (
            f"[{a}] {self.idea.title}\n"
            f"  topic={self.topic} venue={self.idea.target_venue} cycle={self.cycle} "
            f"considered={self.considered} revisions={self.revisions}\n"
            f"  novelty={self.report.novelty:.2f} (bar {self.bar:.2f}) impact={self.idea.impact:.2f} "
            f"fitness={self.idea.fitness:.2f} | review={rev}\n"
            f"  experiment={self.experiment.headline()}{built}\n"
            f"  artifact={(self.artifact.tex_path if self.artifact else 'n/a')}{pdf}\n"
            f"  gate={'clean' if not (self.artifact and self.artifact.violations) else self.artifact.violations}"
            f" | research_capital={self.capital:.2f}"
        )


def _select_idea(topic: Topic, corpus: list[Paper], ctx=None, variant: int = 0,
                 bar: float = FITNESS_BAR, seed_ideas: list[Idea] | None = None
                 ) -> tuple[Idea, NoveltyReport, int, int]:
    """Mine, bar-raise, and iterate until an idea clears the (dynamic) bar.

    ``seed_ideas`` are pre-built candidates (e.g. build-on extensions of prior
    contributions) that compete with freshly mined ideas — this is how the
    compounding step enters selection. Returns
    (best_idea, its_report, revisions_used, candidates_considered).
    """
    prior_titles = [p.title for p in corpus]
    seed_ideas = list(seed_ideas or [])
    candidates = seed_ideas + mine_ideas(
        topic, n=CANDIDATES_PER_TOPIC, ctx=ctx, prior_titles=prior_titles, variant=variant)
    scored = [(idea, assess(idea, corpus, ctx, bar=bar)) for idea in candidates]
    considered = len(scored)

    def _by_fitness(pairs):
        return sorted(pairs, key=lambda ir: ir[0].fitness, reverse=True)

    passing = [ir for ir in scored if ir[1].verdict == "pass"]
    # Prefer compounding: if any build-on (lineage) idea clears the bar, ship it —
    # that's the "one step at a time" step forward. Rotate among the build-on
    # options by `variant` for diversity; only fall back to fresh ideas otherwise.
    passing_buildon = _by_fitness([ir for ir in passing if ir[0].lineage])
    passing_fresh = _by_fitness([ir for ir in passing if not ir[0].lineage])
    if passing_buildon:
        best_idea, best_report = passing_buildon[variant % len(passing_buildon)]
    elif passing_fresh:
        best_idea, best_report = passing_fresh[variant % len(passing_fresh)]
    else:
        best_idea, best_report = _by_fitness(scored)[0]

    revisions = 0
    while best_report.verdict != "pass" and revisions < MAX_REVISIONS:
        revised = revise_idea(best_idea, best_report.rationale, topic, ctx)
        revised.nearest_prior = best_idea.nearest_prior
        rep = assess(revised, corpus, ctx, bar=bar)
        considered += 1
        revisions += 1
        if (rep.verdict == "pass") or (rep.novelty > best_report.novelty
                                       and revised.fitness >= best_idea.fitness):
            best_idea, best_report = revised, rep
        if best_report.verdict == "pass":
            break
    return best_idea, best_report, revisions, considered


def produce_paper(topic_slug: str, ctx=None, outdir: str = "output/papers",
                  seed: int = 1337, ledger: ResearchLedger | None = None) -> PaperResult:
    """Run the full compounding pipeline for one topic and return the result.

    Each call is a *cycle*: it stands on the factory's prior contributions (via the
    offline ledger), tries to build one step further, must clear a novelty bar that
    ratchets up with accumulated research capital, and — if accepted — records a new
    contribution so the next cycle compounds on it.
    """
    topic = TOPICS_BY_SLUG.get(topic_slug) or TOPICS[0]
    ledger = ledger if ledger is not None else ResearchLedger()
    cycle = ledger.next_cycle()
    bar = ledger.current_bar()

    memory = getattr(ctx, "memory", None)
    ingest = ingest_topic(topic, fetcher=_fetcher_from_ctx(ctx), memory=memory, ctx=ctx)
    corpus = ingest.corpus

    # Compounding: build on the best prior contribution for this topic, if any.
    prior = ledger.best_for_topic(topic.slug)
    seed_ideas: list[Idea] = []
    if prior is not None:
        seed_ideas = [extend_idea(prior.title, topic.slug, topic, ctx, variant=v)
                      for v in (seed, seed + 1)]

    idea, report, revisions, considered = _select_idea(
        topic, corpus, ctx, variant=seed, bar=bar, seed_ideas=seed_ideas)

    # Is the chosen idea a build-on of the prior contribution?
    building_on = prior if (prior is not None and prior.title in idea.lineage) else None
    builds_on_titles = [building_on.title] if building_on else []
    depth = (building_on.depth + 1) if building_on else 0

    # Deep-dive: run the real experiment and write the paper (self-citing prior work).
    exp = run_experiment(topic.slug, seed=seed)
    artifact = write_paper(idea, exp, report, corpus, outdir=outdir,
                           gate_check=gates.check_research, builds_on_titles=builds_on_titles)

    # Thoroughness review against the world-leading-conference bar.
    rev = review(idea, exp, artifact.tex, n_citations=len(idea.nearest_prior[:6]), ctx=ctx)

    # Acceptance = novelty bar (dynamic) AND integrity gate AND conference-bar review.
    accepted = report.passes and not artifact.violations and rev.meets_bar
    if accepted:
        reason = "cleared novelty bar, integrity gate, and conference-bar review"
    elif artifact.violations:
        reason = "integrity gate: " + "; ".join(artifact.violations)
    elif not report.passes:
        reason = f"below novelty bar {bar:.2f} (novelty {report.novelty:.2f}, verdict {report.verdict})"
    else:
        reason = f"failed thoroughness review ({rev.recommendation}): missing {rev.failed()}"

    if accepted:
        contrib = Contribution(
            id=_contribution_id(topic.slug, cycle), cycle=cycle, topic=topic.slug,
            title=idea.title, idea_id=idea.id, venue=idea.target_venue,
            novelty=report.novelty, impact=idea.impact, fitness=idea.fitness,
            result_headline=exp.headline(),
            builds_on=[building_on.id] if building_on else [],
            cites=[t for t in idea.nearest_prior[:4]], artifact=artifact.tex_path, depth=depth,
        )
        ledger.add(contrib)

    return PaperResult(
        topic=topic.slug, idea=idea, report=report, experiment=exp, artifact=artifact,
        accepted=accepted, revisions=revisions, considered=considered, ingest=ingest,
        reason=reason, cycle=cycle, bar=bar, review=rev, depth=depth,
        builds_on=builds_on_titles, capital=ledger.research_capital(),
    )


@dataclass
class ServeReport:
    produced: list[PaperResult] = field(default_factory=list)

    @property
    def accepted(self) -> list[PaperResult]:
        return [r for r in self.produced if r.accepted]

    capital_start: float = 0.0
    capital_end: float = 0.0
    bar_start: float = 0.0
    bar_end: float = 0.0

    def summary(self) -> str:
        lines = [f"Dark factory produced {len(self.produced)} papers, "
                 f"{len(self.accepted)} cleared the bar. "
                 f"Research capital {self.capital_start:.2f} → {self.capital_end:.2f}, "
                 f"novelty bar {self.bar_start:.3f} → {self.bar_end:.3f} (compounding):"]
        for r in self.produced:
            mark = "✓" if r.accepted else "✗"
            depth = f" d{r.depth}↑" if r.builds_on else ""
            lines.append(f"  {mark} [{r.topic}] {r.idea.title[:56]}{depth}  "
                         f"(nov {r.report.novelty:.2f}/bar {r.bar:.2f}, "
                         f"{r.experiment.headline().split(';')[0]})")
        return "\n".join(lines)


def serve(topics: list[str] | None = None, ctx=None, outdir: str = "output/papers",
          max_papers: int = 10, seed: int = 1337, on_paper=None,
          ledger: ResearchLedger | None = None) -> ServeReport:
    """Continuous production across topics — the 24/7 loop, bounded by max_papers.

    A single :class:`ResearchLedger` is shared across the whole run so quality
    *compounds*: each paper stands on the accumulated contributions, the novelty
    bar ratchets up with research capital, and later papers build on earlier ones.
    For a true always-on daemon, wrap this in the CLI ``serve`` command or the NYX
    CapabilityRunner with ``keep_going=True`` (both persist the ledger to disk).
    """
    slugs = topics or [t.slug for t in TOPICS]
    ledger = ledger if ledger is not None else ResearchLedger()
    report = ServeReport(capital_start=ledger.research_capital(), bar_start=ledger.current_bar())
    i = 0
    while len(report.produced) < max_papers:
        slug = slugs[i % len(slugs)]
        # Vary the seed per paper so successive papers on a topic differ.
        result = produce_paper(slug, ctx=ctx, outdir=outdir, seed=seed + i, ledger=ledger)
        report.produced.append(result)
        if on_paper:
            on_paper(result)
        i += 1
    report.capital_end = ledger.research_capital()
    report.bar_end = ledger.current_bar()
    return report


def write_index(report: ServeReport, outdir: str = "output/papers") -> str:
    """Write a Markdown index of produced papers for the operator to browse."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Dark Factory — Produced Papers\n"]
    if report.produced:
        lines.append(f"Research capital {report.capital_start:.2f} → {report.capital_end:.2f}; "
                     f"novelty bar {report.bar_start:.3f} → {report.bar_end:.3f} "
                     "(quality compounds each cycle).\n")
    for r in report.produced:
        mark = "✅" if r.accepted else "❌"
        tex = Path(r.artifact.tex_path).name if r.artifact else "n/a"
        built = f" · builds on prior work (depth {r.depth})" if r.builds_on else ""
        lines.append(f"- {mark} **{r.idea.title}** — `{r.topic}` → {r.idea.target_venue}{built}  \n"
                     f"  novelty {r.report.novelty:.2f} (bar {r.bar:.2f}), {r.experiment.headline()}  \n"
                     f"  [`{tex}`]({tex})")
    path = out / "INDEX.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
