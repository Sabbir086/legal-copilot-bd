# MyLegal AI — Architecture

## Product boundary

MyLegal AI (repository: `legal-copilot-bd`) is the independent AI Builders Congress legal-assistance project. It is not LDIS and does not implement LDIS / LandTech land-office registration workflows. Bangladesh is the default legal jurisdiction.

## Current implementation (M0 + M1 + M2 code)

- **Frontend:** Next.js App Router, React and Tailwind CSS; Bengali/English chat workspace with conversation history, AI Chat and Document Analysis views.
- **Backend:** FastAPI REST API; Gemini is called only by the backend. M2 document extraction/OCR itself does not require Gemini credentials.
- **Ingestion:** a shared signature-checked validator handles PDF, DOCX, PNG, JPG/JPEG and WEBP. It checks server-side size limits, extension/signature consistency, image decoder format, pixel/decompression limits and DOCX ZIP structure/expansion limits.
- **PDF:** PyMuPDF extracts selectable text page by page. Low-text/image-only pages are rendered under a pixel budget and sent to an `OCRProvider` interface. The local adapter calls Tesseract and reports missing binary/language data explicitly.
- **DOCX:** python-docx extracts paragraphs and table cells in document order. It records paragraph/table/row/cell/block indexes and offsets; DOCX page numbers remain `null` because reliable page coordinates are not available from the source format.
- **Images:** Pillow validates and normalizes supported image formats. OCR text, source text and any model/vision description are distinct provenance types. The M2 image-vision slot is explicitly `not_requested`; an OCR transcript is not represented as a vision-model analysis.
- **Classification/extraction:** deterministic, explainable rules produce type candidates and confidence/evidence. Pydantic schemas validate facts. A field value is persisted only with an exact source quote and locator; candidate facts require review. Statute/section strings are literal document text, not checked legal authorities.
- **Segmentation:** page/block/heading/clause-aware bounded segments include offsets, start/end locators and overlap metadata. These are document-context segments, not M3 legal corpus chunks and contain no vector embeddings.
- **Persistence:** Supabase PostgreSQL stores document/page/segment/fact/job metadata. Original files and rendered/normalized artifacts use the existing private `conversation-attachments` bucket under workspace/conversation/document-scoped object keys.
- **Worker:** a separate long-running Render Background Worker claims durable jobs using an atomic `FOR UPDATE SKIP LOCKED` RPC, refreshes its lease, validates stored bytes again, processes idempotently and persists terminal state. FastAPI only enqueues jobs and serves status/evidence APIs.
- **Workspace scope:** `X-Workspace-ID` is the M1/M2 device-scope UUID. It is **not** `auth.uid()`, a verified identity, or secure multi-user authentication. M8 must replace it with verified Supabase Auth identity and per-user RLS.

## M2 processing flow

```text
Browser / Next.js
  |-- M1 conversation attachment upload
  |-- Document Analysis polls status / displays evidence
  |-- existing AI Chat remains available
  v
FastAPI (Render API)
  |-- verifies extension + file signature + size/pixel/archive bounds
  |-- stores original in existing private Storage bucket
  |-- inserts M1 conversation_attachment unchanged in shape
  |-- upserts M0 documents row + durable M2 processing job
  |-- returns quickly with document_id and queued status
  |
  |-- GET status/details/analysis/pages/segments/facts; POST retry
  v
Supabase PostgreSQL + private Storage
  |-- documents (existing M0 table extended)
  |-- document_pages / document_segments / document_facts
  |-- document_processing_jobs (durable state + retry count + lock)
  |-- private originals and derived page/image PNGs
  ^
  |-- atomic job claim + lease heartbeat
Render Background Worker
  |-- downloads original and re-validates signature/MIME
  |-- PDF page extraction + OCR, DOCX block extraction, or image OCR
  |-- classification, exact-quote facts, bounded segments
  |-- stores normalized artifacts and evidence/provenance
  |-- updates M1 attachment parse status/context without dropping its row
```

## Processing states and transitions

`queued → processing → completed | partial | needs_ocr | ocr_unavailable | failed`

- `queued`: durable job inserted and waiting for a worker.
- `processing`: worker owns a lease; a heartbeat refreshes its lock while long OCR runs.
- `completed`: readable source/OCR text was extracted without a blocking/partial condition.
- `partial`: some content was processed, but one or more pages/OCR results failed, were unavailable or need review.
- `needs_ocr`: the content is image/scanned but OCR produced no usable text or no attempt could be made successfully.
- `ocr_unavailable`: required Tesseract binary/language data is unavailable and no other readable text is available.
- `failed`: malformed/unreadable content, unsupported content, storage/database/worker exception or exhausted job attempts. Error code/message remain visible.

Retries update the same job row; page/segment/fact IDs are deterministic for the same document and locator, and storage object names are deterministic. M2 does not create duplicate documents or attachment rows on retry.

## API routes

M0/M1 routes remain. M2 adds:

- `GET /api/v1/documents/{document_id}` — details and job metadata.
- `GET /api/v1/documents/{document_id}/status` — processing state, attempts and error.
- `GET /api/v1/documents/{document_id}/analysis` — classification, summary, facts, uncertainty and injection signals.
- `GET /api/v1/documents/{document_id}/pages?limit=25&offset=0` — paginated page/block extraction records.
- `GET /api/v1/documents/{document_id}/segments?limit=25&offset=0` — paginated context segments.
- `GET /api/v1/documents/{document_id}/facts?limit=25&offset=0` — paginated candidate facts.
- `POST /api/v1/documents/{document_id}/retry` — queue a retry if not already queued/processing.

All M2 endpoints require `X-Workspace-ID` and scope each read/write to that workspace. This matches M1 compatibility only; it is not a secure authentication boundary.

## Current API retained

- `GET /`, `GET /health`
- `POST /api/v1/conversations`, `GET /api/v1/conversations`, `GET /api/v1/conversations/{conversation_id}`, `DELETE /api/v1/conversations/{conversation_id}`
- `POST /api/v1/conversations/{conversation_id}/attachments`
- `POST /api/v1/conversations/{conversation_id}/messages`
- `POST /api/v1/documents/analyze` (legacy M0 route)
- `POST /api/v1/chat/document` (legacy M0 endpoint)
- `POST /api/v1/legal/search` (local placeholder source catalog only)
- `POST /api/v1/memoranda/{document_id}/pdf` (preliminary export)

## Target architecture after M3+

```text
Next.js conversational workspace
  -> FastAPI + Supabase Auth/JWT authorization
  -> LangGraph orchestration
       -> document intelligence + OCR (M2)
       -> Bangladesh legal RAG (M3; versioned laws + pgvector)
       -> risk/issue workflow + independent citation verification (M4)
       -> legal triage and case analysis (M5/M6)
       -> verified memorandum generation (M7)
  -> Supabase PostgreSQL + pgvector + private Storage
```

## Trust boundaries

- Every uploaded file, extracted text span and OCR span is untrusted data. Prompt-like instructions inside a document are detected as signals and never become system/developer instructions.
- Document findings require stable page/block/section anchors. Extracted text does not prove authenticity, truth, legal effect or completeness.
- OCR output is distinct from selectable source text and can contain recognition errors. Every OCR fact requires human review.
- Model/visual descriptions are distinct from source and OCR text. M2 does not currently generate persistent vision descriptions.
- Statute/section strings extracted from documents are literal strings, not verified law.
- M2 summaries are extractive previews, not model-generated legal opinions.
- Legal research findings require authoritative source IDs, jurisdiction and version metadata. M3/M4 are not implemented.

## Deployment environment

- **Vercel frontend:** `NEXT_PUBLIC_API_URL` points to the Render API origin. No Supabase secret or Gemini API key is configured in Vercel.
- **Render API:** existing `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` plus M2 safety/segment settings from `backend/.env.example`.
- **Render worker:** same Supabase URL and server-only Supabase secret as the API, plus OCR settings; use `backend/Dockerfile.worker` to install Tesseract and Bangla/English language packages. The worker does not need Gemini unless a future task adds LLM-based document summaries.
- `GET /health` reports only whether Supabase environment values are present; it is not a live database, storage, worker or OCR test.
