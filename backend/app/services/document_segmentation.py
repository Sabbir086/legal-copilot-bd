from __future__ import annotations

import re
from typing import Any

HEADING_PATTERN = re.compile(
    r"^(?:[A-Z][A-Z0-9 .,:;()/-]{3,100}|(?i:section|clause|article)\s+[\w.-]+|(?:ধারা|অনুচ্ছেদ|দফা|শর্ত)\s*[০-৯0-9.\-]+).*$"
)
CLAUSE_PATTERN = re.compile(r"^\s*((?:\d+(?:\.\d+)*|[০-৯]+(?:\.[০-৯]+)*)[.)]?)\s+(.+)$")


def segment_blocks(blocks: list[dict[str, Any]], *, max_chars: int = 6000, overlap_chars: int = 300) -> list[dict[str, Any]]:
    """Create bounded evidence segments; overlap is explicit and source anchors remain stable."""
    max_chars = max(500, min(max_chars, 20000))
    overlap_chars = max(0, min(overlap_chars, max_chars // 4))
    segments: list[dict[str, Any]] = []
    buffer: list[tuple[str, dict[str, Any]]] = []
    size = 0
    heading: str | None = None
    clause: str | None = None
    pending_overlap = ""
    overlap_from: int | None = None

    def flush() -> None:
        nonlocal buffer, size, pending_overlap, overlap_from
        if not buffer:
            return
        content = "\n".join(text for text, _ in buffer).strip()
        source_items = [(text, locator) for text, locator in buffer if locator.get("kind") != "overlap"]
        if not source_items:
            buffer, size = [], 0
            return
        start_locator = source_items[0][1]
        end_locator = source_items[-1][1]
        segments.append({
            "segment_index": len(segments) + 1,
            "text": content,
            "parent_segment_id": None,
            "heading": heading,
            "clause_number": clause,
            "start_locator": start_locator,
            "end_locator": end_locator,
            "overlap": bool(pending_overlap),
            "overlap_from_segment_index": overlap_from,
            "overlap_prefix": pending_overlap,
            "character_count": len(content),
        })
        buffer, size = [], 0
        pending_overlap, overlap_from = "", None

    expanded_blocks: list[dict[str, Any]] = []
    for block in blocks:
        raw_text = str(block.get("text", ""))
        base_locator = dict(block.get("locator") or {"kind": "source_block"})
        base_offset = int(base_locator.get("start_offset") or 0)
        offset = 0
        for raw_line in raw_text.splitlines(keepends=True):
            leading = len(raw_line) - len(raw_line.lstrip())
            line = raw_line.strip()
            if line:
                locator = {
                    **base_locator,
                    "start_offset": base_offset + offset + leading,
                    "end_offset": base_offset + offset + leading + len(line),
                }
                expanded_blocks.append({**block, "text": line, "locator": locator})
            offset += len(raw_line)
        if raw_text and not raw_text.splitlines(keepends=True):
            expanded_blocks.append({**block, "text": raw_text.strip(), "locator": base_locator})

    for block in expanded_blocks:
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        base_locator = dict(block.get("locator") or {"kind": "source_block"})
        heading_match = HEADING_PATTERN.match(text)
        style_name = str(base_locator.get("style") or "").casefold()
        is_docx_heading = style_name.startswith("heading") or style_name in {"title", "subtitle"}
        clause_match = CLAUSE_PATTERN.match(text)
        if heading_match or is_docx_heading:
            flush()
            heading, clause = text[:180], None
        elif clause_match:
            clause = clause_match.group(1).rstrip(".)")
            if size > max_chars * 0.6:
                flush()

        # A single oversized paragraph is split with exact local offsets.
        local_start = 0
        while local_start < len(text):
            available = max_chars - size - (1 if buffer else 0)
            if available <= 0:
                previous_content = "\n".join(part for part, _ in buffer)
                previous_index = len(segments) + 1
                carry = previous_content[-overlap_chars:] if overlap_chars else ""
                flush()
                if carry:
                    pending_overlap = carry
                    overlap_from = previous_index
                    buffer = [(carry, {"kind": "overlap", "source_segment_index": previous_index})]
                    size = len(carry)
                available = max_chars - size - (1 if buffer else 0)
            take = min(len(text) - local_start, max(1, available))
            part = text[local_start:local_start + take]
            source_locator = {
                **base_locator,
                "start_offset": int(base_locator.get("start_offset") or 0) + local_start,
                "end_offset": int(base_locator.get("start_offset") or 0) + local_start + take,
            }
            buffer.append((part, source_locator))
            size += len(part) + (1 if len(buffer) > 1 else 0)
            local_start += take
            if local_start < len(text):
                previous_content = "\n".join(part_text for part_text, _ in buffer)
                previous_index = len(segments) + 1
                carry = previous_content[-overlap_chars:] if overlap_chars else ""
                flush()
                if carry:
                    pending_overlap = carry
                    overlap_from = previous_index
                    buffer = [(carry, {"kind": "overlap", "source_segment_index": previous_index})]
                    size = len(carry)
    flush()
    return segments
