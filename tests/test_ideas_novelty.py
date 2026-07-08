"""Idea mining + the novelty bar-raiser."""
from __future__ import annotations

from darkfactory.ideas import Idea, mine_ideas, revise_idea
from darkfactory.ingest import corpus_for
from darkfactory.novelty import NOVELTY_BAR, assess, assess_offline
from darkfactory.topics import TOPICS_BY_SLUG


def test_mining_produces_structured_ideas():
    topic = TOPICS_BY_SLUG["prompt-injection"]
    ideas = mine_ideas(topic, n=5)
    assert len(ideas) == 5
    for idea in ideas:
        assert idea.title and idea.hypothesis and idea.approach and idea.contribution
        assert idea.topic == "prompt-injection"
        assert 0.0 <= idea.fitness <= 1.0


def test_variant_diversifies_ideas():
    topic = TOPICS_BY_SLUG["prompt-injection"]
    a = mine_ideas(topic, n=6, variant=0)[0].title
    b = mine_ideas(topic, n=6, variant=3)[0].title
    assert a != b  # different variants explore different directions


def test_novelty_penalizes_near_duplicate_of_prior_art():
    prior = corpus_for("prompt-injection")
    # An idea that restates a known paper should score LOW novelty.
    dup = Idea(
        id="dup", topic="prompt-injection",
        title="Indirect prompt injection compromises LLM-integrated applications",
        hypothesis="Adversarial instructions embedded in retrieved content compromise apps.",
        approach="Embed payloads in retrieved documents.",
        contribution="Show indirect prompt injection compromises real applications.",
        threat_model="indirect/retrieved injection", target_venue="satml",
    )
    report = assess_offline(dup, prior)
    assert report.novelty < NOVELTY_BAR  # the bar-raiser catches the near-duplicate
    assert report.verdict in ("revise", "reject")


def test_novel_idea_can_clear_the_bar():
    topic = TOPICS_BY_SLUG["prompt-injection"]
    prior = corpus_for("prompt-injection")
    ideas = mine_ideas(topic, n=6)
    reports = [assess(i, prior) for i in ideas]
    assert any(r.verdict == "pass" for r in reports)  # a genuinely novel one exists


def test_revision_increments_lineage_and_generation():
    topic = TOPICS_BY_SLUG["prompt-injection"]
    idea = mine_ideas(topic, n=6)[0]
    revised = revise_idea(idea, "too close to prior art", topic)
    assert revised.generation == idea.generation + 1
    assert idea.id in revised.lineage
    assert revised.revisions
