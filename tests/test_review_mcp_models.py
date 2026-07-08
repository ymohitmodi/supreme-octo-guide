"""Conference-bar reviewer, arXiv MCP integration, and latest-model selection."""
from __future__ import annotations

import json

from darkfactory import models
from darkfactory.arxiv_mcp import MCP_SERVER_NAME, _parse_papers, search_arxiv_mcp, write_arxiv_manifest
from darkfactory.experiments import run_experiment
from darkfactory.ideas import mine_ideas
from darkfactory.ingest import corpus_for
from darkfactory.novelty import assess
from darkfactory.paper import build_latex
from darkfactory.review import review
from darkfactory.topics import TOPICS_BY_SLUG


# --- reviewer --------------------------------------------------------------
def _paper_fixture():
    topic = TOPICS_BY_SLUG["adversarial-examples"]
    corpus = corpus_for("adversarial-examples")
    idea = mine_ideas(topic, n=6)[0]
    report = assess(idea, corpus)
    exp = run_experiment("adversarial-examples", seed=1337)
    tex = build_latex(idea, exp, report, corpus)
    return idea, exp, tex


def test_thorough_paper_clears_conference_bar():
    idea, exp, tex = _paper_fixture()
    rep = review(idea, exp, tex, n_citations=3)
    assert rep.meets_bar
    assert rep.recommendation == "accept"
    assert rep.score >= 0.85


def test_missing_threat_model_fails_review():
    idea, exp, tex = _paper_fixture()
    stripped = tex.replace("\\section{Threat Model}", "\\section{Background}")
    rep = review(idea, exp, stripped, n_citations=3)
    assert not rep.meets_bar
    assert "threat_model" in rep.failed()


def test_single_condition_experiment_fails_baseline_check():
    idea, exp, tex = _paper_fixture()
    exp.table_rows = exp.table_rows[:1]   # only one condition → no baseline comparison
    rep = review(idea, exp, tex, n_citations=3)
    assert "baseline_comparison" in rep.failed()


# --- arXiv MCP -------------------------------------------------------------
def test_manifest_registers_arxiv_server(tmp_path):
    path = write_arxiv_manifest(str(tmp_path / "mcp.json"), storage=str(tmp_path / "store"))
    data = json.loads(path.read_text())
    assert MCP_SERVER_NAME in data["mcpServers"]
    assert data["mcpServers"][MCP_SERVER_NAME]["command"] == "uvx"


def test_manifest_preserves_existing_servers(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({"mcpServers": {"sec-edgar-mcp": {"command": "docker"}}}))
    write_arxiv_manifest(str(p))
    data = json.loads(p.read_text())
    assert "sec-edgar-mcp" in data["mcpServers"]  # not clobbered
    assert MCP_SERVER_NAME in data["mcpServers"]


def test_parse_papers_from_mcp_json():
    payload = json.dumps([
        {"title": "A new attack", "summary": "We do X.", "published": "2025-03-01"},
        {"title": "A defense", "abstract": "We fix X.", "date": "2024"},
    ])
    papers = _parse_papers(payload, "prompt-injection")
    assert len(papers) == 2
    assert papers[0].title == "A new attack" and papers[0].year == 2025
    assert papers[0].source == "arxiv-mcp"


def test_search_is_offline_safe_without_toolbox():
    # No ctx / toolbox → returns [] rather than crashing (curated corpus carries the run).
    assert search_arxiv_mcp(None, "prompt injection", "prompt-injection") == []


# --- latest models ---------------------------------------------------------
def test_apply_models_sets_latest_cloud_defaults():
    from nyx.config import load_config
    cfg = load_config(dotenv=False)
    models.apply_models(cfg, force=True)
    assert cfg.model_architect == models.LATEST_OLLAMA_CLOUD["architect"]
    assert cfg.model_reviewer == models.LATEST_OLLAMA_CLOUD["reviewer"]
    # The role-resolution map stays coherent with the fields.
    assert cfg.model("architect") == cfg.model_architect


def test_apply_models_respects_user_override(monkeypatch):
    from nyx.config import load_config
    monkeypatch.setenv("NYX_MODEL_ARCHITECT", "my-pinned-model:cloud")
    cfg = load_config(dotenv=False)
    models.apply_models(cfg)   # not forced
    assert cfg.model_architect == "my-pinned-model:cloud"  # user intent preserved
