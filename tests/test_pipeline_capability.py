"""End-to-end pipeline, evolution, and NYX capability integration."""
from __future__ import annotations

from pathlib import Path

from darkfactory.capability import AISecurityResearchCapability
from darkfactory.evolution import RESEARCH_DIRECTIVES, ResearchBenchmark, doctrine_strength
from darkfactory.pipeline import produce_paper, serve


def test_produce_paper_end_to_end(tmp_path):
    result = produce_paper("prompt-injection", outdir=str(tmp_path), seed=1337)
    assert result.accepted
    assert result.artifact and Path(result.artifact.tex_path).exists()
    assert result.artifact.violations == []          # clean integrity gate
    assert result.report.novelty >= 0.0
    assert result.experiment.table_rows              # real experiment ran


def test_serve_produces_multiple_distinct_papers(tmp_path):
    report = serve(topics=["prompt-injection", "adversarial-examples"],
                   outdir=str(tmp_path), max_papers=4)
    assert len(report.produced) == 4
    assert len(report.accepted) >= 1
    # Papers on a repeated topic differ (24/7 diversity).
    titles = [r.idea.title for r in report.produced]
    assert len(set(titles)) >= 3


def test_evolution_rewards_stronger_doctrine():
    bench = ResearchBenchmark()

    class G:
        def __init__(self, prompt):
            self.system_prompt = prompt

    weak = bench.evaluate(G("You are a researcher."))
    strong_charter = (
        "You are a researcher. Use adaptive adversary evaluation, certified provable "
        "bounds, contamination control with held-out sets, reproducible seeds, a precise "
        "threat model, report the trade-off and confidence intervals, follow responsible "
        "disclosure, measure attacker cost, and seek novel results.")
    strong = bench.evaluate(G(strong_charter))
    assert strong.score > weak.score
    assert doctrine_strength(strong_charter) > 0.8   # near-complete methodology
    assert doctrine_strength("You are a researcher.") < 0.2
    assert RESEARCH_DIRECTIVES  # a non-empty directive pool for mutation


def test_capability_routing_and_registration():
    cap = AISecurityResearchCapability()
    assert cap.matches("publish AI security research on prompt injection")
    assert cap.matches("adversarial robustness benchmark for a conference")
    assert not cap.matches("find undervalued value stocks to buy")
    assert cap.evolve_role() == "researcher"
    # Registered into NYX so `nyx run` can route to it.
    from nyx.agents.roles import ROLE_REGISTRY
    from nyx.capabilities.registry import get
    import darkfactory  # noqa: F401 — import triggers registration
    assert "researcher" in ROLE_REGISTRY
    assert get("ai-security-research") is not None


def test_capability_plan_focuses_then_diversifies():
    cap = AISecurityResearchCapability()

    class Ctx:
        cycle_index = 0
    plan = cap.plan("research prompt injection defenses", Ctx())
    assert plan[0] == "prompt-injection"
    assert len(set(plan)) > 1  # diversifies beyond the focus topic
