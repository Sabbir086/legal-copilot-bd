from pathlib import Path
import json

DATA_FILE = Path(__file__).resolve().parents[3] / "legal_data" / "statutes" / "sources.json"


def search_sources(query: str, jurisdiction: str = "BD") -> list[dict]:
    """Keyword discovery only. Records are never promoted to verified legal authority here."""
    if not DATA_FILE.exists():
        return []
    try:
        records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    terms = {term for term in query.casefold().split() if len(term) > 1}
    results = []
    for record in records:
        if record.get("jurisdiction") != jurisdiction:
            continue
        haystack = " ".join(str(value) for value in record.values()).casefold()
        score = sum(1 for term in terms if term in haystack)
        if score:
            item = dict(record)
            item["match_score"] = score
            item["verification_notice"] = (
                "Discovery lead only; exact primary-source text, amendment history, "
                "commencement, repeal and applicability are not verified."
            )
            results.append(item)
    return sorted(results, key=lambda item: item["match_score"], reverse=True)[:8]
