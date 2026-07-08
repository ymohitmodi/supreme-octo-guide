"""The Researcher role — the genome the dark factory evolves.

NYX evolves *agent genomes* (charters + params) against a benchmark. The factory
adds one role, ``researcher``, whose charter is the doctrine the EvolutionEngine
mutates and selects: a genome that encodes stronger research methodology (novelty
seeking, adaptive evaluation, reproducibility, responsible disclosure) mines
higher-fitness ideas and so wins selection.

We register the role into NYX's ``ROLE_REGISTRY`` at import so ``build_agent(
"researcher", ...)`` works everywhere the engine needs it — the same extension
pattern NYX uses for its own roles.
"""
from __future__ import annotations

from nyx.agents.base import Agent
from nyx.agents.roles import ROLE_REGISTRY

RESEARCHER_CHARTER = (
    "You are the AI-Security Researcher — a bar-raising scientist who produces "
    "novel, high-impact, reproducible contributions to AI security. Mine ideas that "
    "go beyond the public prior art of the target venue; state a precise threat model; "
    "prefer adaptive-adversary and certified evaluation over fixed test sets; control "
    "for benchmark contamination and report confidence intervals. Never fabricate "
    "numbers, citations, or results — every claim must be reproducible from released "
    "code and a fixed seed. Lead offensive findings with a defense and follow "
    "responsible disclosure. Contributions must raise the security of the ecosystem."
)


class ResearcherAgent(Agent):
    default_model_role = "architect"
    charter = RESEARCHER_CHARTER


def register_role() -> None:
    """Idempotently register the researcher role into NYX's registry."""
    ROLE_REGISTRY.setdefault("researcher", ResearcherAgent)


register_role()
