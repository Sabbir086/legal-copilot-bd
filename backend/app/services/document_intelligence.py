"""Evidence-grounded, explainable document classification for M2.

This layer does not verify authenticity, legal effect or whether a cited law is current.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.schemas.document_intelligence import DocumentClassification


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", value).casefold()


RULES: dict[str, list[str]] = {
    "contract": ["agreement", "whereas", "indemnity", "indemnify", "termination", "governing law", "চুক্তিপত্র", "চুক্তির পক্ষ", "পক্ষদ্বয়", "party of the first part"],
    "court_filing": ["plaint", "petition", "written statement", "plaintiff", "defendant", "cause of action", "মামলার আরজি", "আরজির বিবরণ", "বাদী", "বিবাদী", "আবেদনকারী", "প্রতিবাদী"],
    "court_order": ["judgment", "order of the court", "it is ordered", "decree", "আদেশের তারিখ", "আদেশ প্রদান", "রায়", "রায়", "আদালতের আদেশ"],
    "legal_notice": ["legal notice", "demand notice", "notice to", "hereby demand", "আইনি নোটিশ", "লিগ্যাল নোটিশ", "দাবি নোটিশ", "নোটিশ প্রদান"],
    "statute": ["act,", "act no", "ordinance", "regulation", "rules made", "আইন,", "অধ্যাদেশ", "বিধিমালা", "প্রজ্ঞাপন"],
    "correspondence": ["dear sir", "dear madam", "sincerely", "regards", "subject:", "বিষয়:", "প্রিয় মহোদয়", "ধন্যবাদান্তে"],
    "identity_supporting_evidence": ["national identity", "identity card", "passport no", "date of birth", "জাতীয় পরিচয়পত্র", "জন্ম তারিখ", "পাসপোর্ট নং", "এনআইডি"],
    # M1 routing compatibility; these types are kept distinct but are not M2 legal classes.
    "land_record": ["খতিয়ান", "খতিয়ান", "নামজারি", "মৌজা", "জে এল", "দাগ নং", "ভূমি অফিস", "জমির শ্রেণী", "জমির শ্রেণি"],
    "deed": ["সাফ কবলা", "হেবা", "দানপত্র", "দলিল নং", "সাব রেজিস্ট্রি", "নিবন্ধন দলিল"],
}

LABELS = {
    "contract": "চুক্তিপত্র / Agreement",
    "court_filing": "আদালতে দাখিলকৃত নথি / Court filing",
    "court_order": "আদালতের আদেশ / রায়",
    "legal_notice": "আইনি নোটিশ / Demand letter",
    "statute": "আইন / বিধিমালা",
    "correspondence": "চিঠিপত্র / Correspondence",
    "identity_supporting_evidence": "পরিচয় / সহায়ক প্রমাণ",
    "land_record": "খতিয়ান / নামজারি রেকর্ড",
    "deed": "জমির দলিল",
    "other": "অন্যান্য / অনির্ধারিত নথি",
}


def classify_document(pages: list[dict[str, Any]]) -> dict[str, Any]:
    full_text = "\n".join(str(page.get("text", "")) for page in pages)
    normalized = _norm(full_text)
    scores = {label: sum(1 for term in terms if _norm(term) in normalized) for label, terms in RULES.items()}
    ranked = sorted(scores.items(), key=lambda pair: (pair[1], pair[0]), reverse=True)
    best_type, best_score = ranked[0] if ranked else ("other", 0)
    if best_score == 0:
        best_type = "other"
        confidence = 0.15 if normalized else 0.0
    else:
        max_rules = max(1, len(RULES[best_type]))
        confidence = min(0.96, 0.45 + 0.13 * best_score + 0.1 * (best_score / max_rules))
        if len(ranked) > 1 and ranked[1][1] == best_score:
            confidence = max(0.35, confidence - 0.18)

    evidence: list[dict[str, Any]] = []
    if best_type != "other":
        terms = RULES[best_type]
        for page_index, page in enumerate(pages, start=1):
            text = str(page.get("text", ""))
            norm_text = _norm(text)
            matched = next((term for term in terms if _norm(term) in norm_text), None)
            if matched:
                quote = _quote_around(text, matched)
                locator = page.get("locator") or {"kind": "page_text", "page_number": page.get("page", page_index)}
                evidence.append({"evidence_locator": locator, "quote": quote, "matched_rule": matched})
            if len(evidence) >= 4:
                break
    alternatives = [
        {"document_type": label, "score": score}
        for label, score in ranked[1:4] if score > 0
    ]
    explanation = (
        f"Matched {best_score} classification rule(s) for {best_type}; this is a routing hint, not a legal conclusion."
        if best_type != "other" else "No supported document-type rule matched; classification remains unknown."
    )
    classification = DocumentClassification(
        document_type=best_type, confidence=confidence, evidence=evidence,
        alternatives=alternatives, explanation=explanation,
    )
    result = classification.model_dump()
    result.update({
        "document_type_bn": LABELS[best_type],
        "document_workflow": {
            "contract": "contract_risk_screening",
            "land_record": "land_record_review",
            "deed": "deed_review_pending",
            "court_filing": "court_filing_review",
            "court_order": "court_order_review",
            "legal_notice": "notice_review",
        }.get(best_type, "general_document_review"),
        "classification_scores": scores,
        "classification_notice": "স্বয়ংক্রিয় নথি-শ্রেণিবিন্যাস; নথির সত্যতা, মালিকানা বা আইনগত বৈধতা যাচাই নয়।",
    })
    return result


def _quote_around(text: str, term: str, radius: int = 120) -> str:
    haystack = _norm(text)
    needle = _norm(term)
    index = haystack.find(needle)
    # Normalization can change offsets; choose a short full line rather than fabricate offsets.
    if index < 0:
        return text.strip()[:240]
    for line in text.splitlines():
        if needle in _norm(line):
            return line.strip()[:240]
    return text.strip()[:240]
