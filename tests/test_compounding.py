"""Compounding memory — quality must build on prior work and the bar must rise."""
from __future__ import annotations

from darkfactory.memory import BASE_BAR, Contribution, ResearchLedger
from darkfactory.pipeline import produce_paper


def _contrib(cycle, topic="prompt-injection", depth=0, builds_on=None):
    return Contribution(
        id=f"c{cycle}", cycle=cycle, topic=topic, title=f"Paper {cycle}", idea_id=f"i{cycle}",
        venue="satml", novelty=0.9, impact=0.8, fitness=0.8, result_headline="F1=0.9",
        builds_on=builds_on or [], depth=depth)


def test_ledger_persists_and_accumulates_capital(tmp_path):
    path = str(tmp_path / "led.jsonl")
    led = ResearchLedger(path)
    assert led.research_capital() == 0.0
    led.add(_contrib(1))
    led.add(_contrib(2))
    # Reload from disk: contributions survive (offline memory).
    reloaded = ResearchLedger(path)
    assert len(reloaded) == 2
    assert reloaded.research_capital() > 0


def test_bar_ratchets_up_with_capital(tmp_path):
    led = ResearchLedger(str(tmp_path / "l.jsonl"))
    assert led.current_bar() == BASE_BAR
    for i in range(1, 8):
        led.add(_contrib(i, depth=i - 1))
    assert led.current_bar() > BASE_BAR       # bar rose with accumulated work
    assert led.current_bar() <= 0.80          # but stays bounded


def test_depth_amplifies_impact():
    shallow = _contrib(1, depth=0)
    deep = _contrib(2, depth=4)
    assert deep.impact_score > shallow.impact_score  # building on prior compounds


def test_pipeline_compounds_depth_and_capital(tmp_path):
    led = ResearchLedger(str(tmp_path / "l.jsonl"))
    papers = str(tmp_path / "papers")
    results = [produce_paper("prompt-injection", outdir=papers, seed=1337 + i, ledger=led)
               for i in range(4)]
    assert all(r.accepted for r in results)
    # Later cycles build on earlier ones: depth grows, capital grows, bar rises.
    assert results[-1].depth > results[0].depth
    assert results[-1].capital > results[0].capital
    assert results[-1].bar > results[0].bar
    # The deepest paper self-cites the prior contribution it extends.
    deepest = results[-1]
    assert deepest.builds_on
    assert "\\cite{ours0}" in deepest.artifact.tex


def test_lineage_chain_is_recorded(tmp_path):
    led = ResearchLedger(str(tmp_path / "l.jsonl"))
    for i in range(4):
        produce_paper("membership-inference", outdir=str(tmp_path / "p"), seed=2000 + i, ledger=led)
    best = led.best_for_topic("membership-inference")
    chain = led.lineage(best.id)
    assert len(chain) >= 2  # a real dependency chain, not isolated papers
