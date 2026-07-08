"""arXiv MCP server integration — SOTA ingestion + citation graph.

Reuses NYX's MCP support (``nyx.tools.mcp``): once the arxiv-mcp-server is in the
manifest, NYX's toolbox exposes it as the proxy tool ``mcp.arxiv-mcp-server`` and
this capability is already allowed ``mcp.*``. We call its ``search_papers`` to
pull SOTA and ``citation_graph`` (its ``[pro]`` extra) to find the exact prior
work each new paper should build on — the backbone of compounding research.

Server: https://github.com/blazickjp/arxiv-mcp-server

    uv tool install "arxiv-mcp-server[pro]"
    # launched by NYX via the manifest below (uvx / stdio)

Everything here is best-effort and offline-safe: if the server, uv, or the tool
call is unavailable, functions return empty and the curated corpus carries the
run.
"""
from __future__ import annotations

import json
from pathlib import Path

from .ingest import Paper

MCP_SERVER_NAME = "arxiv-mcp-server"
MCP_TOOL = f"mcp.{MCP_SERVER_NAME}"


def write_arxiv_manifest(path: str | Path, storage: str = ".darkfactory/arxiv") -> Path:
    """Add/update the arxiv-mcp-server in a NYX MCP manifest (preserving others)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    Path(storage).mkdir(parents=True, exist_ok=True)
    manifest = {"mcpServers": {}}
    if p.exists():
        try:
            existing = json.loads(p.read_text(encoding="utf-8"))
            manifest["mcpServers"] = existing.get("mcpServers", existing) or {}
        except (ValueError, OSError):
            manifest = {"mcpServers": {}}
    manifest["mcpServers"][MCP_SERVER_NAME] = {
        "command": "uvx",
        "args": ["arxiv-mcp-server", "--storage-path", str(Path(storage).resolve())],
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return p


def _toolbox(ctx):
    return getattr(ctx, "toolbox", None)


def _parse_papers(text: str, topic_slug: str) -> list[Paper]:
    """Parse the MCP server's search result (JSON list, or best-effort text)."""
    papers: list[Paper] = []
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return papers
    items = data if isinstance(data, list) else data.get("papers", data.get("results", []))
    for it in items or []:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title", "")).strip()
        summary = str(it.get("summary") or it.get("abstract") or "").strip()
        if not title:
            continue
        year = 0
        for key in ("published", "date", "updated"):
            v = str(it.get(key, ""))
            if len(v) >= 4 and v[:4].isdigit():
                year = int(v[:4])
                break
        papers.append(Paper(title=title, abstract=summary, topic=topic_slug,
                            source="arxiv-mcp", year=year))
    return papers


def search_arxiv_mcp(ctx, query: str, topic_slug: str, max_results: int = 10) -> list[Paper]:
    """Search arXiv via the MCP server. Returns [] if the server is unavailable."""
    box = _toolbox(ctx)
    if box is None:
        return []
    try:
        res = box.call(MCP_TOOL, tool="search_papers",
                       arguments={"query": query, "max_results": max_results,
                                  "categories": ["cs.CR", "cs.LG", "cs.AI"]})
        if not getattr(res, "ok", False):
            return []
        return _parse_papers(res.data if isinstance(res.data, str) else "", topic_slug)
    except Exception:  # noqa: BLE001 — best-effort; curated corpus carries the run
        return []


def citation_graph_mcp(ctx, paper_id: str) -> list[str]:
    """Fetch references/citations for a paper via the MCP citation_graph tool.

    Returns a list of related-work titles the factory can build on. [] on failure.
    """
    box = _toolbox(ctx)
    if box is None or not paper_id:
        return []
    try:
        res = box.call(MCP_TOOL, tool="citation_graph", arguments={"paper_id": paper_id})
        if not getattr(res, "ok", False):
            return []
        data = json.loads(res.data) if isinstance(res.data, str) else {}
        titles = []
        for bucket in ("references", "citations"):
            for it in data.get(bucket, []) or []:
                t = it.get("title") if isinstance(it, dict) else str(it)
                if t:
                    titles.append(str(t).strip())
        return titles
    except Exception:  # noqa: BLE001
        return []


def available(ctx) -> bool:
    """True if the arxiv MCP proxy tool is registered in the toolbox."""
    box = _toolbox(ctx)
    if box is None:
        return False
    try:
        return MCP_TOOL in getattr(box, "tools", {}) or bool(box.call(MCP_TOOL, tool="list_papers"))
    except Exception:  # noqa: BLE001
        return False
