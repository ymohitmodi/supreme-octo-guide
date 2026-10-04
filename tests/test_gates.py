"""Research-integrity gates — the constitution for publications."""
from __future__ import annotations

from darkfactory import gates


def test_clean_paper_passes():
    text = (
        "We evaluate against prior work and baselines (Smith et al.). Table 1 shows "
        "our detector reaches 0.92 F1. We release code and a fixed seed for "
        "reproducibility. We pair the attack with a defense and follow responsible "
        "disclosure.")
    assert gates.check_research(text) == []


def test_unsourced_numbers_are_flagged():
    text = ("Our method achieves 0.95 accuracy, 0.90 precision, and a 3x speedup. "
            "It compares to prior work and releases code with a seed and a defense.")
    v = gates.check_research(text)
    assert any("G_SOURCED_RESULTS" in x for x in v)


def test_missing_related_work_is_flagged():
    text = ("Table 1 reports our results with a released seed and code, plus a "
            "defense and responsible disclosure.")
    assert any("G_RELATED_WORK" in x for x in gates.check_research(text))


def test_missing_reproducibility_is_flagged():
    text = ("Compared to prior work, Table 1 shows strong numbers. We include a "
            "defense and responsible disclosure.")
    assert any("G_REPRODUCIBILITY" in x for x in gates.check_research(text))


def test_offense_without_defense_is_flagged():
    text = ("We present a new jailbreak attack that bypasses safety training. "
            "Compared to prior work, Table 1 shows it works. Code and seed released.")
    assert any("G_RESPONSIBLE_DISCLOSURE" in x for x in gates.check_research(text))


def test_constitution_adds_forbidden_rules():
    const = gates.research_constitution()
    for line in gates.RESEARCH_FORBIDDEN:
        assert line in const.forbidden
