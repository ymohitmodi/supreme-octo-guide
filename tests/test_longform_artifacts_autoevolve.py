"""Model limits, section-wise long-form (no truncation), OSS artifacts, auto-evolve."""
from __future__ import annotations

import json
from pathlib import Path

from darkfactory.artifacts import emit_artifact
from darkfactory.autoevolve import AutoEvolver
from darkfactory.experiments import run_experiment
from darkfactory.ideas import mine_ideas
from darkfactory.longform import Section, estimate_tokens, generate_document
from darkfactory.models import DEFAULT_SPEC, MODEL_SPECS, output_budget, spec_for
from darkfactory.pipeline import produce_paper, serve
from darkfactory.topics import TOPICS_BY_SLUG


# --- model limits ----------------------------------------------------------
def test_spec_lookup_and_fallback():
    assert spec_for("glm-5.2:cloud") is MODEL_SPECS["glm-5.2:cloud"]
    assert spec_for("glm-5.2:cloud-preview").max_output == MODEL_SPECS["glm-5.2:cloud"].max_output
    assert spec_for("some-unknown-model") is DEFAULT_SPEC


def test_output_budget_clamps_to_model_ceiling():
    from nyx.config import load_config
    from darkfactory.models import apply_models
    cfg = apply_models(load_config(dotenv=False), force=True)
    ceiling = spec_for(cfg.model("architect")).max_output
    assert output_budget(cfg, "architect", want=10_000_000) == ceiling   # never exceeds host
    assert output_budget(cfg, "architect", want=512) == 512              # honors a small want
    assert output_budget(cfg, "architect", want=1) >= 256                # floor


# --- long-form (no truncation) ---------------------------------------------
def test_longform_assembles_all_sections_offline():
    secs = [Section("# Title", "", draft="Body one."),
            Section("## A", "brief-a", draft="Section A content."),
            Section("## B", "brief-b")]           # no draft → uses brief
    doc = generate_document(secs)                  # offline: deterministic
    assert "Body one." in doc.text
    assert "Section A content." in doc.text
    assert "brief-b" in doc.text                   # every section present, nothing dropped
    assert len(doc.sections) == 3
    assert not doc.truncated


def test_longform_continues_a_truncated_section_live():
    # Simulate a live provider whose first completion hits the ceiling, then finishes.
    class Comp:
        def __init__(self, text, toks):
            self.text = text
            self.completion_tokens = toks
    class FakeProvider:
        name = "fake"
        def __init__(self):
            self.calls = 0
        def chat(self, model, messages, **kw):
            self.calls += 1
            mt = kw.get("max_tokens", 4096)
            if self.calls == 1:
                return Comp("part one and then it keeps going", mt)   # looks truncated (hit ceiling)
            return Comp(" — the conclusion.", 12)                     # short → done
    import types
    cfg = types.SimpleNamespace(mock_mode=False, model=lambda r: "glm-5.2:cloud")
    ctx = types.SimpleNamespace(config=cfg, provider=FakeProvider())
    doc = generate_document([Section("# T", "write a long section", target_tokens=4096)], ctx=ctx)
    assert doc.continuations >= 1                  # it continued past the first completion
    assert "conclusion" in doc.text               # and stitched the continuation in


# --- OSS artifact bundle ---------------------------------------------------
def test_artifact_bundle_is_runnable_and_reproduces(tmp_path):
    idea = mine_ideas(TOPICS_BY_SLUG["prompt-injection"], n=6)[0]
    exp = run_experiment("prompt-injection", seed=1337)
    b = emit_artifact(idea, exp, outdir=str(tmp_path))
    root = Path(b.path)
    for name in ("experiment_kit.py", "run_benchmark.py", "metrics.json", "README.md",
                 "requirements.txt", "LICENSE"):
        assert (root / name).exists(), name
    assert b.reproduces                                        # emitted kit matches paper numbers
    metrics = json.loads((root / "metrics.json").read_text())
    assert metrics["table_rows"] == exp.table_rows
    # The vendored kit is self-contained: importing it needs no darkfactory.
    src = (root / "experiment_kit.py").read_text()
    assert "import darkfactory" not in src
    assert "run_experiment" in src


# --- auto-evolve trigger ---------------------------------------------------
class _FakeCrit:
    def __init__(self, ids):
        from darkfactory.critique import Weakness
        self.weaknesses = [Weakness(i, "soundness", "minor", "x", "y") for i in ids]

    @property
    def major(self):
        return []


class _FakeResult:
    def __init__(self, directives, weakness_ids):
        self.critique_directives = directives
        self.critique = _FakeCrit(weakness_ids)


def test_autoevolver_accumulates_and_schedules():
    ev = AutoEvolver(every=3)
    for _ in range(2):
        ev.observe(_FakeResult(["do X"], ["non-adaptive-eval"]))
        assert not ev.should_evolve()             # not yet at the schedule
    ev.observe(_FakeResult(["do Y"], ["non-adaptive-eval"]))
    assert ev.should_evolve()                     # 3rd paper + directives present
    assert "non-adaptive-eval" in ev.recurring()  # recurred 3× → a doctrine gap
    assert ev.directives == {"do X", "do Y"}


def test_autoevolve_runs_and_reports_gain():
    from nyx.config import load_config
    ev = AutoEvolver(every=1, generations=6)
    ev.observe(_FakeResult(["Evaluate against an adaptive adversary that knows it."],
                           ["non-adaptive-eval"]))
    event = ev.evolve(load_config(dotenv=False))
    assert event.score_after is not None
    assert event.at_paper == 1


def test_serve_auto_evolves_on_schedule(tmp_path):
    from darkfactory.memory import ResearchLedger
    led = ResearchLedger(str(tmp_path / "l.jsonl"))
    report = serve(topics=["prompt-injection"], outdir=str(tmp_path / "p"),
                   max_papers=2, ledger=led, auto_evolve_every=2)
    assert report.artifacts >= 1                  # accepted papers shipped OSS artifacts
    assert report.auto_evolver is not None
    assert report.auto_evolver.events             # an evolution round fired on schedule


def test_pipeline_emits_artifact_for_accepted_paper(tmp_path):
    from darkfactory.memory import ResearchLedger
    led = ResearchLedger(str(tmp_path / "l.jsonl"))
    r = produce_paper("prompt-injection", outdir=str(tmp_path / "p"), seed=1337, ledger=led)
    if r.accepted:
        assert r.artifact_bundle is not None and r.artifact_bundle.reproduces
    assert estimate_tokens("x" * 400) == 100      # token estimate sanity
