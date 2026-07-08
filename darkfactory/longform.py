"""Long-form generation — build artifacts longer than a single completion.

Frontier cloud models read ~1M tokens but *emit* far less per call (a single
completion reliably returns ~8-16k tokens, not the whole context). A real paper or
a released code repo is longer than that. So we never ask for a whole artifact in
one shot: we generate it **section by section**, each in its own budgeted
completion, and if a single section is itself long we **continue** it until it
completes — so total length is unbounded by any one call and nothing is silently
truncated.

Offline / mock mode is fully deterministic: each section renders from its provided
draft (or brief), so the whole machine is testable without a brain. Live, each
section is written at length by the model, bounded by the model's real output
ceiling (see ``models.output_budget``).
"""
from __future__ import annotations

from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """~4 chars per token — good enough for budgeting."""
    return max(1, len(text) // 4)


@dataclass
class Section:
    title: str
    brief: str                       # what this section must contain (the prompt)
    draft: str = ""                  # deterministic content used offline / in mock
    target_tokens: int = 1200        # desired length for this section (live)


@dataclass
class LongformResult:
    text: str
    sections: list = field(default_factory=list)     # (title, text)
    calls: int = 0
    continuations: int = 0
    truncated: bool = False          # True if a hard cap stopped a still-growing section

    def tokens(self) -> int:
        return estimate_tokens(self.text)


def _is_truncated(completion, requested: int) -> bool:
    """Infer truncation: the model hit (near) the output ceiling for this call."""
    got = getattr(completion, "completion_tokens", 0) or 0
    if got and got >= requested - 32:
        return True
    text = (getattr(completion, "text", "") or "").rstrip()
    # No terminal punctuation → very likely cut mid-thought.
    return bool(text) and text[-1] not in ".!?}\n)`\"'"


def _generate_section_live(section: Section, ctx, role: str, system: str,
                           max_continuations: int) -> tuple[str, int, int, bool]:
    from nyx.providers.base import ChatMessage
    from .models import output_budget

    cfg, provider = ctx.config, ctx.provider
    requested = output_budget(cfg, role, section.target_tokens)
    messages = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=section.brief))
    parts: list[str] = []
    calls = continuations = 0
    truncated = False
    for step in range(max_continuations + 1):
        comp = provider.chat(cfg.model(role), messages, temperature=0.4, max_tokens=requested)
        calls += 1
        chunk = comp.text or ""
        parts.append(chunk)
        if not _is_truncated(comp, requested):
            break
        if step == max_continuations:
            truncated = True
            break
        continuations += 1
        # Ask to continue exactly where it stopped, without repeating.
        messages.append(ChatMessage(role="assistant", content=chunk))
        messages.append(ChatMessage(role="user",
                                    content="Continue exactly where you stopped. Do not repeat."))
    return "".join(parts).strip(), calls, continuations, truncated


def generate_document(sections: list[Section], ctx=None, *, role: str = "architect",
                      system: str = "", max_continuations: int = 4) -> LongformResult:
    """Generate a multi-section document, each section bounded and continued as needed."""
    live = (ctx is not None and getattr(ctx, "provider", None) is not None
            and not getattr(getattr(ctx, "config", None), "mock_mode", True))
    out_sections: list[tuple[str, str]] = []
    calls = conts = 0
    truncated = False
    for sec in sections:
        if live:
            body, c, k, t = _generate_section_live(sec, ctx, role, system, max_continuations)
            calls += c
            conts += k
            truncated = truncated or t
            if not body:                       # live returned nothing → fall back
                body = sec.draft or sec.brief
        else:
            body = sec.draft or sec.brief      # deterministic offline
        out_sections.append((sec.title, body))
    text = "\n\n".join(f"{title}\n{body}" if title else body for title, body in out_sections)
    return LongformResult(text=text, sections=out_sections, calls=calls,
                          continuations=conts, truncated=truncated)
