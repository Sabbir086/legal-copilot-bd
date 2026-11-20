# API Contracts — Current vs Planned

All routes below are mounted under `/api/v1` unless explicitly shown. M1/M2 workspace routes require `X-Workspace-ID`, which is a temporary browser/device scope identifier, not authentication.

## Existing routes retained

| Method | Route | Purpose | Status |
|---|---|---|---|
| GET | `/` | Service identity and docs link | Implemented |
| GET | `/health` | Basic liveness + presence of Supabase settings | Implemented; not an integration check |
| POST | `/documents/analyze` | Legacy M0 PDF/DOCX analysis workflow | Retained; now uses M2 parser/pipeline synchronously |
| POST | `/chat/document` | Legacy M0 one-document chat endpoint | Retained |
| POST | `/conversations` | Create a device-scoped conversation | M1 retained |
| GET | `/conversations` | List conversations for the workspace UUID | M1 retained |
| GET | `/conversations/{conversation_id}` | Load conversation, messages and attachment metadata | M1 retained; adds document ID/status |
| DELETE | `/conversations/{conversation_id}` | Delete conversation and child attachment rows/storage objects | M1 retained |
| POST | `/conversations/{conversation_id}/attachments` | Upload multiple PDF/DOCX/images; store originals and enqueue M2 jobs | M1-compatible; returns queued document ID |
| POST | `/conversations/{conversation_id}/messages` | General legal chat with attachment context | M1 retained; context bounded and wrapped as untrusted evidence |
| POST | `/legal/search` | Keyword search over local `sources.json` discovery records | Placeholder only; not verified legal research |
| POST | `/memoranda/{document_id}/pdf` | Generate a preliminary PDF from submitted risk data | Preliminary only |

## M2 document-intelligence routes

All IDs are UUIDs. Responses are bounded; paginated routes accept `limit` 1–50 (default 25) and `offset` 0–100000. Page text fields are clipped to `MAX_DOCUMENT_RESPONSE_TEXT_CHARS`; omitted character counts are reported when clipped.

| Method | Route | Response / behavior |
|---|---|---|
| GET | `/documents/{document_id}` | Document detail, filename, status, job and last error |
| GET | `/documents/{document_id}/status` | State, attempt count, error code/message and update time |
| GET | `/documents/{document_id}/analysis` | Classification, extractive summary/provenance, facts, uncertainty and prompt-injection signals |
| GET | `/documents/{document_id}/pages?limit=25&offset=0` | Paginated page or DOCX block records; source/OCR fields remain separate |
| GET | `/documents/{document_id}/segments?limit=25&offset=0` | Paginated bounded context segments with source locators/overlap metadata |
| GET | `/documents/{document_id}/facts?limit=25&offset=0` | Paginated candidate facts with evidence locator, exact quote, confidence and review flag |
| POST | `/documents/{document_id}/retry` | Re-queues a failed/partial/completed/OCR-blocked processing job; conflicts if already queued/processing |

### Common request headers

```http
X-Workspace-ID: 00000000-0000-4000-8000-000000000001
```

The UUID above is an example only. It must be the workspace identifier already used by the M1 browser. It is not a Supabase Auth user ID.

### Example status request

```bash
curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/status"
```

Example response:

```json
{
  "document_id": "00000000-0000-4000-8000-000000000002",
  "status": "partial",
  "attempts": 1,
  "error_code": "partial",
  "error_message": "Page 3: Tesseract language data missing: ben.",
  "updated_at": "2026-11-20T12:00:00+00:00"
}
```

### Example evidence request

```bash
curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/facts?limit=25&offset=0"
```

A fact contains a field/value (or `null` when unsupported), `evidence_locator`, `supporting_quote`, confidence, extraction method, `needs_review` and an uncertainty reason. Quotes are validated as exact substrings of the corresponding extracted source block before persistence.

### Example retry request

```bash
curl -X POST -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/retry"
```

Success returns `202`-style queue semantics in the response body (`status: queued`, `job_id`). The implementation currently returns HTTP 200 for compatibility. Invalid IDs/workspace header return 400; missing or out-of-scope documents return 404; unavailable persistence returns 503; a non-retryable active job returns 409.

## Worker contract

FastAPI upload persists the original attachment to the existing private `conversation-attachments` bucket and queues `document_processing_jobs`; it does not wait for OCR. A separate worker runs:

```bash
cd backend
python -m app.workers.document_worker
```

Single-job smoke command:

```bash
python -m app.workers.document_worker --once
```

The worker requires the same backend-only `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as the API. It also needs Tesseract plus requested language data in its execution image/environment. Job claiming and lease heartbeat are database-backed.

## Planned routes (M3–M8; not implemented)

- `POST /legal/research` — jurisdiction-scoped RAG.
- `POST /legal/citations/verify` — independent verification against versioned authoritative sources.
- `POST /cases/analyze` — party-role and evidence-linked case analysis.
- `POST /memoranda` — typed verified memorandum creation.
- Supabase Auth/session routes and authenticated user-owned document APIs (M8).

The current M1/M2 workspace routes are a prototype, not secure multi-user access. M2 does not verify statute currency or provide legal advice.
