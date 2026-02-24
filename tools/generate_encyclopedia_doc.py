#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_HTML = DOCS_DIR / "B7G_Project_Encyclopedia.html"
OUTPUT_DOCX = DOCS_DIR / "B7G_Project_Encyclopedia.docx"

CORE_FILES = [
    "README.md",
    "Makefile",
    "pyproject.toml",
    "requirements.txt",
    "vercel.json",
    "render.yaml",
    "api/index.py",
    "backend/requirements.txt",
    "backend/requirements-dev.txt",
    "backend/app/database.py",
    "backend/app/models.py",
    "backend/app/schemas.py",
    "backend/app/serializers.py",
    "backend/app/crud.py",
    "backend/app/main.py",
    "backend/app/routes/teams.py",
    "backend/app/routes/players.py",
    "backend/app/routes/ties.py",
    "backend/app/routes/matches.py",
    "backend/app/routes/referee.py",
    "backend/app/routes/schedule.py",
    "backend/app/routes/viewer.py",
    "backend/app/routes/finals.py",
    "backend/seed.py",
    "backend/tests/test_api.py",
    "frontend/package.json",
    "frontend/vite.config.js",
    "frontend/src/main.jsx",
    "frontend/src/App.jsx",
    "frontend/src/api.js",
    "frontend/src/pages/Home.jsx",
    "frontend/src/pages/Viewer.jsx",
    "frontend/src/pages/Referee.jsx",
    "frontend/src/pages/PostFinals.jsx",
    "frontend/src/pages/Schedule.jsx",
    "frontend/src/pages/Match.jsx",
    "frontend/src/styles.css",
]


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def explain_line(line: str, ext: str) -> str:
    s = line.strip()
    if not s:
        return "Blank line used for readability and separation of logic blocks."

    if ext in {".md"}:
        if s.startswith("#"):
            return "Markdown heading that structures documentation hierarchy."
        if s.startswith("-"):
            return "Markdown list item used to enumerate concepts or steps."
        if s.startswith("```"):
            return "Markdown code fence boundary."
        return "Documentation content line conveying project instructions or notes."

    if ext in {".json", ".toml", ".yml", ".yaml"}:
        if s.startswith("{") or s.startswith("}") or s.startswith("[") or s.startswith("]"):
            return "Configuration structure delimiter."
        if ":" in s or "=" in s:
            return "Configuration key/value that controls runtime or deployment behavior."
        return "Configuration line in project settings file."

    if ext in {".css"}:
        if s.startswith("/*") or s.startswith("*") or s.startswith("*/"):
            return "CSS comment line."
        if s.endswith("{"):
            return "CSS selector block opening."
        if s == "}":
            return "CSS selector block closing."
        if s.startswith("--"):
            return "CSS custom property (design token) used for consistent theming."
        if ":" in s and s.endswith(";"):
            return "CSS property declaration controlling layout, typography, color, or interaction."
        return "CSS formatting/support line."

    if s.startswith("#"):
        return "Comment line explaining intent or a rule."
    if s.startswith("//"):
        return "Comment line explaining frontend or JS logic."
    if s.startswith("@"):
        return "Decorator/annotation registering behavior (for example API route metadata)."
    if s.startswith("import ") or s.startswith("from "):
        return "Imports dependency or symbol needed by this module."
    if s.startswith("class "):
        return "Class declaration defining a model, schema, or reusable unit of logic."
    if s.startswith("def "):
        return "Function declaration encapsulating a specific unit of backend behavior."
    if s.startswith("return "):
        return "Returns computed value/control from function."
    if s.startswith("raise "):
        return "Raises explicit error to enforce business rule or validation."
    if s.startswith("if ") or s.startswith("if("):
        return "Conditional branch start."
    if s.startswith("elif "):
        return "Alternative conditional branch."
    if s.startswith("else"):
        return "Fallback branch when prior conditions are not met."
    if s.startswith("for "):
        return "Loop over collection to process each item."
    if s.startswith("while "):
        return "Loop while condition remains true."
    if s.startswith("try"):
        return "Starts protected block for exception-safe execution."
    if s.startswith("except"):
        return "Exception handler for anticipated failures."
    if s.startswith("finally"):
        return "Cleanup block guaranteed to run."
    if s in {"{", "}", "};", ")", "("}:
        return "Structure delimiter for code block/syntax."

    if ext in {".js", ".jsx"}:
        if s.startswith("export default function") or s.startswith("function "):
            return "Function component/function declaration in frontend module."
        if s.startswith("const ") and "=>" in s:
            return "Arrow function or computed constant declaration."
        if s.startswith("const "):
            return "Constant declaration storing immutable reference/value."
        if s.startswith("let "):
            return "Mutable variable declaration used for evolving state within scope."
        if s.startswith("<") and not s.startswith("<="):
            return "JSX markup line defining UI structure."
        if s.startswith("use") and "(" in s:
            return "Hook invocation to manage state/effects/memoization in React."
        if "set" in s and "(" in s and s.endswith(");"):
            return "State update or method invocation."
        if "=" in s and s.endswith(";"):
            return "Assignment/computation line in frontend logic."
        return "Frontend logic line participating in data flow or rendering."

    if ext in {".py"}:
        if s.startswith("with "):
            return "Context manager ensuring safe resource handling."
        if s.startswith("db."):
            return "Database operation through ORM session."
        if "=" in s and not s.startswith("=="):
            return "Variable assignment or state mutation line."
        return "Python logic line contributing to backend behavior."

    if "=" in s and s.endswith(";"):
        return "Assignment or statement line."

    return "Code line that supports the surrounding logic block."


def extract_symbols(text: str, ext: str) -> list[str]:
    symbols: list[str] = []
    lines = text.splitlines()

    if ext == ".py":
        for ln in lines:
            m = re.match(r"\s*(def|class)\s+([A-Za-z0-9_]+)", ln)
            if m:
                symbols.append(f"{m.group(1)} {m.group(2)}")
    elif ext in {".js", ".jsx"}:
        patterns = [
            r"\s*export\s+default\s+function\s+([A-Za-z0-9_]+)",
            r"\s*function\s+([A-Za-z0-9_]+)",
            r"\s*const\s+([A-Za-z0-9_]+)\s*=\s*\(",
            r"\s*const\s+([A-Za-z0-9_]+)\s*=\s*[A-Za-z0-9_]+\s*=>",
            r"\s*const\s+([A-Za-z0-9_]+)\s*=",
        ]
        seen = set()
        for ln in lines:
            for pat in patterns:
                m = re.match(pat, ln)
                if m:
                    name = m.group(1)
                    if name not in seen:
                        seen.add(name)
                        symbols.append(name)
                    break
    elif ext == ".css":
        for ln in lines:
            s = ln.strip()
            if s.endswith("{") and not s.startswith("@"):
                selector = s[:-1].strip()
                if selector and len(selector) < 80:
                    symbols.append(selector)

    return symbols[:20]


def code_block(content: str) -> str:
    return f"<pre><code>{html.escape(content)}</code></pre>"


def section_card(title: str, body: str) -> str:
    return f"<div class='card'><h3>{html.escape(title)}</h3><p>{body}</p></div>"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


commit = sh(["git", "rev-parse", "--short", "HEAD"])
branch = sh(["git", "branch", "--show-current"])
generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

existing_files: list[Path] = []
for rel in CORE_FILES:
    p = ROOT / rel
    if p.exists() and p.is_file():
        existing_files.append(p)

backend_files = [p for p in existing_files if "/backend/" in p.as_posix()]
frontend_files = [p for p in existing_files if "/frontend/" in p.as_posix()]
api_files = [p for p in existing_files if "/api/" in p.as_posix()]

lines_total = 0
for p in existing_files:
    try:
        lines_total += len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        pass

html_parts: list[str] = []

html_parts.append(
    """
<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>B7G Project Encyclopedia</title>
<style>
body {
  font-family: "Segoe UI", "Calibri", sans-serif;
  line-height: 1.5;
  color: #0f172a;
  margin: 0;
  padding: 0;
  background: #f8fafc;
}
.cover {
  padding: 52px 48px;
  background: linear-gradient(135deg, #0f766e 0%, #2563eb 48%, #ea580c 100%);
  color: white;
}
.cover h1 { font-size: 34px; margin: 0 0 10px; }
.cover h2 { font-size: 18px; margin: 0 0 18px; font-weight: 500; }
.cover p { margin: 6px 0; font-size: 14px; }
.container { padding: 28px 34px 48px; }
h2.section {
  color: #0f766e;
  border-bottom: 3px solid #bfdbfe;
  padding-bottom: 6px;
  margin-top: 28px;
}
h3 {
  color: #1d4ed8;
  margin-top: 22px;
}
.card-grid {
  display: block;
}
.card {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  padding: 12px;
  margin: 8px 0;
  border-left: 6px solid #2563eb;
}
.note {
  border: 1px solid #fed7aa;
  background: #fff7ed;
  padding: 12px;
  margin: 10px 0;
  border-left: 6px solid #ea580c;
}
.success {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  padding: 12px;
  margin: 10px 0;
  border-left: 6px solid #16a34a;
}
code {
  font-family: "Consolas", "Courier New", monospace;
  background: #e2e8f0;
  padding: 1px 4px;
  border-radius: 4px;
}
pre {
  background: #0b1220;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 20px;
  font-size: 11px;
  table-layout: fixed;
}
th, td {
  border: 1px solid #cbd5e1;
  padding: 6px;
  vertical-align: top;
  word-wrap: break-word;
}
th {
  background: #e0f2fe;
  color: #0f172a;
}
tr:nth-child(even) td { background: #f8fafc; }
.toc a { color: #1d4ed8; text-decoration: none; }
.small { font-size: 12px; color: #334155; }
.file-title {
  background: #ecfeff;
  border: 1px solid #bae6fd;
  border-left: 5px solid #0891b2;
  padding: 8px 10px;
  margin-top: 20px;
}
.appendix-controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin: 12px 0;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f1f5f9;
}
.appendix-controls input {
  min-width: 220px;
  flex: 1 1 260px;
  border: 1px solid #94a3b8;
  border-radius: 6px;
  padding: 7px 8px;
  font-size: 12px;
}
.appendix-controls button {
  border: 1px solid #1d4ed8;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
}
.appendix-controls button.secondary {
  background: #fff;
  color: #1d4ed8;
}
.appendix-link-grid {
  columns: 2;
  column-gap: 14px;
  margin: 10px 0 14px;
}
.appendix-link-grid a {
  display: inline-block;
  margin: 2px 0;
  color: #1d4ed8;
  text-decoration: none;
  font-size: 12px;
}
.file-block {
  margin: 12px 0;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  background: #ffffff;
}
.file-block summary {
  list-style: none;
  cursor: pointer;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #ecfeff;
  font-weight: 600;
  color: #0f172a;
}
.file-block summary::-webkit-details-marker {
  display: none;
}
.file-block summary::before {
  content: "+ ";
  color: #2563eb;
}
.file-block[open] summary::before {
  content: "- ";
}
.file-block-content {
  padding: 8px 10px 2px;
}
.footer {
  margin-top: 26px;
  padding-top: 10px;
  border-top: 1px dashed #94a3b8;
  font-size: 12px;
  color: #334155;
}
@page {
  margin: 1in;
}
@media (max-width: 900px) {
  .appendix-link-grid {
    columns: 1;
  }
}
</style>
</head>
<body>
"""
)

html_parts.append(
    f"""
<div class='cover'>
  <h1>B7G Badminton Project Encyclopedia</h1>
  <h2>Industry-Standard Technical Handbook - Setup, Codebase, Operations, and Deployment</h2>
  <p><strong>Repository:</strong> badminton-app</p>
  <p><strong>Branch:</strong> {html.escape(branch)} | <strong>Commit:</strong> {html.escape(commit)}</p>
  <p><strong>Generated:</strong> {html.escape(generated)}</p>
  <p><strong>Audience:</strong> New and experienced engineers onboarding to this project.</p>
</div>
<div class='container'>
"""
)

html_parts.append("<h2 class='section' id='toc'>Table of Contents</h2>")
html_parts.append(
    """
<div class='toc'>
  <p>1. <a href='#s1'>Project Overview</a></p>
  <p>2. <a href='#s2'>Prerequisites and Local Installation</a></p>
  <p>3. <a href='#s3'>How the System Works End-to-End</a></p>
  <p>4. <a href='#s4'>Backend Deep Dive (FastAPI + SQLAlchemy)</a></p>
  <p>5. <a href='#s5'>Frontend Deep Dive (React + Vite)</a></p>
  <p>6. <a href='#s6'>Deployment Guide (Single Vercel and Split Hosting)</a></p>
  <p>7. <a href='#s7'>Operations Runbook (Reset, Seed, Verify, Troubleshoot)</a></p>
  <p>8. <a href='#s8'>Code Encyclopedia Appendix (Line-by-Line)</a></p>
</div>
"""
)

html_parts.append("<h2 class='section' id='s1'>1. Project Overview</h2>")
html_parts.append(
    "<p>This product is a tournament operations platform for badminton league matches. It provides referee workflows, live viewer dashboards, standings, finals orchestration, and post-finals category analytics.</p>"
)
html_parts.append("<div class='card-grid'>")
html_parts.append(section_card("Tournament Format", "10 round-robin ties (league stage). Each tie has 12 regular games. Game #13 appears only as a decider at 6-6 tie score."))
html_parts.append(section_card("Qualification", "After all 10 ties are complete, rank 1 and 2 become finalists. Rank 3 automatically gets Bronze."))
html_parts.append(section_card("Finals", "Final tie consists of 12 games between top 2 teams. Winner gets Gold, other finalist gets Silver."))
html_parts.append(section_card("Live Data Model", "Viewer and referee screens poll backend frequently; updates propagate without manual refresh."))
html_parts.append("</div>")

html_parts.append("<h2 class='section' id='s2'>2. Prerequisites and Local Installation</h2>")
html_parts.append("<h3>2.1 Tools Required</h3>")
html_parts.append(
    "<ul><li>Python 3.11+ (backend)</li><li>Node.js 18+ and npm (frontend)</li><li>Git</li><li>PostgreSQL 14+ (required for local runtime)</li><li>pgAdmin 4 or DBeaver (recommended local DB GUI)</li></ul>"
)
html_parts.append("<h3>2.2 Clone and Install</h3>")
html_parts.append(
    code_block(
        "git clone <your-repo-url>\n"
        "cd badminton-app\n\n"
        "# Local Postgres (Homebrew example)\n"
        "brew services start postgresql@16\n"
        "createdb -h localhost -U <your-macos-username> badminton_b7g || true\n\n"
        "# Backend\n"
        "cd backend\n"
        "python3 -m venv .venv\n"
        "source .venv/bin/activate\n"
        "pip install -r requirements-dev.txt\n"
        "export DATABASE_URL=postgresql://<your-macos-username>@localhost:5432/badminton_b7g\n"
        "python3 seed.py\n"
        "uvicorn app.main:app --reload\n\n"
        "# Frontend (new terminal)\n"
        "cd ../frontend\n"
        "npm install\n"
        "cp .env.example .env\n"
        "# set VITE_API_URL=http://localhost:8000\n"
        "npm run dev"
    )
)
html_parts.append("<div class='success'><strong>Result:</strong> frontend runs on <code>http://localhost:5173</code>, backend on <code>http://localhost:8000</code>.</div>")

html_parts.append("<h3>2.3 pgAdmin Setup (Local DB UI)</h3>")
html_parts.append(
    "<ol>"
    "<li>Install pgAdmin: <code>brew install --cask pgadmin4</code></li>"
    "<li>Create server with Name <code>Badminton Local PG</code> (any label).</li>"
    "<li>Use Host <code>localhost</code>, Port <code>5432</code>, Maintenance DB <code>postgres</code>.</li>"
    "<li>Username: macOS user for Homebrew Postgres (for example <code>arjundixithts</code>) or <code>postgres</code> for Docker Postgres.</li>"
    "<li>Password: your configured local role password (Docker default is <code>postgres</code>).</li>"
    "</ol>"
)

html_parts.append("<h3>2.4 Seed Modes</h3>")
html_parts.append(
    "<ul>"
    "<li><code>python3 seed.py</code>: fresh tournament start (same teams/players, all pending).</li>"
    "<li><code>python3 seed.py --demo-progress</code>: sample live/completed demo states.</li>"
    "</ul>"
)

html_parts.append("<h2 class='section' id='s3'>3. How the System Works End-to-End</h2>")
html_parts.append("<h3>3.1 Runtime Request Flow</h3>")
html_parts.append(
    "<ol>"
    "<li>User action in React page (for example, Save Score in Referee).</li>"
    "<li><code>frontend/src/api.js</code> sends HTTP request.</li>"
    "<li>FastAPI route in <code>backend/app/routes/*.py</code> receives request.</li>"
    "<li>Route calls business logic in <code>backend/app/crud.py</code>.</li>"
    "<li>CRUD updates DB and recalculates tie/final status as needed.</li>"
    "<li>Viewer/Referee polling reloads dashboard and reflects latest state.</li>"
    "</ol>"
)
html_parts.append("<h3>3.2 Core Rule Enforcement</h3>")
html_parts.append(
    "<ul>"
    "<li>Referee assignment required before scoring.</li>"
    "<li>Lineup confirmation required before scoring.</li>"
    "<li>Badminton scoring: 21 with deuce, cap 30.</li>"
    "<li>Game #13 only appears/starts when tie is 6-6.</li>"
    "<li>Final tie appears only after league completion.</li>"
    "</ul>"
)

html_parts.append("<h2 class='section' id='s4'>4. Backend Deep Dive (FastAPI + SQLAlchemy)</h2>")
html_parts.append(
    f"<p class='small'>Backend files analyzed: {len(backend_files)}. Total project lines analyzed: {lines_total}.</p>"
)

html_parts.append("<h3>4.1 Backend Responsibilities</h3>")
html_parts.append(
    "<ul>"
    "<li>Define schema and constraints (models).</li>"
    "<li>Expose API contracts (schemas, serializers, routes).</li>"
    "<li>Enforce tournament business rules (crud).</li>"
    "<li>Initialize default tournament data (seed + startup auto-seed).</li>"
    "</ul>"
)

html_parts.append("<h3>4.2 Backend File Summary</h3>")
html_parts.append("<table><tr><th>File</th><th>Purpose</th><th>Top Symbols</th></tr>")
for p in backend_files + api_files:
    text = p.read_text(encoding="utf-8", errors="ignore")
    ext = p.suffix.lower()
    symbols = extract_symbols(text, ext)
    rel = p.relative_to(ROOT).as_posix()
    purpose = ""
    if rel.endswith("models.py"):
        purpose = "ORM tables and constraints for tournament entities."
    elif rel.endswith("crud.py"):
        purpose = "Primary business logic and ranking/finals calculations."
    elif rel.endswith("main.py"):
        purpose = "API app bootstrap, CORS, auto-seed, router wiring."
    elif rel.endswith("database.py"):
        purpose = "Database URL normalization, engine/session creation."
    elif "/routes/" in rel:
        purpose = "HTTP endpoints for a functional module."
    elif rel.endswith("serializers.py"):
        purpose = "Maps DB models to API response objects."
    elif rel.endswith("schemas.py"):
        purpose = "Pydantic request/response models."
    elif rel.endswith("seed.py"):
        purpose = "Seeds exact team/player/fixture default dataset."
    elif rel.endswith("test_api.py"):
        purpose = "API and business behavior regression tests."
    elif rel.endswith("api/index.py"):
        purpose = "Vercel serverless adapter for nested /api paths."
    else:
        purpose = "Backend/project support module."

    html_parts.append(
        "<tr>"
        f"<td><code>{html.escape(rel)}</code></td>"
        f"<td>{html.escape(purpose)}</td>"
        f"<td>{html.escape(', '.join(symbols) if symbols else 'N/A')}</td>"
        "</tr>"
    )
html_parts.append("</table>")

html_parts.append("<h2 class='section' id='s5'>5. Frontend Deep Dive (React + Vite)</h2>")
html_parts.append(
    f"<p class='small'>Frontend files analyzed: {len(frontend_files)}.</p>"
)
html_parts.append("<h3>5.1 Frontend Responsibilities</h3>")
html_parts.append(
    "<ul>"
    "<li>Render mobile-first dashboards and score controls.</li>"
    "<li>Route between Home, Viewer, Referee, and Post Finals.</li>"
    "<li>Poll API frequently to provide near real-time updates.</li>"
    "<li>Apply business-guided UX constraints (start/stop/save guards).</li>"
    "</ul>"
)

html_parts.append("<h3>5.2 Frontend File Summary</h3>")
html_parts.append("<table><tr><th>File</th><th>Purpose</th><th>Top Symbols</th></tr>")
for p in frontend_files:
    text = p.read_text(encoding="utf-8", errors="ignore")
    ext = p.suffix.lower()
    symbols = extract_symbols(text, ext)
    rel = p.relative_to(ROOT).as_posix()
    if rel.endswith("App.jsx"):
        purpose = "Top-level route map and dynamic navigation tabs."
    elif rel.endswith("api.js"):
        purpose = "Central HTTP client and endpoint wrappers."
    elif rel.endswith("Referee.jsx"):
        purpose = "Referee workflow, tie accordions, scoring controls, confirmations."
    elif rel.endswith("Viewer.jsx"):
        purpose = "Live viewer, standings, team-wise ties, finals status, medals."
    elif rel.endswith("Home.jsx"):
        purpose = "Landing dashboard and rule highlights."
    elif rel.endswith("PostFinals.jsx"):
        purpose = "Category-wise individual winner analytics view."
    elif rel.endswith("styles.css"):
        purpose = "Global visual system, responsive layout, themed components."
    else:
        purpose = "Frontend support module."

    html_parts.append(
        "<tr>"
        f"<td><code>{html.escape(rel)}</code></td>"
        f"<td>{html.escape(purpose)}</td>"
        f"<td>{html.escape(', '.join(symbols) if symbols else 'N/A')}</td>"
        "</tr>"
    )
html_parts.append("</table>")

html_parts.append("<h2 class='section' id='s6'>6. Deployment Guide</h2>")
html_parts.append("<h3>6.1 Single Free Deployment on Vercel (Current Setup)</h3>")
html_parts.append(
    "<ol>"
    "<li>Import repo into Vercel with root directory as repository root.</li>"
    "<li>Vercel uses <code>vercel.json</code> to build frontend and route API.</li>"
    "<li>Set env vars: <code>VITE_API_URL=/api</code>, <code>DATABASE_URL</code>, <code>CORS_ORIGINS</code>, <code>AUTO_SEED_ON_EMPTY=true</code>.</li>"
    "<li>Deploy and verify <code>/api/health</code> and <code>/api/viewer/dashboard</code>.</li>"
    "</ol>"
)
html_parts.append("<h3>6.2 Why /api Rewrite Exists</h3>")
html_parts.append(
    "<p>The project rewrites <code>/api/(.*)</code> to <code>/api?__path=/$1</code> and then maps <code>__path</code> inside <code>api/index.py</code>. This avoids Vercel nested-path edge NOT_FOUND behavior in some serverless route layouts.</p>"
)
html_parts.append("<h3>6.3 Optional Split Deployment</h3>")
html_parts.append(
    "<ul>"
    "<li>Frontend on Vercel.</li>"
    "<li>Backend on Render using <code>render.yaml</code>.</li>"
    "<li>Set frontend <code>VITE_API_URL</code> to Render URL.</li>"
    "</ul>"
)

html_parts.append("<h2 class='section' id='s7'>7. Operations Runbook</h2>")
html_parts.append("<h3>7.1 One-time Full Data Reset</h3>")
html_parts.append(
    "<div class='note'><strong>Use carefully:</strong> Set <code>AUTO_SEED_FORCE_RESET=true</code> for one deploy/startup to reset tournament state to default seed. Then set it back to <code>false</code>.</div>"
)
html_parts.append("<h3>7.2 Verification Checklist</h3>")
html_parts.append(
    "<ul>"
    "<li><code>/api/health</code> returns JSON status ok.</li>"
    "<li>Viewer loads without JSON parse errors.</li>"
    "<li>Referee can assign and score a match end-to-end.</li>"
    "<li>Standings update after completed tie games.</li>"
    "<li>Final appears only after all 10 ties completed.</li>"
    "</ul>"
)

html_parts.append("<h2 class='section' id='s8'>8. Code Encyclopedia Appendix (Line-by-Line)</h2>")
html_parts.append(
    "<p>This appendix presents every line for core project files with concise explanations. Sections are collapsed by default to improve navigation.</p>"
)
html_parts.append(
    "<div class='appendix-controls'>"
    "<input id='fileFilter' type='text' placeholder='Filter files (example: viewer, backend/app, seed.py)'>"
    "<button type='button' onclick='expandAllFiles()'>Expand All</button>"
    "<button type='button' class='secondary' onclick='collapseAllFiles()'>Collapse All</button>"
    "<span class='small' id='fileCount'></span>"
    "</div>"
)

appendix_entries: list[tuple[Path, str, str, int]] = []
for p in existing_files:
    rel = p.relative_to(ROOT).as_posix()
    appendix_entries.append((p, rel, slugify(rel), len(p.read_text(encoding="utf-8", errors="ignore").splitlines())))

html_parts.append("<div class='appendix-link-grid'>")
for _, rel, slug, line_count in appendix_entries:
    html_parts.append(
        f"<a href='#{html.escape(slug)}'><code>{html.escape(rel)}</code> ({line_count})</a>"
    )
html_parts.append("</div>")

for idx, (p, rel, slug, line_count) in enumerate(appendix_entries):
    text = p.read_text(encoding="utf-8", errors="ignore")
    ext = p.suffix.lower()
    lines = text.splitlines()

    open_attr = " open" if idx < 2 else ""
    html_parts.append(
        f"<details class='file-block' id='{html.escape(slug)}' data-file='{html.escape(rel.lower())}'{open_attr}>"
        f"<summary><code>{html.escape(rel)}</code> &nbsp; | &nbsp; Lines: {line_count}</summary>"
        "<div class='file-block-content'>"
    )

    symbols = extract_symbols(text, ext)
    if symbols:
        html_parts.append(f"<p class='small'><strong>Key symbols:</strong> {html.escape(', '.join(symbols))}</p>")

    # Keep very long lines manageable
    html_parts.append("<table><tr><th style='width:7%'>Line</th><th style='width:43%'>Code</th><th style='width:50%'>Explanation</th></tr>")
    for idx, raw in enumerate(lines, start=1):
        code = raw.replace("\t", "    ")
        if len(code) > 240:
            code = code[:237] + "..."
        explanation = explain_line(raw, ext)
        html_parts.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td><code>{html.escape(code) if code else '&nbsp;'}</code></td>"
            f"<td>{html.escape(explanation)}</td>"
            "</tr>"
        )
    html_parts.append("</table>")
    html_parts.append("</div></details>")

html_parts.append(
    f"<div class='footer'>Generated from source at commit <code>{html.escape(commit)}</code> on branch <code>{html.escape(branch)}</code> ({html.escape(generated)}).</div>"
)

html_parts.append(
    """
<script>
(function () {
  const blocks = () => Array.from(document.querySelectorAll(".file-block"));
  const counter = document.getElementById("fileCount");
  const filterInput = document.getElementById("fileFilter");

  function updateCount(visible) {
    if (!counter) return;
    counter.textContent = visible + " file sections visible";
  }

  window.expandAllFiles = function () {
    blocks().forEach((node) => {
      if (node.style.display !== "none") node.open = true;
    });
  };

  window.collapseAllFiles = function () {
    blocks().forEach((node) => {
      if (node.style.display !== "none") node.open = false;
    });
  };

  function applyFilter() {
    const query = (filterInput && filterInput.value ? filterInput.value : "").trim().toLowerCase();
    let visible = 0;
    blocks().forEach((node) => {
      const file = node.getAttribute("data-file") || "";
      const show = !query || file.includes(query);
      node.style.display = show ? "" : "none";
      if (show) visible += 1;
    });
    updateCount(visible);
  }

  if (filterInput) {
    filterInput.addEventListener("input", applyFilter);
  }
  applyFilter();
})();
</script>
"""
)
html_parts.append("</div></body></html>")

OUTPUT_HTML.write_text("\n".join(html_parts), encoding="utf-8")
print(f"HTML generated: {OUTPUT_HTML}")
print(f"Target DOCX path: {OUTPUT_DOCX}")
