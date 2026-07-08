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
from .ideas import Idea, mine_ideas, revise_idea
from .ingest import IngestResult, Paper, ingest_topic
from .novelty import NoveltyReport, assess
from .paper import PaperArtifact, write_paper
from .topics import TOPICS, TOPICS_BY_SLUG, Topic

MAX_REVISIONS = 3
CANDIDATES_PER_TOPIC = 6


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

    def summary(self) -> str:
        a = "ACCEPTED" if self.accepted else "REJECTED"
        pdf = " (+PDF)" if self.artifact and self.artifact.compiled else ""
        return (
            f"[{a}] {self.idea.title}\n"
            f"  topic={self.topic} venue={self.idea.target_venue} "
            f"considered={self.considered} revisions={self.revisions}\n"
            f"  novelty={self.report.novelty:.2f} impact={self.idea.impact:.2f} "
            f"fitness={self.idea.fitness:.2f} verdict={self.report.verdict}\n"
            f"  experiment={self.experiment.headline()}\n"
            f"  artifact={(self.artifact.tex_path if self.artifact else 'n/a')}{pdf}\n"
            f"  gate={'clean' if not (self.artifact and self.artifact.violations) else self.artifact.violations}"
        )


def _select_idea(topic: Topic, corpus: list[Paper], ctx=None,
                 variant: int = 0) -> tuple[Idea, NoveltyReport, int, int]:
    """Mine, bar-raise, and iterate until an idea clears the bar (or revisions run out).

    Returns (best_idea, its_report, revisions_used, candidates_considered).
    """
    prior_titles = [p.title for p in corpus]
    candidates = mine_ideas(topic, n=CANDIDATES_PER_TOPIC, ctx=ctx,
                            prior_titles=prior_titles, variant=variant)
    scored = [(idea, assess(idea, corpus, ctx)) for idea in candidates]
    considered = len(scored)
    # Rank by fitness; a 'pass' always outranks 'revise'/'reject'.
    scored.sort(key=lambda ir: (ir[1].verdict == "pass", ir[0].fitness), reverse=True)
    # Rotate the pick through the passing ideas by `variant` so a 24/7 loop ships
    # a *different* high-quality paper each run instead of re-selecting the argmax.
    passing = [ir for ir in scored if ir[1].verdict == "pass"]
    pool = passing or scored
    best_idea, best_report = pool[variant % len(pool)]

    revisions = 0
    while best_report.verdict != "pass" and revisions < MAX_REVISIONS:
        revised = revise_idea(best_idea, best_report.rationale, topic, ctx)
        revised.nearest_prior = best_idea.nearest_prior
        rep = assess(revised, corpus, ctx)
        considered += 1
        revisions += 1
        # Keep the better of the two by fitness (elitist iteration).
        if (rep.verdict == "pass") or (rep.novelty > best_report.novelty
                                       and revised.fitness >= best_idea.fitness):
            best_idea, best_report = revised, rep
        if best_report.verdict == "pass":
            break
    return best_idea, best_report, revisions, considered


def produce_paper(topic_slug: str, ctx=None, outdir: str = "output/papers",
                  seed: int = 1337) -> PaperResult:
    """Run the full pipeline for one topic and return the result (accepted or not)."""
    topic = TOPICS_BY_SLUG.get(topic_slug) or TOPICS[0]
    memory = getattr(ctx, "memory", None)
    ingest = ingest_topic(topic, fetcher=_fetcher_from_ctx(ctx), memory=memory)
    corpus = ingest.corpus

    idea, report, revisions, considered = _select_idea(topic, corpus, ctx, variant=seed)

    # Deep-dive: run the real experiment for this topic and write the paper.
    exp = run_experiment(topic.slug, seed=seed)
    artifact = write_paper(idea, exp, report, corpus, outdir=outdir,
                           gate_check=gates.check_research)

    # Bar-raiser acceptance: novelty must clear the bar AND the integrity gate
    # must be clean. This is the "all publications must go through" check.
    accepted = report.passes and not artifact.violations
    reason = ("cleared novelty bar and integrity gate" if accepted
              else ("integrity gate: " + "; ".join(artifact.violations) if artifact.violations
                    else f"below novelty/fitness bar (verdict={report.verdict})"))
    return PaperResult(
        topic=topic.slug, idea=idea, report=report, experiment=exp, artifact=artifact,
        accepted=accepted, revisions=revisions, considered=considered, ingest=ingest,
        reason=reason,
    )


@dataclass
class ServeReport:
    produced: list[PaperResult] = field(default_factory=list)

    @property
    def accepted(self) -> list[PaperResult]:
        return [r for r in self.produced if r.accepted]

    def summary(self) -> str:
        lines = [f"Dark factory produced {len(self.produced)} papers, "
                 f"{len(self.accepted)} cleared the bar:"]
        for r in self.produced:
            mark = "✓" if r.accepted else "✗"
            lines.append(f"  {mark} [{r.topic}] {r.idea.title[:60]}  "
                         f"(nov {r.report.novelty:.2f}, {r.experiment.headline().split(';')[0]})")
        return "\n".join(lines)


def serve(topics: list[str] | None = None, ctx=None, outdir: str = "output/papers",
          max_papers: int = 10, seed: int = 1337, on_paper=None) -> ServeReport:
    """Continuous production across topics — the 24/7 loop, bounded by max_papers.

    ``on_paper(result)`` is invoked after each paper (e.g. to write to memory or a
    ledger). For a true always-on daemon, wrap this in the CLI ``serve`` command
    or the NYX CapabilityRunner with ``keep_going=True``.
    """
    slugs = topics or [t.slug for t in TOPICS]
    report = ServeReport()
    i = 0
    while len(report.produced) < max_papers:
        slug = slugs[i % len(slugs)]
        # Vary the seed per paper so successive papers on a topic differ.
        result = produce_paper(slug, ctx=ctx, outdir=outdir, seed=seed + i)
        report.produced.append(result)
        if on_paper:
            on_paper(result)
        i += 1
    return report


def write_index(report: ServeReport, outdir: str = "output/papers") -> str:
    """Write a Markdown index of produced papers for the operator to browse."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Dark Factory — Produced Papers\n"]
    for r in report.produced:
        mark = "✅" if r.accepted else "❌"
        tex = Path(r.artifact.tex_path).name if r.artifact else "n/a"
        lines.append(f"- {mark} **{r.idea.title}** — `{r.topic}` → {r.idea.target_venue}  \n"
                     f"  novelty {r.report.novelty:.2f}, {r.experiment.headline()}  \n"
                     f"  [`{tex}`]({tex})")
    path = out / "INDEX.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
