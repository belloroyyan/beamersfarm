"""Build the staff wiki from scripts/staff_manual_data.py.

    python scripts/build_staff_manual.py

Writes:
  templates/staff_manual_content.html     the searchable wiki page (role-aware: owner-only sections are wrapped in a Jinja if)
  static/staff-manual.md                  Owner download (everything)
  static/staff-manual-salesperson.md      Salesperson download (owner-only sections left out)
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from staff_manual_data import SECTIONS  # noqa: E402


def inline_html(text):
    """Escape, then turn `code`, **bold** and *italic* into tags."""
    codes = []
    def stash(m):
        codes.append(html.escape(m.group(1)))
        return f"\x00{len(codes) - 1}\x00"
    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", text)


def block_html(block):
    kind = block[0]
    if kind == "p":
        return f"<p>{inline_html(block[1])}</p>"
    if kind in ("steps", "ul"):
        head, items = block[1], block[2]
        tag = "ol" if kind == "steps" else "ul"
        cls = "wiki-steps" if kind == "steps" else "wiki-list"
        h = f'<h3>{inline_html(head)}</h3>' if head else ""
        lis = "".join(f"<li>{inline_html(i)}</li>" for i in items)
        return f'{h}<{tag} class="{cls}">{lis}</{tag}>'
    if kind == "note":
        label = {"tip": "Tip", "warn": "Careful", "info": "Good to know"}[block[1]]
        return f'<div class="wiki-note wiki-note-{block[1]}"><strong>{label}</strong><p>{inline_html(block[2])}</p></div>'
    if kind == "table":
        head = "".join(f"<th scope=\"col\">{inline_html(h)}</th>" for h in block[1])
        rows = "".join("<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in row) + "</tr>" for row in block[2])
        return f'<div class="wiki-table-wrap"><table class="wiki-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    raise ValueError(kind)


def section_html(sec):
    badge = '<span class="wiki-badge">Owner only</span>' if sec["audience"] == "owner" else ""
    body = "".join(block_html(b) for b in sec["blocks"])
    return (f'<article class="wiki-block" data-wiki-block id="{sec["id"]}">'
            f'<header class="wiki-block-head"><h2>{inline_html(sec["title"])}</h2>{badge}</header>'
            f'<p class="wiki-summary">{inline_html(sec["summary"])}</p>{body}</article>')


def build_html():
    toc_all, toc_owner, parts = [], [], []
    for sec in SECTIONS:
        link = f'<a href="#{sec["id"]}">{html.escape(sec["title"])}</a>'
        (toc_owner if sec["audience"] == "owner" else toc_all).append((sec["id"], link, sec["audience"]))
    toc = []
    for sec in SECTIONS:
        link = f'<a href="#{sec["id"]}">{html.escape(sec["title"])}</a>'
        toc.append(f"{{% if manual_role == 'Owner' %}}{link}{{% endif %}}" if sec["audience"] == "owner" else link)
        sec_html = section_html(sec)
        parts.append(f"{{% if manual_role == 'Owner' %}}{sec_html}{{% endif %}}" if sec["audience"] == "owner" else sec_html)
    out = ('<nav class="wiki-toc" aria-label="Contents"><p class="wiki-toc-title">Contents</p><div class="wiki-toc-links">'
           + "".join(toc) + "</div></nav>\n" + "\n".join(parts) + "\n")
    assert "{{" not in out.replace("{%", "").replace("%}", "") and "{#" not in out, "content must not contain Jinja syntax"
    return out


def block_md(block):
    kind = block[0]
    if kind == "p":
        return block[1]
    if kind in ("steps", "ul"):
        head, items = block[1], block[2]
        lines = [f"**{head}**\n"] if head else []
        lines += [f"{n}. {i}" if kind == "steps" else f"- {i}" for n, i in enumerate(items, 1)]
        return "\n".join(lines)
    if kind == "note":
        label = {"tip": "Tip", "warn": "Careful", "info": "Good to know"}[block[1]]
        return f"> **{label}:** {block[2]}"
    if kind == "table":
        rows = [" | ".join(block[1]), " | ".join("---" for _ in block[1])] + [" | ".join(c.replace("|", "/") for c in r) for r in block[2]]
        return "\n".join("| " + r + " |" for r in rows)
    raise ValueError(kind)


def build_md(include_owner):
    secs = [s for s in SECTIONS if include_owner or s["audience"] == "all"]
    who = "Owner and Salespeople" if include_owner else "Salespeople"
    lines = [f"# Beamers Farms Staff Digital Wiki", "", f"*Operating manual for {who}. Built from the same content as the in-site wiki.*", "", "## Contents", ""]
    lines += [f"- {s['title']}" + (" *(Owner only)*" if s["audience"] == "owner" else "") for s in secs]
    for s in secs:
        lines += ["", f"## {s['title']}" + (" (Owner only)" if s["audience"] == "owner" else ""), "", f"*{s['summary']}*", ""]
        for b in s["blocks"]:
            lines += [block_md(b), ""]
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    (ROOT / "templates" / "staff_manual_content.html").write_text(build_html(), encoding="utf-8")
    (ROOT / "static" / "staff-manual.md").write_text(build_md(True), encoding="utf-8")
    (ROOT / "static" / "staff-manual-salesperson.md").write_text(build_md(False), encoding="utf-8")
    words = sum(len(re.findall(r"\w+", build_md(True))) for _ in [0])
    print(f"built {len(SECTIONS)} sections, ~{words} words (owner edition)")
