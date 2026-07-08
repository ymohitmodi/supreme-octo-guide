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

# Role -> latest recommended Ollama Cloud model tag (highest accuracy first).
LATEST_OLLAMA_CLOUD = {
    "architect": "glm-5.2:cloud",          # deep reasoning: idea mining + paper writing
    "coder": "glm-5.2:cloud",              # benchmark/harness code
    "reviewer": "deepseek-v4-pro:cloud",   # strict bar-raiser + thoroughness review
    "fast": "qwen3.5:cloud",               # routing, scoring, short judgments
    "embed": "nomic-embed-text",           # semantic memory embeddings
}

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
