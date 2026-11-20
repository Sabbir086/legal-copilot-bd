from __future__ import annotations
import logging
import re
from typing import Any

from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _normalize_numbers(text: str) -> str:
    return text.translate(_BN_DIGITS)


def extract_section_numbers(text: str) -> list[str]:
    normalized = _normalize_numbers(text)
    matches = re.findall(r"(?i)(?:section|ধারা|সেকশন|u/s|under\s+section)\s*[:#-]?\s*(\d{1,3}[A-Z]?)(?!\w)", normalized)
    # Also accept a bare section number only when it is essentially the whole prompt.
    if not matches and re.fullmatch(r"\s*\d{1,3}[A-Z]?\s*", normalized):
        matches = [normalized.strip()]
    return list(dict.fromkeys(m.upper() for m in matches if 1 <= int(re.match(r"\d+", m).group()) <= 511))[:8]


def search_sections(query: str, match_count: int = 10) -> list[dict[str, Any]]:
    client = get_supabase_client()
    clean = _normalize_numbers(query).strip()
    result: list[dict[str, Any]] = []
    for section_number in extract_section_numbers(clean):
        try:
            exact = client.table("penal_code_sections").select(
                "section_number,title,chapter,section_text,punishment_excerpt,source_status,source_page_start,source_page_end,source_pdf,source_url,source_snapshot_date,verification_status"
            ).eq("section_number", section_number).limit(1).execute().data or []
            result.extend(exact)
        except Exception:
            logger.debug("Exact Penal Code section lookup failed", exc_info=True)
    seen = {item.get("section_number") for item in result}
    try:
        rpc = client.rpc("search_penal_code_sections", {
            "search_query": clean,
            "match_count": max(1, min(match_count, 20)),
        }).execute()
        for row in rpc.data or []:
            number = row.get("section_number")
            if number not in seen:
                result.append(row)
                seen.add(number)
    except Exception:
        logger.warning("Penal Code retrieval RPC unavailable; check migration and CSV import", exc_info=True)

    # The SQL full-text query combines words with AND. For incident narratives,
    # search individual English keywords as a fallback so one extra adjective
    # does not suppress otherwise relevant sections.
    if len(result) < match_count:
        keywords = []
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", clean):
            token = token.strip("'-").lower()
            if token and token not in keywords:
                keywords.append(token)
        for token in keywords[:8]:
            if len(result) >= match_count:
                break
            try:
                rpc = client.rpc("search_penal_code_sections", {
                    "search_query": token,
                    "match_count": min(5, match_count),
                }).execute()
                for row in rpc.data or []:
                    number = row.get("section_number")
                    if number not in seen:
                        result.append(row)
                        seen.add(number)
                    if len(result) >= match_count:
                        break
            except Exception:
                logger.debug("Single-keyword Penal Code fallback failed for %r", token, exc_info=True)
    return result[:match_count]


def classify_query(query: str) -> str:
    q = query.casefold()
    if any(word in q for word in ("ধারা", "সেকশন", "section", "u/s", "under section")) or re.fullmatch(r"\s*\d{1,3}[a-z]?\s*", _normalize_numbers(q)):
        return "section_lookup"
    if any(word in q for word in ("মামলার বয়ান", "মামলার বর্ণনা", "এজাহার", "fir", "case statement", "complaint", "বয়ান")):
        return "case_statement_analysis"
    if any(word in q for word in ("ঘটনা", "মারধর", "চুরি", "হত্যা", "প্রতারণা", "হুমকি", "assault", "theft", "murder", "fraud", "incident")):
        return "incident_to_sections"
    return "general_legal_information"


def format_retrieved_context(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching Penal Code section was retrieved from the imported database. Do not invent a section number or punishment."
    sections=[]
    for row in rows:
        number=row.get("section_number", "?")
        title=row.get("title") or ""
        body=str(row.get("section_text") or "")[:5000]
        punishment=str(row.get("punishment_excerpt") or "")[:1600]
        source_date=row.get("source_snapshot_date") or "unknown"
        pages=f"PDF pages {row.get('source_page_start')}-{row.get('source_page_end')}"
        sections.append(
            f"[STATUTORY SOURCE: Penal Code, 1860, section {number} — {title}]\n"
            f"Verbatim extracted text (do not treat as current-law verification):\n{body}\n"
            f"Punishment excerpt: {punishment or 'No separate punishment excerpt extracted; read the full section text.'}\n"
            f"Source snapshot: {source_date}; {pages}; status: {row.get('verification_status','needs_current_law_verification')}"
        )
    return "\n\n".join(sections)
