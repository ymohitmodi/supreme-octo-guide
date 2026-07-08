"""Internal adversarial+constructive critic, feedback-driven refine, skills, rubric."""
from __future__ import annotations

from darkfactory.critique import ACCEPT_BAR, critique, critique_offline
from darkfactory.experiments import run_experiment
from darkfactory.ideas import Idea, mine_ideas
from darkfactory.ingest import corpus_for
from darkfactory.knowledge import skill_files, sync_skills, titles
from darkfactory.novelty import assess
from darkfactory.paper import build_latex
from darkfactory.pipeline import produce_paper
from darkfactory.refine import refine
from darkfactory.reviewer_corpus import ARCHETYPES, DIMENSIONS, detect_weaknesses
from darkfactory.topics import TOPICS_BY_SLUG


def _fixture(slug="prompt-injection"):
    topic = TOPICS_BY_SLUG[slug]
    corpus = corpus_for(slug)
    idea = mine_ideas(topic, n=6)[0]
    report = assess(idea, corpus)
    exp = run_experiment(slug, seed=1337)
    return topic, corpus, idea, report, exp


# --- rubric corpus ---------------------------------------------------------
def test_dimension_weights_sum_to_one():
    assert abs(sum(d.weight for d in DIMENSIONS) - 1.0) < 1e-9


def test_detectors_flag_a_weak_bundle():
    weak = {"tex": "We propose a method.", "finding": "it always works on any model",
            "n_rows": 1, "n_citations": 0, "novelty": 0.3,
            "title": "A thing", "contribution": "we show it works"}
    fired = {a.id for a in detect_weaknesses(weak)}
    # No threat model, single row (no baseline), overclaiming, thin novelty, no artifact.
    assert "unrealistic-threat-model" in fired
    assert "weak-baselines" in fired
    assert "overclaiming" in fired
    assert "thin-novelty" in fired
    assert "not-foundational" in fired
    assert all(a.remedy for a in ARCHETYPES)  # every archetype carries a constructive fix


# --- critic ----------------------------------------------------------------
def test_strong_generated_paper_has_no_major_weakness():
    _, corpus, idea, report, exp = _fixture()
    tex = build_latex(idea, exp, report, corpus)
    crit = critique(idea, exp, tex)
    assert not crit.major                       # the factory's own papers clear the bar
    assert crit.overall >= ACCEPT_BAR


def test_critic_finds_major_weaknesses_in_a_bad_draft():
    _, corpus, idea, report, exp = _fixture()
    # A bare draft with no threat model and no adaptive evaluation — a real reviewer
    # rejects on exactly these.
    bad_tex = ("\\section{Introduction} We propose a method and report numbers in "
               "Table 1. \\section{Results} It performs well.")
    crit = critique_offline(idea, exp, bad_tex)
    fired = {w.archetype_id for w in crit.weaknesses}
    assert "unrealistic-threat-model" in fired
    assert "non-adaptive-eval" in fired
    assert crit.major                           # both are major → reject
    assert crit.verdict == "reject"
    # Every weakness is actionable — negative feedback carries a remedy.
    assert all(w.remedy for w in crit.weaknesses)


# --- feedback-driven refinement --------------------------------------------
def test_refine_turns_negative_feedback_constructive():
    topic, corpus, _, _, exp = _fixture()
    weak = Idea(id="w", topic="prompt-injection", title="A prompt injection attack on apps",
                hypothesis="Injected instructions compromise apps.", approach="We embed payloads.",
                contribution="We show it works on some apps.",
                threat_model="indirect/retrieved injection", target_venue="satml")
    report = assess(weak, corpus)
    r = refine(weak, report, exp, corpus, topic)
    assert "not-foundational" in r.resolved                 # the loop fixed a real weakness
    assert "reusable" in r.idea.contribution.lower()        # constructive graft applied
    assert r.final.overall >= r.initial.overall             # the paper improved
    assert r.directives                                     # and taught the evolution pool


def test_refine_is_noop_on_already_strong_paper():
    topic, corpus, idea, report, exp = _fixture()
    r = refine(idea, report, exp, corpus, topic)
    assert not r.final.major
    assert r.rounds == 0 or r.final.overall >= r.initial.overall


# --- skills ----------------------------------------------------------------
def test_skill_packs_present_and_ingestible(tmp_path):
    assert len(skill_files()) >= 5
    assert any("critique" in t.lower() for t in titles())
    from nyx.memory import MemoryStore
    store = MemoryStore(str(tmp_path / "mem.jsonl"))
    n = sync_skills(store)
    assert n >= 20                              # many sections ingested
    assert len(store) >= 20


# --- pipeline integration --------------------------------------------------
def test_pipeline_runs_internal_critique_before_acceptance(tmp_path):
    from darkfactory.memory import ResearchLedger
    led = ResearchLedger(str(tmp_path / "l.jsonl"))
    r = produce_paper("prompt-injection", outdir=str(tmp_path / "p"), seed=1337, ledger=led)
    assert r.critique is not None
    # Accepted papers must have cleared the internal critic (no unresolved major).
    if r.accepted:
        assert not r.critique.major
