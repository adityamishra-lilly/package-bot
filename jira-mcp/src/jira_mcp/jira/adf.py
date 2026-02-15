"""Atlassian Document Format (ADF) helpers.

Jira REST API v3 requires rich text in ADF format. These helpers convert
plain text and simple markdown to/from ADF.
"""

from __future__ import annotations

import re
from typing import Any


def text_to_adf(text: str) -> dict[str, Any]:
    """Convert plain text to ADF document with paragraphs split on double newlines."""
    paragraphs = re.split(r"\n{2,}", text.strip()) if text.strip() else [""]
    content = []
    for para in paragraphs:
        lines = para.split("\n")
        inline: list[dict[str, Any]] = []
        for i, line in enumerate(lines):
            if i > 0:
                inline.append({"type": "hardBreak"})
            inline.append({"type": "text", "text": line})
        content.append({"type": "paragraph", "content": inline})

    return {"type": "doc", "version": 1, "content": content}


def markdown_to_adf(markdown: str) -> dict[str, Any]:
    """Convert simple markdown to ADF.

    Supports headings (# / ## / ###), bullet lists (- / *), code blocks (```),
    and bold (**text**). Falls back to text_to_adf for anything else.
    """
    lines = markdown.split("\n")
    content: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip() or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            node: dict[str, Any] = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": "\n".join(code_lines)}],
            }
            if lang:
                node["attrs"] = {"language": lang}
            content.append(node)
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            content.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": _inline_markup(heading_match.group(2)),
            })
            i += 1
            continue

        # Bullet list
        if re.match(r"^[\-\*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[\-\*]\s+", lines[i]):
                item_text = re.sub(r"^[\-\*]\s+", "", lines[i])
                items.append({
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": _inline_markup(item_text)}],
                })
                i += 1
            content.append({"type": "bulletList", "content": items})
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Regular paragraph
        content.append({"type": "paragraph", "content": _inline_markup(line)})
        i += 1

    return {"type": "doc", "version": 1, "content": content or [_empty_paragraph()]}


def _inline_markup(text: str) -> list[dict[str, Any]]:
    """Parse inline bold (**text**) into ADF text nodes."""
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    nodes: list[dict[str, Any]] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            nodes.append({
                "type": "text",
                "text": part[2:-2],
                "marks": [{"type": "strong"}],
            })
        else:
            nodes.append({"type": "text", "text": part})
    return nodes or [{"type": "text", "text": ""}]


def _empty_paragraph() -> dict[str, Any]:
    return {"type": "paragraph", "content": [{"type": "text", "text": ""}]}


def adf_to_text(adf: dict[str, Any] | None) -> str:
    """Extract plain text from an ADF document."""
    if not adf:
        return ""
    return _extract_text(adf).strip()


def _extract_text(node: dict[str, Any]) -> str:
    if node.get("type") == "text":
        return node.get("text", "")
    if node.get("type") == "hardBreak":
        return "\n"
    parts = []
    for child in node.get("content", []):
        parts.append(_extract_text(child))
    separator = "\n" if node.get("type") in ("doc", "codeBlock", "bulletList") else ""
    result = separator.join(parts)
    if node.get("type") == "listItem":
        result = "- " + result
    if node.get("type") in ("paragraph", "heading", "codeBlock", "listItem"):
        result += "\n"
    return result
