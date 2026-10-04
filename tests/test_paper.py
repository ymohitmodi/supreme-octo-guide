"""Paper generation — the LaTeX/Markdown artifacts must be well-formed and real."""
from __future__ import annotations

from darkfactory import gates
from darkfactory.experiments import run_experiment
from darkfactory.ideas import mine_ideas
from darkfactory.ingest import corpus_for
from darkfactory.novelty import assess
from darkfactory.paper import build_latex, write_paper
from darkfactory.topics import TOPICS_BY_SLUG


def _fixture():
    topic = TOPICS_BY_SLUG["membership-inference"]
    corpus = corpus_for("membership-inference")
    idea = mine_ideas(topic, n=6)[0]
    report = assess(idea, corpus)
    exp = run_experiment(topic.slug, seed=1337)
    return idea, exp, report, corpus


def test_latex_has_required_structure_and_real_numbers():
    idea, exp, report, corpus = _fixture()
    tex = build_latex(idea, exp, report, corpus)
    for section in ("\\begin{document}", "\\begin{abstract}", "\\section{Threat Model}",
                    "\\section{Related Work}", "\\section{Results}",
                    "\\section{Ethics and Responsible Disclosure}",
                    "\\begin{thebibliography}", "\\end{document}"):
        assert section in tex
    # A real metric value from the experiment appears in the body.
    a_value = exp.table_rows[0][1]
    assert a_value in tex
    # Balanced document environment.
    assert tex.count("\\begin{document}") == 1 and tex.count("\\end{document}") == 1


def test_latex_escapes_special_characters():
    idea, exp, report, corpus = _fixture()
    idea.title = "Attack on 90% & $models$ #1"
    tex = build_latex(idea, exp, report, corpus)
    assert "90\\%" in tex and "\\&" in tex and "\\#1" in tex


def test_write_paper_emits_tex_and_markdown_and_passes_gate(tmp_path):
    idea, exp, report, corpus = _fixture()
    art = write_paper(idea, exp, report, corpus, outdir=str(tmp_path),
                      gate_check=gates.check_research)
    assert art.tex_path.endswith(".tex") and art.md_path.endswith(".md")
    from pathlib import Path
    assert Path(art.tex_path).exists() and Path(art.md_path).exists()
    # The generated paper must clear its own integrity gate.
    assert art.violations == []
    md = Path(art.md_path).read_text()
    assert "## Results" in md and exp.table_headers[0] in md
