"""Latest Ollama Cloud models — highest accuracy for autonomous research.

Ollama Cloud runs frontier open-weight models server-side, so a GPU-less mini-PC
only orchestrates. As of mid-2026 the accuracy leaders are GLM-5.2 (top of the
Artificial Analysis Intelligence Index and SWE-Bench Pro) and DeepSeek-V4-Pro
(reasoning). We default the research roles to these and keep a fast model for
routing/scoring. Everything is overridable via the same ``NYX_MODEL_*`` env vars
NYX reads, so operators can pin whatever their account can call.

``apply_models(cfg)`` upgrades a NYX ``Config`` to these defaults **without**
clobbering an explicit user override (env var or a value already different from
NYX's own placeholder defaults).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Role -> latest recommended Ollama Cloud model tag (highest accuracy first).
LATEST_OLLAMA_CLOUD = {
    "architect": "glm-5.2:cloud",          # deep reasoning: idea mining + paper writing
    "coder": "glm-5.2:cloud",              # benchmark/harness code
    "reviewer": "deepseek-v4-pro:cloud",   # strict bar-raiser + thoroughness review
    "fast": "qwen3.5:cloud",               # routing, scoring, short judgments
    "embed": "nomic-embed-text",           # semantic memory embeddings
}


@dataclass(frozen=True)
class ModelSpec:
    """Capacity of a model: how much it can read (context) and write (output).

    ``context_window`` is total tokens in ⇄ out; ``max_output`` is the largest
    single completion. These frontier cloud models take ~1M-token context, but the
    single-completion output is far smaller — which is exactly why long artifacts
    (papers, code repos) must be generated section-by-section (see longform.py) and
    never in one shot. Values are conservative, honest defaults for what a single
    Ollama-Cloud completion reliably returns; override via env if your host differs.
    """
    context_window: int
    max_output: int


# Studied capacities (mid-2026). Context windows are ~1M for the frontier models;
# we cap the *working* context we actually fill (well under the max) and the
# single-completion output to values the serving layer reliably returns.
MODEL_SPECS: dict[str, ModelSpec] = {
    "glm-5.2:cloud": ModelSpec(context_window=1_000_000, max_output=16_384),
    "deepseek-v4-pro:cloud": ModelSpec(context_window=1_000_000, max_output=16_384),
    "deepseek-v4-flash:cloud": ModelSpec(context_window=1_000_000, max_output=16_384),
    "qwen3.5:cloud": ModelSpec(context_window=262_144, max_output=8_192),
    "kimi-k2.6:cloud": ModelSpec(context_window=262_144, max_output=16_384),
}
# Safe fallback for any unlisted model: assume a modest window + output so we
# chunk conservatively rather than truncate.
DEFAULT_SPEC = ModelSpec(context_window=32_768, max_output=4_096)

# The working context we are willing to fill for a prompt (leaves headroom for the
# model's own reasoning + output within the real window). Bounded so we never rely
# on the full million tokens, which degrades quality and latency.
WORKING_CONTEXT_TOKENS = 96_000


def spec_for(model: str) -> ModelSpec:
    key = model.strip()
    if key in MODEL_SPECS:
        return MODEL_SPECS[key]
    # Match by family prefix (e.g. "glm-5.2:cloud-preview").
    for name, spec in MODEL_SPECS.items():
        if key.startswith(name.split(":")[0]):
            return spec
    return DEFAULT_SPEC


def output_budget(cfg, role: str, want: int | None = None) -> int:
    """Max tokens to request for one completion of ``role`` — bounded by the model.

    ``want`` is the desired length; the result is clamped to the model's single-
    completion ceiling so a call never asks for more than the host will return
    (which would silently truncate). Long artifacts loop over sections instead.
    """
    spec = spec_for(cfg.model(role) if hasattr(cfg, "model") else role)
    ceiling = spec.max_output
    return max(256, min(want or ceiling, ceiling))


def context_budget_chars(cfg, role: str) -> int:
    """Approximate char budget for a prompt to ``role`` (~4 chars/token)."""
    spec = spec_for(cfg.model(role) if hasattr(cfg, "model") else role)
    tokens = min(spec.context_window, WORKING_CONTEXT_TOKENS)
    # Reserve ~1/3 of the working window for the model's output/reasoning.
    return int(tokens * 4 * 0.66)

# NYX's own placeholder defaults — safe to overwrite (they are not user intent).
_NYX_PLACEHOLDERS = {
    "qwen3.5-coder:480b-cloud", "glm-5.1:cloud", "gemma4:cloud", "nomic-embed-text",
}
_ENV_FOR_ROLE = {
    "architect": "NYX_MODEL_ARCHITECT", "coder": "NYX_MODEL_CODER",
    "reviewer": "NYX_MODEL_REVIEWER", "fast": "NYX_MODEL_FAST", "embed": "NYX_MODEL_EMBED",
}


def apply_models(cfg, force: bool = False):
    """Set the latest Ollama Cloud model defaults on a NYX Config in place.

    A role is upgraded only when the user hasn't expressed intent — i.e. no
    ``NYX_MODEL_*`` env var is set for it and its current value is a NYX
    placeholder — unless ``force=True``.
    """
    current = {
        "architect": cfg.model_architect, "coder": cfg.model_coder,
        "reviewer": cfg.model_reviewer, "fast": cfg.model_fast, "embed": cfg.model_embed,
    }
    for role, latest in LATEST_OLLAMA_CLOUD.items():
        user_set = bool(os.environ.get(_ENV_FOR_ROLE[role]))
        if force or (not user_set and current[role] in _NYX_PLACEHOLDERS):
            setattr(cfg, f"model_{role}", latest)
    # Keep the role→model resolution map coherent with the fields we just set.
    cfg.model_for_role = {
        "architect": cfg.model_architect, "coder": cfg.model_coder,
        "reviewer": cfg.model_reviewer, "fast": cfg.model_fast,
    }
    return cfg


def env_block() -> str:
    """A ready-to-paste .env snippet pinning the latest cloud models."""
    lines = ["# Latest Ollama Cloud models (highest accuracy). Adjust to your account."]
    for role, env in _ENV_FOR_ROLE.items():
        lines.append(f"{env}={LATEST_OLLAMA_CLOUD[role]}")
    return "\n".join(lines)
