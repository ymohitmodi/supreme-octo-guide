"""Research-integrity gates — the values a publication must not violate.

Four domain rules the factory enforces before a paper ships, exposed as (a) plain
functions callable anywhere and (b) extra ``forbidden`` lines grafted onto NYX's
Constitution so its ``check_forbidden`` enforces them too:

1. **No fabricated results** — every quantitative claim must trace to a reported
   experiment (a table/figure/metric the factory actually ran).
2. **Related work required** — a contribution claim without positioning against
   prior art is rejected (that is what the bar-raiser produced; it must appear).
3. **Reproducibility required** — the paper must state seed/code/benchmark so the
   numbers can be reproduced.
4. **Responsible disclosure** — any offensive framing must be paired with a
   defense and an ethics/disclosure statement.

These make integrity mechanical, not aspirational.
"""
from __future__ import annotations

import re

_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%|\b0?\.\d+\b|\b\d+(?:\.\d+)?x\b", re.IGNORECASE)
_RESULT_SOURCE_RE = re.compile(
    r"\b(table|figure|fig\.|experiment|benchmark|we (?:measure|observe|report|find)|"
    r"results? show|our evaluation)\b", re.IGNORECASE)
_RELATED_RE = re.compile(
    r"\b(related work|prior (?:art|work)|compared? (?:to|with)|baseline|"
    r"differs? from|unlike (?:prior|existing)|\bet al\.)\b", re.IGNORECASE)
_REPRO_RE = re.compile(
    r"\b(seed|reproduc|released? code|open[- ]source|artifact|benchmark spec|"
    r"code (?:is|will be) available)\b", re.IGNORECASE)
_OFFENSE_RE = re.compile(
    r"\b(attack|exploit|jailbreak|poison|evasion|extraction|bypass|backdoor)\b",
    re.IGNORECASE)
_DEFENSE_RE = re.compile(
    r"\b(defense|defence|mitigation|detect|responsible disclosure|ethics|"
    r"we disclosed|countermeasure|hardening)\b", re.IGNORECASE)

RESEARCH_FORBIDDEN = [
    "fabricate experimental results",
    "plagiarize prior work",
    "publish an offensive attack without a defense and responsible disclosure",
]


def has_unsourced_results(text: str) -> bool:
    """True if the text states several quantitative results with no experimental source."""
    numbers = len(_NUMBER_RE.findall(text))
    return numbers >= 3 and not _RESULT_SOURCE_RE.search(text)


def lacks_related_work(text: str) -> bool:
    return not _RELATED_RE.search(text)


def lacks_reproducibility(text: str) -> bool:
    return not _REPRO_RE.search(text)


def offense_without_defense(text: str) -> bool:
    """True if the paper frames offense but never a defense / disclosure."""
    return bool(_OFFENSE_RE.search(text)) and not _DEFENSE_RE.search(text)


def check_research(text: str) -> list[str]:
    """Return research-integrity violations for a paper artifact."""
    v: list[str] = []
    if has_unsourced_results(text):
        v.append("G_SOURCED_RESULTS: quantitative claims not traced to a reported experiment")
    if lacks_related_work(text):
        v.append("G_RELATED_WORK: contribution not positioned against prior art")
    if lacks_reproducibility(text):
        v.append("G_REPRODUCIBILITY: no seed/code/benchmark for the reported numbers")
    if offense_without_defense(text):
        v.append("G_RESPONSIBLE_DISCLOSURE: offensive framing without a defense/disclosure")
    return v


def add_research_forbidden(const):
    """Append the research-integrity forbidden rules to a constitution (idempotent)."""
    for line in RESEARCH_FORBIDDEN:
        if line not in const.forbidden:
            const.forbidden.append(line)
    return const


def research_constitution(path: str | None = None, mode: str = "block"):
    """Load NYX's base constitution and add the research-integrity forbidden rules.

    Falls back to an empty base constitution when the YAML is not on disk (e.g.
    running standalone outside a NYX checkout), so the research gates are always
    available. Under the CapabilityRunner the loaded base is passed in instead.
    """
    from nyx.config import load_config
    from nyx.constitution import Constitution

    cfg = load_config()
    try:
        const = Constitution.load(path or cfg.constitution_path, mode=mode)
    except (FileNotFoundError, OSError):
        const = Constitution({}, mode=mode)
    return add_research_forbidden(const)
