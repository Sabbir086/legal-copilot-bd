# Target Data Model (M0)

The current Supabase migration contains an initial document/analysis/legal-source schema. It is not yet connected to the live application. The following is the target logical model for later migrations; it is not a claim that these tables already exist.

## Core entities

- **profiles** — authenticated user profile and preferences (language, default jurisdiction).
- **conversations** — owner, title, jurisdiction, status, retention policy and timestamps.
- **messages** — conversation, role, content, model/agent metadata and timestamps.
- **attachments** — conversation/message association, private object key, MIME type, size, hash, scan status and retention state.
- **documents** — normalized representation of an attachment; document type, jurisdiction, parse state and page count.
- **document_pages** — page number, extracted text, OCR status, extraction confidence and source offsets.
- **document_facts** — typed facts such as party, date, amount, court, case number, statute reference and evidence locator.
- **analysis_runs** — workflow ID, agent versions, model ID, status and timestamps.
- **risk_findings** — distinct risk, category, severity, explanation, recommendation and document evidence locator.
- **case_files** — parties/roles, court, case number, procedural stage and linked documents.
- **legal_sources** — law/case/service metadata and jurisdiction.
- **legal_source_versions** — immutable version, full source text, hash, retrieval time, publication/effective dates and amendment relationships.
- **legal_chunks** — section/paragraph-level text and stable source locators.
- **legal_embeddings** — vector embedding, model/version and chunk reference.
- **citation_candidates** — citations extracted or proposed by agents.
- **citation_verifications** — exact matched source version, text match, amendment/status/applicability checks, verifier method, reviewer and timestamp.
- **memoranda** — structured report data, PDF object key, verification coverage and review timestamp.
- **audit_events** — security-relevant access, file lifecycle, analysis and deletion events.

## Key relationships

```text
profile 1--N conversations 1--N messages
conversation 1--N attachments
attachment 1--1 document 1--N document_pages
conversation/document 1--N analysis_runs
analysis_run 1--N risk_findings
risk_findings N--N legal_chunks (through evidence links)
legal_source 1--N legal_source_versions 1--N legal_chunks
legal_chunks 1--1/N legal_embeddings
analysis_run 1--N citation_candidates 1--N citation_verifications
analysis_run 1--N memoranda
```

## Storage and authorization invariants

- Every conversation, message, attachment, document and analysis record has an owner scope.
- A user can access only their own records unless explicit shared-case permissions are added.
- Legal source records are shared read-only only after source review; write access is restricted to ingestion/reviewer roles.
- Service-role credentials remain server-side and never reach the browser.
- Deleting a conversation triggers a documented attachment/report retention workflow.
- Embeddings inherit the same source/document access control as their parent chunk.
