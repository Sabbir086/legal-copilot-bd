from __future__ import annotations

import re
from typing import Any

from app.schemas.document_intelligence import EvidenceFact


DATE_PATTERNS = [
    re.compile(r"(?<!\d)(?:\d{1,2}[/-]\d{1,2}[/-](?:19|20)?\d{2}|\d{4}-\d{2}-\d{2})(?!\d)"),
    re.compile(r"(?<!\w)(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", re.I),
    re.compile(r"(?<!\w)[০-৯]{1,2}[/-][০-৯]{1,2}[/-][০-৯]{2,4}(?!\w)"),
]
AMOUNT_PATTERN = re.compile(
    r"(?:৳\s*(?:\d{1,3}(?:,\d{2})*(?:,\d{3})?|\d+)(?:\.\d{1,2})?|(?:BDT|Tk\.?|টাকা)\s*\d[\d,]*(?:\.\d{1,2})?|\d[\d,]*(?:\.\d{1,2})?\s*(?:BDT|Tk\.?|টাকা))",
    re.I,
)
STATUTE_PATTERN = re.compile(r"(?:ধারা|section|sec\.?)\s*[০-৯0-9A-Za-z()./-]+(?:\s+(?:of|এর)\s+[^,;.!\n]{1,90})?", re.I)
CASE_PATTERN = re.compile(r"(?:case|suit|মামলা|পিটিশন|petition)\s*(?:no\.?|number|নং)?\s*[:：#-]?\s*[A-Za-z/-]*[০-৯0-9][০-৯0-9A-Za-z/.-]{0,40}", re.I)
COURT_PATTERN = re.compile(r"(?:Supreme Court[^\n,;]{0,100}|(?:District|Sessions|Judge|Magistrate|High Court)[^\n,;]{0,80}Court|[\u0980-\u09FF]{2,30}(?: জেলা)? জজ আদালত|আদালত[^\n,;]{0,70})", re.I)
DISTRICT_PATTERN = re.compile(r"(?:district|জেলা)\s*[:：-]?\s*([^\n,;]{2,70})", re.I)

PARTY_PATTERNS = [
    ("party.plaintiff", re.compile(r"(?:plaintiff|বাদী|আবেদনকারী)\s*[:：-]?\s*([^\n,;]{2,100})", re.I)),
    ("party.defendant", re.compile(r"(?:defendant|বিবাদী|প্রতিবাদী)\s*[:：-]?\s*([^\n,;]{2,100})", re.I)),
    ("party.notice_sender", re.compile(r"(?:নোটিশদাতা|notice sender)\s*[:：-]?\s*([^\n,;]{2,100})", re.I)),
    ("party.notice_recipient", re.compile(r"(?:নোটিশগ্রহীতা|notice recipient)\s*[:：-]?\s*([^\n,;]{2,100})", re.I)),
]
TERM_FIELDS = {
    "clause.obligations": ["obligation", "shall", "must", "দায়িত্ব", "বাধ্য থাকিবে", "করতে হবে"],
    "clause.representations": ["representation", "represents", "warrants", "প্রতিনিধিত্ব"],
    "clause.warranties": ["warranty", "warranties", "গ্যারান্টি"],
    "clause.termination": ["termination", "terminate", "বাতিল", "সমাপ্তি"],
    "clause.indemnity": ["indemnity", "indemnify", "ক্ষতিপূরণ"],
    "clause.confidentiality": ["confidential", "confidentiality", "গোপনীয়তা"],
    "clause.payment": ["payment", "payable", "installment", "পরিশোধ", "টাকা প্রদান"],
    "clause.dispute_resolution": ["dispute resolution", "arbitration", "jurisdiction", "বিরোধ নিষ্পত্তি", "সালিশ"],
}


def _fact(field: str, value: str, quote: str, block: dict[str, Any], start: int, end: int, confidence: float = 0.78) -> dict[str, Any] | None:
    text = str(block.get("text", ""))
    if not quote or quote not in text:
        return None
    locator = dict(block.get("locator") or {"kind": "source_block"})
    base_offset = locator.get("start_offset") or 0
    locator.update({"start_offset": base_offset + start, "end_offset": base_offset + end})
    source_type = block.get("source_type", "source_text")
    method = "ocr_rule_based" if source_type == "ocr_text" else "rule_based"
    return EvidenceFact(
        field=field, value=value.strip(), evidence_locator=locator,
        supporting_quote=quote, confidence=confidence, extraction_method=method,
        needs_review=True, uncertainty_reason="Candidate extracted from source text; a human should confirm context and interpretation.",
    ).model_dump()


def extract_candidate_facts(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(item: dict[str, Any] | None) -> None:
        if not item:
            return
        key = (item["field"], str(item["value"]), str(item["supporting_quote"]))
        if key not in seen:
            seen.add(key)
            facts.append(item)

    for block in blocks:
        text = str(block.get("text", ""))
        if not text.strip():
            continue
        for pattern in DATE_PATTERNS:
            for match in pattern.finditer(text):
                add(_fact("date_or_deadline", match.group(0), match.group(0), block, match.start(), match.end(), 0.82))
        for match in AMOUNT_PATTERN.finditer(text):
            add(_fact("amount_or_currency", match.group(0), match.group(0), block, match.start(), match.end(), 0.82))
        for field, pattern in PARTY_PATTERNS:
            for match in pattern.finditer(text):
                quote = match.group(0).strip()
                add(_fact(field, match.group(1).strip(), quote, block, match.start(), match.end(), 0.72))
        for field, pattern in (("court_case_number", CASE_PATTERN), ("court_or_tribunal", COURT_PATTERN), ("statute_section_literal", STATUTE_PATTERN)):
            for match in pattern.finditer(text):
                value = match.group(0).strip()
                add(_fact(field, value, value, block, match.start(), match.end(), 0.7))
        for match in DISTRICT_PATTERN.finditer(text):
            add(_fact("district", match.group(1).strip(), match.group(0).strip(), block, match.start(), match.end(), 0.68))
        for field, terms in TERM_FIELDS.items():
            for term in terms:
                match = re.search(re.escape(term), text, re.I)
                if match:
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    if line_end < 0:
                        line_end = len(text)
                    quote = text[line_start:line_end].strip()
                    add(_fact(field, term, quote, block, line_start, line_end, 0.62))
                    break
        for field, pattern in (
            ("claim_or_allegation", re.compile(r"[^\n]{0,100}(?:allege[sd]?|claim(?:s|ed)?|অভিযোগ|দাবি)[^\n]{0,140}", re.I)),
            ("evidence_reference", re.compile(r"(?:exhibit|annexure|schedule|প্রদর্শনী|সংযুক্তি)\s*[A-Za-z0-9০-৯.-]*", re.I)),
            ("procedural_stage", re.compile(r"(?:hearing|trial|appeal|revision|summons|warrant|শুনানি|বিচার|আপিল|রিভিশন|সমন|পরোয়ানা)[^\n]{0,80}", re.I)),
        ):
            for match in pattern.finditer(text):
                quote = match.group(0).strip()
                add(_fact(field, quote, quote, block, match.start(), match.end(), 0.65))
    return validate_fact_quotes(facts, blocks)


def validate_fact_quotes(facts: list[dict[str, Any]], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Require an exact quote at the fact's source block and, when present, its offsets."""
    validated: list[dict[str, Any]] = []
    identity_fields = (
        "kind", "page_number", "paragraph_index", "table_index",
        "row_index", "cell_index", "block_index",
    )
    for raw in facts:
        fact = EvidenceFact.model_validate(raw)
        quote = fact.supporting_quote
        fact_locator = fact.evidence_locator.model_dump() if hasattr(fact.evidence_locator, "model_dump") else dict(fact.evidence_locator)
        match_found = False
        if quote:
            for block in blocks:
                source = str(block.get("text", ""))
                block_locator = dict(block.get("locator") or {})
                same_source = all(
                    fact_locator.get(key) is None or block_locator.get(key) == fact_locator.get(key)
                    for key in identity_fields
                )
                if not same_source or quote not in source:
                    continue
                start = fact_locator.get("start_offset")
                end = fact_locator.get("end_offset")
                if start is not None and end is not None:
                    try:
                        if source[int(start):int(end)].strip() != quote:
                            continue
                    except (TypeError, ValueError):
                        continue
                match_found = True
                break
        if not match_found:
            fact.value = None
            fact.supporting_quote = None
            fact.confidence = 0.0
            fact.needs_review = True
            fact.uncertainty_reason = (
                "The supporting quote could not be verified at the recorded source locator/offset; value withheld."
            )
        validated.append(fact.model_dump())
    return validated
