# Dark Factory — Windows 11 mini-PC setup (no GPU, 12 GB RAM, 100 GB disk).
#
# Sets up the autonomous AI-security research team to run 24/7 on a small box
# using Ollama Cloud models (no local GPU needed). Run in PowerShell:
#
#     powershell -ExecutionPolicy Bypass -File scripts/setup-windows11.ps1
#
# Idempotent: safe to re-run.

$ErrorActionPreference = "Stop"
Write-Host "== Dark Factory setup (Windows 11 mini-PC) ==" -ForegroundColor Cyan

# 1) Python 3.10+ check
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) {
    Write-Host "Python not found. Install Python 3.11 from https://python.org and re-run." -ForegroundColor Yellow
    exit 1
}
python --version

# 2) Virtual environment
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# 3) Install the factory (pulls NYX from git) + live extras
pip install -e ".[dev]"
pip install requests    # enables live Ollama Cloud + web ingestion

# 4) Configure the Ollama Cloud brain. Cloud models run server-side, so a
#    GPU-less 12 GB mini-PC is plenty. Create a .env with your key:
if (-not (Test-Path ".env")) {
@"
# Ollama Cloud brain (get a key at https://ollama.com). Leave blank to run
# fully offline in deterministic MOCK mode.
OLLAMA_API_KEY=
OLLAMA_HOST=https://ollama.com
# Cloud model names (adjust to what your account can call):
NYX_MODEL_ARCHITECT=qwen3.5-coder:480b-cloud
NYX_MODEL_REVIEWER=glm-5.1:cloud
NYX_MODEL_FAST=gemma4:cloud
# Be a good web citizen when ingesting arXiv:
NYX_USER_AGENT=dark-factory/0.1 (+research; you@example.com)
"@ | Out-File -Encoding utf8 .env
    Write-Host "Wrote .env — add your OLLAMA_API_KEY to go live (optional)." -ForegroundColor Green
}

# 5) (Optional) A TeX toolchain for PDF output. Without it the factory still
#    emits .tex + .md. Install MiKTeX for PDFs:
if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    Write-Host "No TeX found. For PDF output install MiKTeX: winget install MiKTeX.MiKTeX" -ForegroundColor Yellow
}

# 6) Health check + a first paper
python -m darkfactory doctor
python -m darkfactory paper prompt-injection

Write-Host "`n== Ready. Run the 24/7 loop with: ==" -ForegroundColor Cyan
Write-Host "   python -m darkfactory serve --max 10" -ForegroundColor White
Write-Host "Or schedule it with Task Scheduler to run continuously." -ForegroundColor White
