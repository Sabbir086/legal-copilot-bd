# API Contracts — Current vs Planned

## Current routes (present in code)

| Method | Route | Purpose | Status |
|---|---|---|---|
| GET | `/` | Service identity and docs link | Implemented |
| GET | `/health` | Basic liveness response | Implemented |
| POST | `/api/v1/documents/analyze` | Upload PDF/DOCX, extract text, classify and run contract screening where applicable | Implemented; local prototype |
| POST | `/api/v1/chat/document` | Legacy M0 one-document chat endpoint | Implemented; retained for backward compatibility |
| POST | `/api/v1/conversations` | Create a device-scoped conversation | M1 implemented; Supabase required |
| GET | `/api/v1/conversations` | List conversations for the workspace UUID | M1 implemented; not authentication |
| GET | `/api/v1/conversations/{conversation_id}` | Load conversation, messages and attachment metadata | M1 implemented |
| DELETE | `/api/v1/conversations/{conversation_id}` | Permanently delete the conversation, child rows and private attachment objects | M1 implemented |
| POST | `/api/v1/conversations/{conversation_id}/attachments` | Attach multiple PDF/DOCX/images and prepare context | M1 implemented |
| POST | `/api/v1/conversations/{conversation_id}/messages` | General legal chat with optional multi-attachment context | M1 implemented; Gemini required |
| POST | `/api/v1/legal/search` | Keyword search over local `sources.json` discovery records | Implemented; placeholder-only results, not legal research verification |
| POST | `/api/v1/memoranda/{document_id}/pdf` | Generate a preliminary PDF from submitted risk data | Implemented; preliminary only |

## Planned API surface (not implemented)

### Authentication and secure ownership (M8)

- Supabase Auth sign-up/sign-in/session refresh and sign-out.
- Replace caller-supplied `X-Workspace-ID` with verified JWT-derived user identity.
- Per-user Row Level Security policies and ownership tests for every conversation, message, attachment and Storage object.
- Account export, retention settings and audited deletion.

### Attachments and document work

- `GET /api/v1/documents/{document_id}` — retrieve analysis/status only after ownership authorization.
- `POST /api/v1/documents/{document_id}/analyze` — request or retry structured analysis.
- `GET /api/v1/documents/{document_id}/analysis` — retrieve extracted facts, risks, evidence and analysis states.

### Legal research and verification

- `POST /api/v1/legal/research` — issue a jurisdiction-scoped RAG search.
- `POST /api/v1/legal/citations/verify` — independently verify a citation candidate against versioned authoritative sources.
- `POST /api/v1/cases/analyze` — analyze case materials with selected party role and source anchors.
- `POST /api/v1/memoranda` — create a typed memorandum from completed, evidence-bearing workflow output.

All planned routes require verified authentication/authorization, rate limiting, structured error handling and audit events before public exposure. The existing M1 conversation routes are a device-scoped prototype and must not be treated as authenticated multi-user access.
