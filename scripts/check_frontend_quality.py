"""Static frontend quality checks for the Phase 3–6 release."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
issues = []
for path in TEMPLATES.rglob("*.html"):
    text = path.read_text()
    for tag in re.findall(r"<img\b[^>]*>", text, re.I):
        if "alt=" not in tag:
            issues.append(f"{path}: image missing alt text")
    for tag in re.findall(r"<script\b[^>]*src=[^>]*>", text, re.I):
        if "defer" not in tag and "async" not in tag:
            issues.append(f"{path}: external script is not deferred")
css = (ROOT / "static/css/refinement.css").read_text()
if "@media(max-width:700px)" not in css and "@media (max-width:700px)" not in css:
    issues.append("refinement.css: missing mobile breakpoint")
if issues:
    print("frontend-quality-failed")
    print("\n".join(issues))
    raise SystemExit(1)
print("frontend-quality-ok")
