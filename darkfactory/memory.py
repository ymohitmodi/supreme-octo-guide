"""Offline compounding memory — the research ledger that makes quality compound.

Every accepted paper is recorded as a durable :class:`Contribution` on disk
(``.darkfactory/contributions.jsonl``), with a lineage of what it *builds on*
(prior contributions of this factory + the external SOTA it cites). Because the
ledger survives across runs, each research cycle stands on the accumulated body
of work instead of starting cold — the compounding loop the user asked for.

Two mechanisms turn accumulation into *rising* quality:

1. **Build-on lineage** — new ideas extend the most impactful prior contribution
   on a topic (see ``ideas.extend_idea``), so contributions form a deepening
   chain rather than a flat pile.
2. **Ratcheting bar** — the novelty/impact bar a paper must clear rises with the
   factory's accumulated *research capital*, so later cycles must be more
   impactful than earlier ones to be accepted. The ratchet is bounded so the
   factory keeps producing while trending upward.

This is deliberately separate from NYX's semantic ``MemoryStore`` (which holds
doctrine + track record). The ledger is the *structured* record of shipped
contributions and their dependency graph; both persist offline.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_LEDGER = ".darkfactory/contributions.jsonl"

# Bar ratchet: base novelty bar, how fast it climbs with capital, and its cap.
BASE_BAR = 0.62
BAR_CAP = 0.80
CAPITAL_SCALE = 12.0        # capital units for a full climb toward the cap


@dataclass
class Contribution:
    id: str
    cycle: int
    topic: str
    title: str
    idea_id: str
    venue: str
    novelty: float
    impact: float
    fitness: float
    result_headline: str
    builds_on: list[str] = field(default_factory=list)      # prior contribution ids
    cites: list[str] = field(default_factory=list)          # external SOTA titles
    artifact: str = ""
    depth: int = 0                                          # lineage depth (compounding)
    ts: float = field(default_factory=time.time)

    @property
    def impact_score(self) -> float:
        """A contribution's standalone worth, amplified by how deep its lineage is
        (building on prior work compounds impact)."""
        return round(self.fitness * (1.0 + 0.15 * self.depth), 4)


class ResearchLedger:
    """Append-only, offline record of shipped contributions + their lineage."""

    def __init__(self, path: str = DEFAULT_LEDGER):
        self.path = Path(path)
        self._items: list[Contribution] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self._items.append(Contribution(**json.loads(line)))
            except (ValueError, TypeError):
                continue

    def add(self, contribution: Contribution) -> Contribution:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(contribution)) + "\n")
        self._items.append(contribution)
        return contribution

    # -- queries -------------------------------------------------------------
    def all(self) -> list[Contribution]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def for_topic(self, topic: str) -> list[Contribution]:
        return [c for c in self._items if c.topic == topic]

    def latest(self, n: int = 5) -> list[Contribution]:
        return sorted(self._items, key=lambda c: c.ts, reverse=True)[:n]

    def best_for_topic(self, topic: str) -> Contribution | None:
        items = self.for_topic(topic)
        return max(items, key=lambda c: c.impact_score) if items else None

    def next_cycle(self) -> int:
        return (max((c.cycle for c in self._items), default=0)) + 1

    def lineage(self, contribution_id: str) -> list[Contribution]:
        by_id = {c.id: c for c in self._items}
        chain, cur = [], by_id.get(contribution_id)
        seen = set()
        while cur and cur.id not in seen:
            seen.add(cur.id)
            chain.append(cur)
            parent = cur.builds_on[0] if cur.builds_on else None
            cur = by_id.get(parent) if parent else None
        return chain

    # -- compounding metrics -------------------------------------------------
    def research_capital(self) -> float:
        """Accumulated impact across all contributions, rewarding depth (compounding).

        Sum of impact scores; because ``impact_score`` grows with lineage depth,
        a chain of papers that build on each other is worth more than the same
        number of isolated papers."""
        return round(sum(c.impact_score for c in self._items), 4)

    def current_bar(self) -> float:
        """The novelty bar this cycle must clear — rises with research capital."""
        capital = self.research_capital()
        climb = (BAR_CAP - BASE_BAR) * (1.0 - math.exp(-capital / CAPITAL_SCALE))
        return round(min(BAR_CAP, BASE_BAR + climb), 4)

    def summary(self) -> str:
        n = len(self._items)
        depth = max((c.depth for c in self._items), default=0)
        lines = [
            f"Research ledger: {n} contributions, capital={self.research_capital():.2f}, "
            f"max lineage depth={depth}, next bar={self.current_bar():.3f}",
        ]
        for c in self.latest(8):
            chain = " → ".join(reversed([x.title[:28] for x in self.lineage(c.id)]))
            lines.append(f"  #{c.cycle:03d} [{c.topic}] nov={c.novelty:.2f} depth={c.depth}"
                         f"  {c.title[:52]}")
            if c.depth:
                lines.append(f"        builds on: {chain}")
        return "\n".join(lines)
