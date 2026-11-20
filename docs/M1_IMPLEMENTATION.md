# M1 Implementation Notes — Conversational Legal Workspace

## User flow

1. On first visit, the browser generates and stores a random UUID named `mylegal_workspace_id` in local storage.
2. The frontend sends this value as `X-Workspace-ID` on conversation API requests.
3. The user can start a general legal chat without an attachment.
4. PDF/DOCX, PNG/JPG/JPEG and WEBP attachments can be added to a conversation. PDF/DOCX are limited to 20 MB each; images are limited to 8 MB each and 12 MB total per conversation. PDF/DOCX are parsed into page text; images are stored and sent to Gemini as multimodal image input on chat turns.
5. Later turns include bounded recent conversation history and all conversation attachment context.
6. The user can reopen or permanently delete conversations and switch between AI Chat and Document Analysis views.

## API

- `POST /api/v1/conversations`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`
- `DELETE /api/v1/conversations/{conversation_id}`
- `POST /api/v1/conversations/{conversation_id}/attachments` (`multipart/form-data`, repeated `files` field)
- `POST /api/v1/conversations/{conversation_id}/messages` (`{ "message": "..." }`)

Every workspace route requires `X-Workspace-ID` containing a UUID. The API rejects missing or invalid values. This is only a prototype device scope, not a verified identity or an authentication boundary.

## Supabase

Migration order:

1. `001_initial_schema.sql`
2. `002_conversational_workspace.sql`

Migration 002 creates `conversations`, `conversation_messages`, and `conversation_attachments`, plus a private `conversation-attachments` Storage bucket. Run migration 001 only if it has not already been applied; migration 002 must be applied for M1. The FastAPI backend uses the server-only service-role/secret key. Do not put that key in a `NEXT_PUBLIC_` variable or frontend environment.

Required backend environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (value may be the recommended new Supabase secret key beginning `sb_secret_...`, or the legacy `service_role` key during transition)
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `CORS_ORIGINS`

`GET /health` returns `workspace_persistence: true` when both Supabase URL and key are present. This checks configuration presence, not a full database/storage integration test.

## Prototype security boundary

The workspace UUID is not authentication. It is stored in browser local storage and is supplied by the client; anyone who obtains or guesses it may impersonate that device workspace. Supabase RLS blocks direct browser table access, while FastAPI uses the server-side secret/service-role key and filters by workspace UUID. That elevated key bypasses RLS, so the API ownership check is the effective prototype boundary. M8 must replace this with verified Supabase Auth/JWT-derived ownership and `auth.uid()` RLS before confidential or production use.

## M1 boundaries

- File extraction currently runs synchronously during upload; there is no separate background job queue or live progress monitor yet.
- Images are sent as Gemini visual context but are not persisted as OCR text.
- Scanned PDF OCR, robust long-document chunking, formal summaries, risk detection workflow, legal source RAG, citation verification, case strategy and verified memoranda are later milestones.
- General legal chat provides preliminary information only and must not fabricate or label citations as verified.
