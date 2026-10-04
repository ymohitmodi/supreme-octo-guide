"""Skill packs — the factory's SOTA knowledge, loaded into NYX long-term memory.

The markdown packs under ``darkfactory/skills/`` are in-depth instructive skills
(AI-security SOTA, the frontier-model lifecycle, the adversarial-critique playbook,
the conference reviewer rubric, and foundational-research heuristics). NYX's
``sync_skills`` splits each on its ``##`` sections and stores one long-term lesson
per section, so the live critic, judge, and researcher recall exactly the relevant
guidance while they work.
"""
from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def skill_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*.md"))


def sync_skills(memory) -> int:
    """Ingest the factory's skill packs into NYX long-term memory. Returns count."""
    from nyx.skills import sync_skills as nyx_sync
    return nyx_sync(memory, SKILLS_DIR)


def titles() -> list[str]:
    out = []
    for p in skill_files():
        first = p.read_text(encoding="utf-8").splitlines()[:1]
        out.append(first[0].lstrip("# ").strip() if first else p.stem)
    return out
