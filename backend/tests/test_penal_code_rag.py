from __future__ import annotations

import pytest

from app.services import penal_code_rag as rag


SECTION_302 = {
    "section_number": "302",
    "title": "Punishment for murder",
    "chapter": "CHAPTER XVI",
    "section_text": "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
    "punishment_excerpt": "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
    "source_status": "text_present_in_source",
    "source_page_start": 93,
    "source_page_end": 93,
    "source_pdf": "Penal-Code-1860.pdf",
    "source_url": "https://bdlaws.minlaw.gov.bd/print_sections_all.php?id=11",
    "source_snapshot_date": "2013-08-26",
    "verification_status": "needs_current_law_verification",
}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("302 dhara ki?", ["302"]),
        ("ধারা ৩০২", ["302"]),
        ("৩০২ ধারার শাস্তি কী?", ["302"]),
        ("section no. 302", ["302"]),
        ("u/s 302", ["302"]),
        ("dafa 302", ["302"]),
        ("302A dhara", ["302A"]),
        ("302", ["302"]),
        ("ধারা ৫১২", []),
    ],
)
def test_extract_section_numbers_bangla_and_transliterated(query: str, expected: list[str]) -> None:
    assert rag.extract_section_numbers(query) == expected


def test_classifies_transliterated_section_question_as_lookup() -> None:
    assert rag.classify_query("302 dhara ki?") == "section_lookup"


class _Response:
    def __init__(self, data):
        self.data = data


class _RpcCall:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return _Response(self.data)


class _TableQuery:
    def __init__(self, client, table_name: str):
        self.client = client
        self.table_name = table_name
        self.filters = []

    def select(self, _columns: str):
        return self

    def eq(self, column: str, value: str):
        self.filters.append(("eq", column, value))
        return self

    def ilike(self, column: str, value: str):
        self.filters.append(("ilike", column, value))
        return self

    def limit(self, _count: int):
        return self

    def execute(self):
        self.client.table_calls.append(self.filters[:])
        for operator, column, value in self.filters:
            if column == "section_number" and operator == "eq" and value == "302":
                return _Response([SECTION_302])
        return _Response([])


class _Client:
    def __init__(self):
        self.table_calls = []
        self.rpc_calls = []

    def table(self, table_name: str):
        assert table_name == "penal_code_sections"
        return _TableQuery(self, table_name)

    def rpc(self, function_name: str, params: dict):
        self.rpc_calls.append((function_name, params))
        return _Response([])


def test_search_sections_uses_direct_exact_lookup_for_transliterated_prompt(monkeypatch) -> None:
    client = _Client()
    monkeypatch.setattr(rag, "get_supabase_client", lambda: client)

    rows = rag.search_sections("302 dhara ki?")

    assert len(rows) == 1
    assert rows[0]["section_number"] == "302"
    assert client.table_calls[0] == [("eq", "section_number", "302")]
    # The exact row was returned, so there is no need to rely on fuzzy keyword search.
    assert client.rpc_calls == []


def test_search_sections_uses_number_only_rpc_after_direct_miss(monkeypatch) -> None:
    class MissTableQuery(_TableQuery):
        def execute(self):
            self.client.table_calls.append(self.filters[:])
            return _Response([])

    class RpcFallbackClient(_Client):
        def table(self, table_name: str):
            assert table_name == "penal_code_sections"
            return MissTableQuery(self, table_name)

        def rpc(self, function_name: str, params: dict):
            self.rpc_calls.append((function_name, params))
            if params["search_query"] == "302":
                return _RpcCall([SECTION_302])
            return _RpcCall([])

    client = RpcFallbackClient()
    monkeypatch.setattr(rag, "get_supabase_client", lambda: client)

    rows = rag.search_sections("302 dhara ki?")

    assert [row["section_number"] for row in rows] == ["302"]
    assert client.rpc_calls == [
        ("search_penal_code_sections", {"search_query": "302", "match_count": 2})
    ]


def test_search_sections_raises_when_database_cannot_be_queried(monkeypatch) -> None:
    class BrokenQuery(_TableQuery):
        def execute(self):
            raise RuntimeError("database unavailable")

    class BrokenClient(_Client):
        def table(self, table_name: str):
            return BrokenQuery(self, table_name)

        def rpc(self, function_name: str, params: dict):
            raise RuntimeError("RPC unavailable")

    monkeypatch.setattr(rag, "get_supabase_client", lambda: BrokenClient())

    with pytest.raises(rag.PenalCodeRetrievalError):
        rag.search_sections("302 dhara ki?")


def test_retrieved_context_contains_exact_source_content_and_page() -> None:
    context = rag.format_retrieved_context([SECTION_302])
    assert "section 302 — Punishment for murder" in context
    assert "Whoever commits murder" in context
    assert "PDF pages 93-93" in context
    assert "2013-08-26" in context
