"""Dark Factory — an autonomous, self-evolving AI-security research team.

A NYX *capability* that researches AI security around the clock, mines and
validates novel ideas against the public prior art of top venues, runs real
benchmarks, and writes conference-grade LaTeX/PDF papers — every publication
gated by a strict novelty bar-raiser and research-integrity constitution.

Importing this package registers the capability and the ``researcher`` role into
NYX, so ``nyx run "publish AI security research"`` routes here automatically.
"""
from __future__ import annotations

__version__ = "0.1.0"

from . import roles  # noqa: F401 — registers the researcher role on import
from .capability import AISecurityResearchCapability
from .critique import critique
from .ideas import Idea, extend_idea, mine_ideas
from .knowledge import sync_skills
from .memory import Contribution, ResearchLedger
from .models import apply_models
from .novelty import assess
from .pipeline import PaperResult, produce_paper, serve
from .refine import refine
from .review import review
from .topics import TOPICS, seed_doctrine


def register() -> None:
    """Register the capability into NYX's registry (idempotent)."""
    from nyx.capabilities.registry import register as nyx_register
    try:
        nyx_register(AISecurityResearchCapability)
    except Exception:  # noqa: BLE001 — registration must never crash import
        pass


register()

__all__ = [
    "__version__",
    "AISecurityResearchCapability",
    "produce_paper",
    "serve",
    "PaperResult",
    "mine_ideas",
    "extend_idea",
    "assess",
    "review",
    "critique",
    "refine",
    "sync_skills",
    "Idea",
    "Contribution",
    "ResearchLedger",
    "apply_models",
    "TOPICS",
    "seed_doctrine",
    "register",
]
