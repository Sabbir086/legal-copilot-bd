# API Contracts — Current vs Planned

## Current routes (present in code)

| Method | Route | Purpose | Status |
|---|---|---|---|
| GET | `/` | Service identity and docs link | Implemented |
| GET | `/health` | Basic liveness response | Implemented |
| POST | `/api/v1/documents/analyze` | Upload PDF/DOCX, extract text, classify and run contract screening where applicable | Implemented; local prototype |
| POST | `/api/v1/chat/document` | Ask a question about one uploaded document, with bounded short history supplied by frontend | Implemented; not a general chat API |
| POST | `/api/v1/legal/search` | Keyword search over local `sources.json` discovery records | Implemented; placeholder-only results, not legal research verification |
| POST | `/api/v1/memoranda/{document_id}/pdf` | Generate a preliminary PDF from submitted risk data | Implemented; preliminary only |

## Planned API surface (not implemented)

### Conversations

- `POST /api/v1/conversations` — create a conversation with jurisdiction and language preference.
- `GET /api/v1/conversations` — list conversations belonging to the authenticated user.
- `GET /api/v1/conversations/{conversation_id}` — retrieve messages and attachment metadata for an authorized user.
- `POST /api/v1/conversations/{conversation_id}/messages` — send a normal message, with or without attachment context.
- `DELETE /api/v1/conversations/{conversation_id}` — delete a conversation and apply its attachment-retention policy.

### Attachments and document work

- `POST /api/v1/conversations/{conversation_id}/attachments` — attach one or more allowed files to an authorized conversation.
- `GET /api/v1/documents/{document_id}` — retrieve analysis/status only after ownership authorization.
- `POST /api/v1/documents/{document_id}/analyze` — request or retry structured analysis.
- `GET /api/v1/documents/{document_id}/analysis` — retrieve extracted facts, risks, evidence and analysis states.

### Legal research and verification

- `POST /api/v1/legal/research` — issue a jurisdiction-scoped RAG search.
- `POST /api/v1/legal/citations/verify` — independently verify a citation candidate against versioned authoritative sources.
- `POST /api/v1/cases/analyze` — analyze case materials with selected party role and source anchors.
- `POST /api/v1/memoranda` — create a typed memorandum from completed, evidence-bearing workflow output.

All planned routes require authentication, authorization, rate limiting, structured error handling and audit events before public exposure.
