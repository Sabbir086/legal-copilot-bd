from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_SECTION_COLUMNS = (
    "section_number,title,chapter,section_text,punishment_excerpt,source_status,"
    "source_page_start,source_page_end,source_pdf,source_url,source_snapshot_date,verification_status"
)


class PenalCodeRetrievalError(RuntimeError):
    """Raised when the statutory database could not be queried reliably."""


def _normalize_numbers(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").translate(_BN_DIGITS)


def extract_section_numbers(text: str) -> list[str]:
    """Extract explicit Penal Code section references in Bangla and English.

    Handles forms such as `section 302`, `ধারা ৩০২`, `302 dhara ki?`,
    `302 ধারার শাস্তি`, `dafa 302`, `u/s 302` and a bare `302`.
    """
    normalized = _normalize_numbers(text).casefold()
    number = r"(\d{1,3}[a-z]?)"
    marker = (
        r"(?:under\s+section|section|sec\.?|u\s*/\s*s|penal\s+code|"
        r"ধারা|ধারার|ধারা\s*নং|সেকশন|সেকশনের|"
        r"dhara|dharar|dharā|dharār|dafa|dafar|dof[aā])"
    )
    optional_number_label = r"(?:\s*(?:no\.?|number|নং|নম্বর))?"
    matches: list[str] = []

    # Marker before the number: "ধারা ৩০২", "section no. 302", "u/s 302".
    before = re.findall(
        rf"(?i){marker}{optional_number_label}\s*[:#-]?\s*{number}(?![a-z0-9])",
        normalized,
    )
    matches.extend(before)

    # Number before the marker: "302 dhara ki?", "৩০২ ধারা", "302 ধারার শাস্তি".
    after = re.findall(
        rf"(?i)(?<![a-z0-9]){number}{optional_number_label}\s*{marker}(?![a-z])",
        normalized,
    )
    matches.extend(after)

    # A bare section number is unambiguous only when it is the whole prompt.
    if not matches and re.fullmatch(r"\s*\d{1,3}[a-z]?\s*", normalized):
        matches = [normalized.strip()]

    normalized_matches: list[str] = []
    for match in matches:
        digits = re.match(r"\d+", match)
        if not digits:
            continue
        value = int(digits.group())
        if 1 <= value <= 511:
            canonical = f"{value}{match[len(digits.group()):].upper()}"
            if canonical not in normalized_matches:
                normalized_matches.append(canonical)
    return normalized_matches[:8]


def _append_unique(target: list[dict[str, Any]], seen: set[str], rows: list[dict[str, Any]]) -> None:
    for row in rows:
        number = str(row.get("section_number", "")).strip().upper()
        if number and number not in seen:
            target.append(row)
            seen.add(number)


def _lookup_exact_section(client: Any, section_number: str) -> tuple[list[dict[str, Any]], bool, list[Exception]]:
    """Try direct equality and a case-insensitive exact pattern before RPC fallback."""
    failures: list[Exception] = []
    rows: list[dict[str, Any]] = []

    try:
        response = (
            client.table("penal_code_sections")
            .select(_SECTION_COLUMNS)
            .eq("section_number", section_number)
            .limit(1)
            .execute()
        )
        rows = response.data or []
    except Exception as exc:  # continue to RPC; it may still be available
        failures.append(exc)
        logger.warning("Direct Penal Code lookup failed for section %s", section_number, exc_info=True)

    if rows:
        return rows, True, failures

    # Some CSV importers preserve incidental spaces/case; query broadly, then
    # compare the normalized field value in Python so 302 cannot match 302A.
    try:
        response = (
            client.table("penal_code_sections")
            .select(_SECTION_COLUMNS)
            .ilike("section_number", f"%{section_number}%")
            .limit(20)
            .execute()
        )
        rows = [
            row for row in (response.data or [])
            if str(row.get("section_number", "")).strip().upper() == section_number
        ]
        return rows[:1], True, failures
    except Exception as exc:
        failures.append(exc)
        logger.warning("Case-insensitive Penal Code lookup failed for section %s", section_number, exc_info=True)
        return [], False, failures


def search_sections(query: str, match_count: int = 10) -> list[dict[str, Any]]:
    """Retrieve exact requested sections first, otherwise perform corpus search.

    Explicit section references never go through LLM keyword rewriting. A database
    outage raises PenalCodeRetrievalError instead of being misreported as no match.
    """
    client = get_supabase_client()
    clean = _normalize_numbers(query).strip()
    limit = max(1, min(match_count, 20))
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    explicit_sections = extract_section_numbers(clean)

    if explicit_sections:
        query_succeeded = False
        rpc_failures: list[Exception] = []
        for section_number in explicit_sections:
            exact_rows, exact_succeeded, _exact_failures = _lookup_exact_section(client, section_number)
            query_succeeded = query_succeeded or exact_succeeded
            _append_unique(result, seen, exact_rows)

            if not exact_rows:
                # Search only the number. Searching the whole sentence with an AND
                # tsquery can miss a valid row because of words such as "dhara ki".
                try:
                    response = client.rpc(
                        "search_penal_code_sections",
                        {"search_query": section_number, "match_count": 2},
                    ).execute()
                    query_succeeded = True
                    matching = [
                        row for row in (response.data or [])
                        if str(row.get("section_number", "")).strip().upper() == section_number
                    ]
                    _append_unique(result, seen, matching)
                except Exception as exc:
                    rpc_failures.append(exc)
                    logger.warning("Exact Penal Code RPC lookup failed for section %s", section_number, exc_info=True)

        if result:
            return result[:limit]
        if not query_succeeded and rpc_failures:
            raise PenalCodeRetrievalError(
                "Supabase Penal Code table/RPC could not be queried for an explicit section."
            ) from rpc_failures[-1]
        # The database responded, but this exact section number is not in the corpus.
        return []

    successful_queries = 0
    try:
        response = client.rpc(
            "search_penal_code_sections",
            {"search_query": clean, "match_count": limit},
        ).execute()
        successful_queries += 1
        _append_unique(result, seen, response.data or [])
    except Exception as exc:
        logger.warning("Penal Code retrieval RPC failed for the full query", exc_info=True)
        first_error: Exception | None = exc

    # The SQL full-text query combines words with AND. For incident narratives,
    # search individual English keywords so an extra adjective does not suppress matches.
    keywords: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", clean):
        token = token.strip("'-").lower()
        if token and token not in keywords:
            keywords.append(token)

    for token in keywords[:8]:
        if len(result) >= limit:
            break
        try:
            response = client.rpc(
                "search_penal_code_sections",
                {"search_query": token, "match_count": min(5, limit)},
            ).execute()
            successful_queries += 1
            _append_unique(result, seen, response.data or [])
        except Exception:
            logger.debug("Single-keyword Penal Code fallback failed for %r", token, exc_info=True)

    if successful_queries == 0:
        raise PenalCodeRetrievalError(
            "Supabase Penal Code retrieval RPC is unavailable; no reliable search result can be returned."
        ) from locals().get("first_error")

    return result[:limit]


def classify_query(query: str) -> str:
    q = _normalize_numbers(query).casefold()
    if extract_section_numbers(q):
        return "section_lookup"
    if any(word in q for word in ("ধারা", "সেকশন", "section", "u/s", "under section", "dhara", "dharar", "dafa", "dafar")):
        return "section_lookup"
    if any(word in q for word in ("মামলার বয়ান", "মামলার বর্ণনা", "এজাহার", "fir", "case statement", "complaint", "বয়ান")):
        return "case_statement_analysis"
    if any(word in q for word in ("ঘটনা", "মারধর", "চুরি", "হত্যা", "প্রতারণা", "হুমকি", "assault", "theft", "murder", "fraud", "incident")):
        return "incident_to_sections"
    return "general_legal_information"


def format_retrieved_context(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching Penal Code section was retrieved from the imported database. Do not invent a section number or punishment."
    sections = []
    for row in rows:
        number = row.get("section_number", "?")
        title = row.get("title") or ""
        body = str(row.get("section_text") or "")[:5000]
        punishment = str(row.get("punishment_excerpt") or "")[:1600]
        source_date = row.get("source_snapshot_date") or "unknown"
        pages = f"PDF pages {row.get('source_page_start')}-{row.get('source_page_end')}"
        sections.append(
            f"[STATUTORY SOURCE: Penal Code, 1860, section {number} — {title}]\n"
            f"Verbatim extracted text (do not treat as current-law verification):\n{body}\n"
            f"Punishment excerpt: {punishment or 'No separate punishment excerpt extracted; read the full section text.'}\n"
            f"Source snapshot: {source_date}; {pages}; status: {row.get('verification_status', 'needs_current_law_verification')}"
        )
    return "\n\n".join(sections)
