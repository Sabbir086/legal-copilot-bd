# Data Model — M0/M1 with M2 document intelligence

The repo contains sequential migrations `001_initial_schema.sql`, `002_conversational_workspace.sql` and `003_document_intelligence.sql`. Never assume they are applied to a live Supabase project: inspect its migration history first. `001` already defines `public.documents`; M2 extends that table and does not create a competing `documents` table.

## Existing entities

- **documents** — M0 table (`id`, optional `user_id`, `file_name`, `file_path`, `file_type`, `jurisdiction`, `status`, `created_at`); extended by M2 with workspace/conversation/attachment linkage, document type/classification, summary/provenance, extraction counts, processing state, prompt-injection flag and errors.
- **conversations** — M1 table with workspace UUID, title, jurisdiction, language and timestamps.
- **conversation_messages** — M1 conversation, role, content, metadata and timestamps.
- **conversation_attachments** — M1 original filename, verified MIME, byte size, private object key, document-type hint, extracted legacy page JSON and legacy parse state. M2 preserves this table and its existing IDs/fields.

## M2 normalized entities

- **documents** — one normalized record per M1 attachment. `attachment_id` is unique; `workspace_id` and `conversation_id` retain current scope; `processing_status` tracks the pipeline. Existing M0 standalone documents with no attachment relationship remain valid.
- **document_pages** — page or source-block records. Stores `source_text` separately from `ocr_text`, plus combined display text, OCR state/engine/languages/confidence, image dimensions, optional private derived artifact key, stable locator JSONB and provenance JSONB. PDF `page_number` is real; DOCX page number stays null and uses paragraph/table/block anchors.
- **document_segments** — bounded chunks for reading/context only. Stores parent relationship, heading/clause, content, start/end locators, character count and overlap metadata. M2 does not store legal RAG embeddings.
- **document_facts** — candidate fact field/value, stable evidence locator, exact supporting quote, confidence, extraction method, review flag, uncertainty reason and provenance JSONB. `fact_key` makes retries idempotent.
- **document_processing_jobs** — durable queue row per document/job type, state, attempts/max attempts, error, timestamps and processing lease. Worker claims are atomic and lock-safe; heartbeat refreshes long OCR jobs.

## Relationships

```text
conversation 1--N conversation_attachments
conversation_attachment 1--1 documents (via unique attachment_id)
documents 1--N document_pages
documents 1--N document_segments (segments may reference a parent segment)
documents 1--N document_facts
documents 1--N document_processing_jobs (unique per job_type)
```

## Storage

- Original PDF/DOCX/image bytes remain in the existing private `conversation-attachments` bucket under the existing M1 workspace/conversation/attachment key.
- Derived page render/normalized PNG objects use deterministic keys of the form `{workspace_id}/{conversation_id}/{document_id}/derived/{artifact_type}/{page-or-normalized}.png` in the same private bucket.
- No bucket is made public. Database records store object keys, not public URLs.

## Scope and M8 migration

M2's `workspace_id` is copied from M1's caller-provided `X-Workspace-ID` device-scope UUID. `user_id` in the reused M0 `documents` row remains null until verified user identity exists. The workspace UUID is not equivalent to `auth.uid()` and must not be described as secure ownership.

M8 conversion plan:

1. Introduce Supabase Auth and require verified JWTs at the API boundary.
2. Backfill/associate each workspace and child row with verified `user_id` only after user confirmation/ownership proof; do not infer account identity from a UUID.
3. Add `user_id` to M1/M2 rows and storage ownership metadata.
4. Create and test per-user RLS policies for conversations, attachments, documents, pages, segments, facts and jobs.
5. Replace `X-Workspace-ID` authorization with JWT-derived `auth.uid()` scope; maintain only a time-bounded, audited migration compatibility path.
6. Review retention, deletion, service-role access and audit logging.

RLS is enabled on the new M2 child tables and direct anon/authenticated table grants are revoked; the server uses its service-role/secret key. This is still not a complete user authorization design because M1 has no verified auth identity.
