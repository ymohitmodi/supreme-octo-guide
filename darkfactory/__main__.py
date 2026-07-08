"""Dark Factory command-line console.

    darkfactory topics                 list the AI-security research frontier
    darkfactory ingest <topic>         show the prior-art corpus (curated + live)
    darkfactory ideas <topic>          mine + bar-raise candidate ideas
    darkfactory experiment <topic>     run the real benchmark and print metrics
    darkfactory paper <topic>          produce ONE full paper end to end
    darkfactory serve --max N          24/7 loop: keep producing gated papers
    darkfactory evolve -g N            evolve the researcher doctrine (Darwin)
    darkfactory doctor                 verify NYX, brain, and TeX availability
"""
from __future__ import annotations

import argparse
import types

from .conferences import primary_venue
from .experiments import run_experiment
from .ideas import mine_ideas
from .ingest import ingest_topic
from .novelty import assess
from .pipeline import produce_paper, serve, write_index
from .topics import TOPICS, TOPICS_BY_SLUG, topic_for


def _resolve_topic(name: str):
    return TOPICS_BY_SLUG.get(name) or topic_for(name) or TOPICS[0]


def _live_ctx():
    """Build a lightweight context that lights up the brain when OLLAMA_API_KEY is set.

    Offline (mock mode) this returns None, so the whole pipeline stays deterministic.
    """
    try:
        from nyx.config import load_config
        cfg = load_config()
        if cfg.mock_mode:
            return None
        from nyx.embeddings import embedder_for
        from nyx.memory import MemoryStore
        from nyx.providers import build_provider
        provider = build_provider(cfg)
        memory = MemoryStore(cfg.memory_path, embedder=embedder_for(cfg, provider))
        return types.SimpleNamespace(config=cfg, provider=provider, memory=memory,
                                     lessons=[], cycle_index=0)
    except Exception:  # noqa: BLE001 — fall back to offline
        return None


def cmd_topics(args) -> int:
    print("AI-security research frontier:\n")
    for t in TOPICS:
        v = primary_venue(t.slug)
        print(f"  {t.slug:24s} {t.name}\n{'':26s}→ {v.name}")
    return 0


def cmd_ingest(args) -> int:
    topic = _resolve_topic(args.topic)
    res = ingest_topic(topic, fetcher=None)
    print(f"Prior-art corpus for {topic.slug}: {res.stats()}\n")
    for p in res.corpus:
        print(f"  [{p.year or 'n/a'}] {p.title}")
    return 0


def cmd_ideas(args) -> int:
    topic = _resolve_topic(args.topic)
    ctx = _live_ctx()
    res = ingest_topic(topic, fetcher=None)
    ideas = mine_ideas(topic, n=args.n, ctx=ctx, prior_titles=[p.title for p in res.corpus])
    scored = sorted(((assess(i, res.corpus, ctx), i) for i in ideas),
                    key=lambda ri: ri[1].fitness, reverse=True)
    print(f"Mined {len(ideas)} ideas for {topic.slug} "
          f"(brain={'live' if ctx else 'mock'}):\n")
    for rep, idea in scored:
        print(f"  [{rep.verdict:6s}] nov={idea.novelty:.2f} imp={idea.impact:.2f} "
              f"fit={idea.fitness:.2f} :: {idea.title}")
        if rep.nearest:
            print(f"{'':11s}closest prior: {rep.nearest[0][0][:70]} (sim {rep.nearest[0][1]})")
    return 0


def cmd_experiment(args) -> int:
    topic = _resolve_topic(args.topic)
    exp = run_experiment(topic.slug, seed=args.seed)
    print(f"Experiment [{exp.family}] for {topic.slug} (seed {exp.seed})")
    print(f"  dataset: {exp.dataset}\n  method : {exp.method}\n")
    print("  " + " | ".join(exp.table_headers))
    for row in exp.table_rows:
        print("  " + " | ".join(row))
    print(f"\n  finding: {exp.finding}")
    return 0


def cmd_paper(args) -> int:
    topic = _resolve_topic(args.topic)
    ctx = _live_ctx()
    result = produce_paper(topic.slug, ctx=ctx, outdir=args.outdir, seed=args.seed)
    print(result.summary())
    return 0 if result.accepted else 1


def cmd_serve(args) -> int:
    ctx = _live_ctx()
    topics = args.topics.split(",") if args.topics else None
    report = serve(topics=topics, ctx=ctx, outdir=args.outdir, max_papers=args.max)
    index = write_index(report, outdir=args.outdir)
    print(report.summary())
    print(f"\nIndex: {index}")
    return 0


def cmd_evolve(args) -> int:
    from nyx.config import load_config
    from nyx.evolution.engine import EvolutionEngine

    from .evolution import RESEARCH_DIRECTIVES, ResearchBenchmark
    from . import roles  # noqa: F401 — ensure the researcher role is registered

    cfg = load_config()
    # Provide a constitution explicitly (with a file-missing fallback) so the
    # engine never tries to load the YAML from a cwd that may not have it.
    from . import gates
    engine = EvolutionEngine(config=cfg, role="researcher", benchmark=ResearchBenchmark(),
                             directive_pool=RESEARCH_DIRECTIVES,
                             constitution=gates.research_constitution(mode=cfg.constitution_mode))
    report = engine.evolve(generations=args.generations)
    print(f"Evolved researcher doctrine over {report.generations} generations:")
    print(f"  admitted={report.admitted} rejected={report.rejected} "
          f"archive={report.archive_size}")
    print(f"  best {report.best_score_before} → {report.best_score_after} "
          f"(gain {report.gain})")
    return 0


def cmd_doctor(args) -> int:
    ok = True
    try:
        import nyx
        print(f"✓ nyx importable (v{nyx.__version__})")
    except Exception as exc:  # noqa: BLE001
        print(f"✗ nyx not importable: {exc}")
        return 1
    from nyx.agents.roles import ROLE_REGISTRY
    from nyx.capabilities.registry import get
    print(f"{'✓' if 'researcher' in ROLE_REGISTRY else '✗'} researcher role registered")
    print(f"{'✓' if get('ai-security-research') else '✗'} capability registered")
    from nyx.config import load_config
    cfg = load_config()
    print(f"• brain: {'MOCK (offline)' if cfg.mock_mode else 'Ollama Cloud @ ' + cfg.ollama_host}")
    import shutil
    tex = shutil.which("pdflatex") or shutil.which("tectonic")
    print(f"• TeX: {tex or 'not found — papers emit .tex + .md (no PDF)'}")
    print(f"• topics: {len(TOPICS)} on the frontier")
    print("\nDoctor:", "healthy ✓" if ok else "issues found ✗")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="darkfactory",
                                description="Autonomous AI-security research dark factory")
    p.add_argument("--version", action="version", version=f"darkfactory {__import__('darkfactory').__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("topics", help="list the research frontier")
    sp.set_defaults(func=cmd_topics)

    sp = sub.add_parser("ingest", help="show the prior-art corpus for a topic")
    sp.add_argument("topic")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("ideas", help="mine + bar-raise ideas for a topic")
    sp.add_argument("topic")
    sp.add_argument("-n", type=int, default=6)
    sp.set_defaults(func=cmd_ideas)

    sp = sub.add_parser("experiment", help="run the real benchmark for a topic")
    sp.add_argument("topic")
    sp.add_argument("--seed", type=int, default=1337)
    sp.set_defaults(func=cmd_experiment)

    sp = sub.add_parser("paper", help="produce one full paper end to end")
    sp.add_argument("topic")
    sp.add_argument("--outdir", default="output/papers")
    sp.add_argument("--seed", type=int, default=1337)
    sp.set_defaults(func=cmd_paper)

    sp = sub.add_parser("serve", help="24/7 loop: keep producing gated papers")
    sp.add_argument("--max", type=int, default=10, help="papers to produce this run")
    sp.add_argument("--topics", help="comma-separated topic slugs (default: all)")
    sp.add_argument("--outdir", default="output/papers")
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("evolve", help="evolve the researcher doctrine (Darwin-Gödel)")
    sp.add_argument("-g", "--generations", type=int, default=8)
    sp.set_defaults(func=cmd_evolve)

    sp = sub.add_parser("doctor", help="verify NYX, brain, and TeX availability")
    sp.set_defaults(func=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
