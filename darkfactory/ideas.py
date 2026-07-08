"""Idea mining — the dark factory's generative core.

An :class:`Idea` is a candidate contribution: a hypothesis, an approach, the
claimed novelty, and a target venue. Ideas are *mined* continuously, *scored*
(novelty/impact/feasibility/rigor), *revised* toward the bar, and the strongest
survive to become papers — Darwinian selection over research directions.

Live, the miner asks the model to propose ideas grounded in the recalled prior
art and the topic's threat models. Offline, it recombines the topic's threat
models × methods × assets deterministically, so CI mines reproducible ideas
without a brain. Either way the *scoring* and *bar-raiser* (novelty.py) are what
decide which survive — generation is cheap, selection is strict.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from dataclasses import dataclass, field

from .conferences import primary_venue
from .topics import Topic

# Weights for the composite fitness of a research idea. Novelty and impact
# dominate (a paper must say something new that matters); feasibility and rigor
# gate whether the factory can actually execute and defend it.
FITNESS_WEIGHTS = {"novelty": 0.40, "impact": 0.30, "feasibility": 0.15, "rigor": 0.15}


@dataclass
class Idea:
    id: str
    topic: str
    title: str
    hypothesis: str
    approach: str
    contribution: str
    threat_model: str
    target_venue: str
    novelty: float = 0.0
    impact: float = 0.0
    feasibility: float = 0.0
    rigor: float = 0.0
    generation: int = 0
    nearest_prior: list[str] = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)
    revisions: list[str] = field(default_factory=list)

    @property
    def fitness(self) -> float:
        return round(
            FITNESS_WEIGHTS["novelty"] * self.novelty
            + FITNESS_WEIGHTS["impact"] * self.impact
            + FITNESS_WEIGHTS["feasibility"] * self.feasibility
            + FITNESS_WEIGHTS["rigor"] * self.rigor,
            4,
        )

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["fitness"] = self.fitness
        return d


def _idea_id(topic: str, title: str) -> str:
    return "idea-" + hashlib.sha1(f"{topic}|{title}".encode()).hexdigest()[:10]


# ---------------------------------------------------------------------------
# Deterministic offline miner: recombine the topic's primitives into concrete,
# venue-shaped research directions. These read like real submissions, not
# templates, because the primitives encode the actual research frontier.
# ---------------------------------------------------------------------------
_FRAMES = (
    ("Certifying {asset} under {threat}",
     "A {method} defense yields a *provable* bound on {asset} against a {threat} adversary.",
     "We hypothesize that {method} gives a certificate for {asset} that holds under "
     "adaptive {threat}, not just the fixed test distribution.",
     "Formalize the threat, derive a certificate via {method}, and evaluate the "
     "clean/robust trade-off against adaptive attacks.",
     "First certified bound on {asset} for the {threat} threat model with an "
     "adaptive-attack evaluation."),
    ("Adaptive-adversary evaluation of {method} for {asset}",
     "Existing {method} defenses of {asset} overstate robustness because they are not "
     "evaluated against an adversary that knows the defense.",
     "We hypothesize that a compute-matched adaptive attack collapses reported "
     "{method} robustness for {asset} by a large margin.",
     "Build an adaptive attack targeting {method}, re-evaluate published defenses, and "
     "release a contamination-controlled benchmark.",
     "A reusable adaptive-evaluation protocol and benchmark that separates real "
     "{asset} robustness from gradient masking."),
    ("Provenance-aware defense against {threat}",
     "Tracking the provenance of every input lets a system contain {threat} without "
     "degrading utility on {asset}.",
     "We hypothesize that {method} with per-input provenance detects {threat} at a "
     "false-positive rate low enough for deployment.",
     "Instrument inputs with provenance, train a {method} detector, and measure "
     "detection vs utility on unseen payloads.",
     "A provenance-aware {method} defense for {threat} evaluated on out-of-distribution "
     "attacks, with an open detector."),
    ("Measuring the cost of {threat} on {asset}",
     "The right defense metric for {threat} is the *cost* an adversary must pay, not "
     "binary feasibility of attacking {asset}.",
     "We hypothesize that {method} raises the adversary's query/compute cost for "
     "{threat} by orders of magnitude while preserving {asset}.",
     "Define a cost model, implement {method}, and empirically trace attacker cost "
     "vs defender utility across budgets.",
     "A cost-based evaluation methodology for {threat} and a {method} defense that "
     "shifts the attacker's cost curve."),
)


def _mine_offline(topic: Topic, n: int, generation: int = 0, variant: int = 0) -> list[Idea]:
    ideas: list[Idea] = []
    combos = list(itertools.product(topic.threat_models, topic.methods, topic.assets))
    # Rotate the combo + frame ordering by `variant` so successive runs on the same
    # topic (24/7 production) explore different threat×method×frame directions
    # rather than re-mining the same idea, while staying fully deterministic.
    start = variant % len(combos)
    combos = combos[start:] + combos[:start]
    frames = _FRAMES[variant % len(_FRAMES):] + _FRAMES[:variant % len(_FRAMES)]
    venue = primary_venue(topic.slug).slug
    for (threat, method, asset), frame in zip(combos, itertools.cycle(frames)):
        title_t, hyp_t, hh_t, appr_t, contrib_t = frame
        subs = {"threat": threat, "method": method, "asset": asset}
        title = title_t.format(**subs)
        idea = Idea(
            id=_idea_id(topic.slug, title),
            topic=topic.slug,
            title=title,
            hypothesis=hh_t.format(**subs),
            approach=appr_t.format(**subs),
            contribution=contrib_t.format(**subs),
            threat_model=threat,
            target_venue=venue,
            generation=generation,
        )
        ideas.append(idea)
        if len(ideas) >= n:
            break
    return ideas


# ---------------------------------------------------------------------------
# Live miner: ask the brain for grounded, novel directions. Falls back to the
# offline miner on mock mode or any parse failure.
# ---------------------------------------------------------------------------
def _mine_live(topic: Topic, n: int, ctx, prior_titles: list[str], generation: int) -> list[Idea]:
    from nyx.providers.base import ChatMessage

    provider, config = ctx.provider, ctx.config
    prior = "\n".join(f"- {t}" for t in prior_titles[:15]) or "(none provided)"
    lessons = "\n".join(f"- {l}" for l in (ctx.lessons or [])[:8])
    prompt = (
        "You are a bar-raising AI-security researcher mining NOVEL, high-impact paper "
        f"ideas for topic: {topic.name}.\n\n"
        f"THREAT MODELS: {', '.join(topic.threat_models)}\n"
        f"METHODS: {', '.join(topic.methods)}\n"
        f"ASSETS AT RISK: {', '.join(topic.assets)}\n\n"
        f"KNOWN PRIOR ART (do NOT restate these — go beyond them):\n{prior}\n\n"
        f"RECALLED DOCTRINE:\n{lessons}\n\n"
        f"Propose {n} ideas that a top venue would consider novel. Reply as a JSON array; "
        "each item: {\"title\":..., \"threat_model\":..., \"hypothesis\":..., "
        "\"approach\":..., \"contribution\":...}. JSON only."
    )
    try:
        out = provider.chat(config.model("architect"),
                            [ChatMessage(role="user", content=prompt)],
                            temperature=0.7, max_tokens=1200).text
        arr = _extract_json_array(out)
        venue = primary_venue(topic.slug).slug
        ideas: list[Idea] = []
        for item in arr[:n]:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            ideas.append(Idea(
                id=_idea_id(topic.slug, title), topic=topic.slug, title=title,
                hypothesis=str(item.get("hypothesis", "")).strip(),
                approach=str(item.get("approach", "")).strip(),
                contribution=str(item.get("contribution", "")).strip(),
                threat_model=str(item.get("threat_model", topic.threat_models[0])).strip(),
                target_venue=venue, generation=generation,
            ))
        if ideas:
            return ideas
    except Exception:  # noqa: BLE001 — generation must never crash a run
        pass
    return _mine_offline(topic, n, generation)


def _extract_json_array(text: str):
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _extract_json_object(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


def mine_ideas(topic: Topic, n: int = 6, ctx=None, prior_titles: list[str] | None = None,
               generation: int = 0, variant: int = 0) -> list[Idea]:
    """Mine ``n`` candidate ideas for a topic (live when a brain is available)."""
    if ctx is not None and getattr(ctx, "provider", None) is not None \
            and not getattr(ctx.config, "mock_mode", True):
        return _mine_live(topic, n, ctx, prior_titles or [], generation)
    return _mine_offline(topic, n, generation, variant=variant)


def revise_idea(idea: Idea, reason: str, topic: Topic, ctx=None) -> Idea:
    """Iterate an idea toward the bar: sharpen novelty by pivoting the frame.

    Deterministic offline (rotate to a less-explored threat×method combo and note
    the revision); live, ask the brain to differentiate from the nearest prior art.
    """
    generation = idea.generation + 1
    if ctx is not None and getattr(ctx, "provider", None) is not None \
            and not getattr(ctx.config, "mock_mode", True):
        revised = _revise_live(idea, reason, topic, ctx)
        if revised is not None:
            revised.lineage = idea.lineage + [idea.id]
            revised.revisions = idea.revisions + [reason]
            revised.generation = generation
            return revised
    # Offline pivot: pick the next frame + a rotated threat model to differentiate.
    pool = _mine_offline(topic, n=len(topic.threat_models) * 2, generation=generation)
    for cand in pool:
        if cand.title != idea.title and cand.id not in idea.lineage:
            cand.lineage = idea.lineage + [idea.id]
            cand.revisions = idea.revisions + [reason]
            return cand
    idea.generation = generation
    idea.revisions = idea.revisions + [reason]
    return idea


def _revise_live(idea: Idea, reason: str, topic: Topic, ctx) -> Idea | None:
    from nyx.providers.base import ChatMessage

    prior = "\n".join(f"- {t}" for t in idea.nearest_prior[:6]) or "(unknown)"
    prompt = (
        "Revise this AI-security research idea to raise its NOVELTY against the nearest "
        f"prior art. Reason it fell short: {reason}\n\n"
        f"IDEA: {idea.title}\nHYPOTHESIS: {idea.hypothesis}\nAPPROACH: {idea.approach}\n"
        f"NEAREST PRIOR ART:\n{prior}\n\n"
        "Return JSON: {\"title\":..., \"hypothesis\":..., \"approach\":..., "
        "\"contribution\":...}. Differentiate sharply. JSON only."
    )
    try:
        out = ctx.provider.chat(ctx.config.model("architect"),
                                [ChatMessage(role="user", content=prompt)],
                                temperature=0.6, max_tokens=800).text
        obj = _extract_json_object(out)
        if not obj:
            return None
        title = str(obj.get("title", idea.title)).strip()
        return Idea(
            id=_idea_id(topic.slug, title), topic=topic.slug, title=title,
            hypothesis=str(obj.get("hypothesis", idea.hypothesis)).strip(),
            approach=str(obj.get("approach", idea.approach)).strip(),
            contribution=str(obj.get("contribution", idea.contribution)).strip(),
            threat_model=idea.threat_model, target_venue=idea.target_venue,
        )
    except Exception:  # noqa: BLE001
        return None
