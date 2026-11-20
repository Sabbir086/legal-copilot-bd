"""Lightweight document-type classification for Bangladesh-focused documents.

Classification is a routing hint, not a legal conclusion or authenticity check.
"""
from __future__ import annotations

import re
import unicodedata


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", value).casefold()


def classify_document(pages: list[dict]) -> dict:
    text = _norm("\n".join(page.get("text", "") for page in pages))

    land_terms = [
        "খতিয়ান", "খতিয়ান", "নামজারি", "মৌজা", "জে এল", "জে.এল", "দাগের",
        "দাগ নং", "ভূমি অফিস", "জমির শ্রেণী", "জমির শ্রেণি", "একর", "শতাংশ",
    ]
    deed_terms = ["সাফ কবলা", "হেবা", "দানপত্র", "দলিল নং", "সাব রেজিস্ট্রি", "নিবন্ধন দলিল"]
    contract_terms = ["agreement", "whereas", "indemnify", "termination", "governing law", "চুক্তিপত্র", "চুক্তির পক্ষ"]
    court_terms = ["আদেশের তারিখ", "মামলা নং", "আদালত", "রায়", "রায়", "judgment", "order of the court"]

    scores = {
        "land_record": sum(1 for term in land_terms if term in text),
        "deed": sum(1 for term in deed_terms if term in text),
        "contract": sum(1 for term in contract_terms if term in text),
        "court_document": sum(1 for term in court_terms if term in text),
    }

    best_type = max(scores, key=scores.get)
    if scores[best_type] < 2:
        best_type = "other"

    labels = {
        "land_record": ("খতিয়ান / নামজারি রেকর্ড", "land_record_review"),
        "deed": ("জমির দলিল", "deed_review_pending"),
        "contract": ("চুক্তিপত্র", "contract_risk_screening"),
        "court_document": ("আদালতের নথি", "court_document_review_pending"),
        "other": ("অন্যান্য নথি", "general_document_review"),
    }
    label, route = labels[best_type]
    return {
        "document_type": best_type,
        "document_type_bn": label,
        "document_workflow": route,
        "classification_scores": scores,
        "classification_notice": (
            "স্বয়ংক্রিয় নথি-শ্রেণিবিন্যাস; নথির সত্যতা, মালিকানা বা আইনগত বৈধতা যাচাই নয়।"
        ),
    }
