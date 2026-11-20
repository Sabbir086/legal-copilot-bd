# M2 Implementation Handoff — Document Intelligence, OCR & Evidence-Preserving Extraction

**Project:** MyLegal AI / Legal Copilot BD
**Milestone:** M2
**Status:** Partial completion — source implementation and backend tests delivered; external rollout and frontend validation pending.

## 1. Implementation summary

M2 adds a document-intelligence layer to the existing M0/M1 codebase without replacing the application. M1 conversation attachments and endpoints remain available. Uploads continue to store the original file in the existing private Supabase Storage bucket, then create a normalized document row and durable processing job. A separate worker performs OCR/extraction and stores normalized evidence records.

No live Supabase migration was executed. No secret `.env` file was created or overwritten. No M3 legal RAG/embedding work was started.

## 2. Implemented features

### Ingestion and validation

- Supported formats: PDF, DOCX, PNG, JPG/JPEG and WEBP.
- Server-side extension and magic/signature/decoder verification; browser-provided MIME is not trusted.
- PDF/DOCX size uses `MAX_UPLOAD_MB` (20 MB default); images are limited by `MAX_IMAGE_UPLOAD_MB` (8 MB default) and `MAX_IMAGE_PIXELS` (40 million default).
- Pillow image signature, dimension and decompression-bomb checks.
- DOCX ZIP entry count, total uncompressed bytes, compression ratio and unsafe path checks occur before XML is read.
- PDF page processing is capped by `MAX_PDF_PAGES` (500 default); page rasterization downscales before rendering to stay within the pixel budget.
- Original attachment rows and object keys are preserved. Derived page and normalized image PNGs use predictable workspace/conversation/document-scoped keys in the same private bucket.

### Extraction and OCR

- Selectable PDF text is extracted page by page with PyMuPDF.
- Low-text and image-only PDF pages are rendered and passed through the `OCRProvider` abstraction.
- `TesseractOCRProvider` checks the executable and requested language packs and returns OCR text, language list, engine and average word confidence. Default languages are `ben+eng`.
- Missing Tesseract or language data is reported as `ocr_unavailable` or `partial`, not successful empty text.
- DOCX paragraphs and tables are extracted in body reading order. Source locators include paragraph, table, row, cell, paragraph-within-cell and block index. Page number is `null` for DOCX.
- Image OCR stores dimensions, engine, requested languages, confidence and image locator. Image visual/vision-model analysis is independent; M2 marks it `not_requested`.
- Source text, OCR text and model/vision descriptions have separate provenance fields. The current M2 worker does not generate a persistent vision description.

### Classification and facts

Document classification supports `contract`, `court_filing`, `court_order`, `legal_notice`, `statute`, `correspondence`, `identity_supporting_evidence`, `other` and `unknown` fallback behavior. M1's earlier `land_record`/`deed` routing hints remain supported for backwards compatibility.

Rule-based candidate facts include parties and labeled roles, visible dates/deadlines (without deadline calculation), amounts/currency, court/case/district/procedural-stage references, literal statute/section strings, obligations/representations/warranties/termination/indemnity/confidentiality/payment/dispute-resolution indicators, allegations/claims and evidence references. Pydantic schemas validate the record. Exact quote validation checks each quote against extracted source blocks before it can be persisted. Candidate values are always reviewable; unsupported facts are withheld as `null` rather than invented.

### Segmentation and context bounds

M2 creates bounded document-context segments independent of vector embeddings. Segments preserve page/block offsets, DOCX block anchors, detected heading/clause, start/end locators and explicit overlap source metadata. A single oversized block is split at bounded character offsets. M1 chat attachment context has a configured total character budget; omitted material is stored in message metadata rather than silently truncated. Page retrieval is paginated and very long text fields are clipped with an omitted-character count.

### Lifecycle, APIs and UI

States: `queued`, `processing`, `partial`, `completed`, `failed`, `needs_ocr`, `ocr_unavailable`.

The API inserts a durable job and returns without waiting for OCR. The Render worker claims a job atomically through `claim_next_document_processing_job()` (`FOR UPDATE SKIP LOCKED`), refreshes its processing lease through a heartbeat RPC, downloads/revalidates the original, processes it and upserts deterministic page/segment/fact identifiers. Retrying reuses the existing job/document and deterministic object keys.

M2 API endpoints:

- `GET /api/v1/documents/{document_id}`
- `GET /api/v1/documents/{document_id}/status`
- `GET /api/v1/documents/{document_id}/analysis`
- `GET /api/v1/documents/{document_id}/pages?limit=25&offset=0`
- `GET /api/v1/documents/{document_id}/segments?limit=25&offset=0`
- `GET /api/v1/documents/{document_id}/facts?limit=25&offset=0`
- `POST /api/v1/documents/{document_id}/retry`

All M2 endpoints require the M1 `X-Workspace-ID` header and scope operations to that workspace. This is prototype compatibility, not authenticated identity.

The frontend adds processing status, document type, extractive summary/provenance, candidate facts/quotes/confidence/locators, uncertainty, prompt-injection warnings and retry. M1 AI Chat and attachment context remain.

## 3. Architecture and state transitions

```text
API upload
  -> validate actual content/signature/limits
  -> store original in private conversation-attachments bucket
  -> preserve conversation_attachments row
  -> upsert existing M0 documents row with attachment/workspace link
  -> enqueue document_processing_jobs row
  -> return document_id + queued

Render Background Worker
  -> atomically claim job (queued -> processing)
  -> heartbeat lease while processing
  -> revalidate original, parse PDF/DOCX/image, run OCR where needed
  -> classify, extract exact-quote facts, segment
  -> upload derived page/normalized PNG artifacts privately
  -> upsert pages/segments/facts and summary/provenance
  -> set job/document to completed | partial | needs_ocr | ocr_unavailable
  -> mark failed with error if processing cannot continue
```

`partial` means some material may be available but one or more pages/OCR results need review, failed or unavailable. `needs_ocr` means scanned/image content produced no usable text. `ocr_unavailable` means OCR could not be performed because the binary or language pack is absent and no selectable text is available. Errors are visible through status/details.

## 4. Migration instructions

New migration: `supabase/migrations/003_document_intelligence.sql`.

The M0 migration `001_initial_schema.sql` already creates `public.documents`. M2 extends it and adds `document_pages`, `document_segments`, `document_facts`, `document_processing_jobs`, claim/heartbeat RPCs, indexes and service-role-only grants. It backfills existing M1 `conversation_attachments` without renaming or dropping the M1 tables. Storage bucket `conversation-attachments` is kept private.

**Safe apply order:**

1. In Supabase Dashboard → SQL Editor (or your migration tool), first inspect migration history and confirm whether `001_initial_schema.sql` and `002_conversational_workspace.sql` have already been applied.
2. If both are already applied, apply **only** `003_document_intelligence.sql` once.
3. If the project is new and neither has been applied, apply `001_initial_schema.sql`, then `002_conversational_workspace.sql`, then `003_document_intelligence.sql`, each once.
4. If only one of `001`/`002` is applied, reconcile the actual schema/history before continuing. Do not blindly rerun a migration.
5. Back up the database and test the migration in a non-production Supabase project first. Do not apply via this code bundle; no live migration has been run.
6. Verify the private `conversation-attachments` bucket exists and remains private. Do not add public read policies.

The migration does not claim `workspace_id = auth.uid()`. It preserves the temporary M1 workspace-scope model. M8 must introduce verified Auth and user-bound policies.

## 5. Python and system dependencies

### Versions inspected before implementation

- The repository does not pin Python via `.python-version`/`pyproject.toml`, and `requirements.txt` uses version ranges rather than an exact Python runtime lock. The supplied execution environment is Python `3.13.5`.
- The repository does not pin Node via `.nvmrc`/`.node-version` or an `engines` field. The supplied execution environment is Node `v22.16.0` and npm `10.9.2`.
- `frontend/package.json` and its lockfile resolve Next.js `16.4.6`, React/React DOM `19.3.1`, TypeScript `5.9.3` and Tailwind CSS / `@tailwindcss/postcss` `4.3.5`; `lucide-react` resolves to `0.468.0`.
- The backend dependency ranges for FastAPI, Uvicorn, Pydantic, PyMuPDF, python-docx, Supabase, LangGraph and Gemini integration were retained. Pillow is the only new Python package requirement.

### Python package change

- Added `Pillow>=10.4,<13` to `backend/requirements.txt` for image verification, dimension checks and normalization.
- Existing FastAPI, Pydantic, PyMuPDF, python-docx, Supabase, LangGraph and Gemini dependencies are retained; no major dependency upgrade was made.

### macOS local OCR

```bash
brew install tesseract

# Confirm installed language packs:
tesseract --list-langs
```

Ensure both `ben` and `eng` appear. If one is missing, obtain the corresponding `ben.traineddata` / `eng.traineddata` from the official Tesseract tessdata repository and place them in the `tessdata` directory used by the Homebrew Tesseract installation (typically `$(brew --prefix)/share/tessdata`). Then run `tesseract --list-langs` again. The application reports missing language data as `ocr_unavailable`; it does not silently treat an empty extraction as success.

For Apple Silicon Homebrew, `brew --prefix` normally resolves under `/opt/homebrew`; on Intel Macs it normally resolves under `/usr/local`. Do not hardcode either path in application configuration.

### Render worker OCR image

`backend/Dockerfile.worker` installs the worker's OS packages:

- `tesseract-ocr`
- `tesseract-ocr-ben`
- `tesseract-ocr-eng`

The image installs `backend/requirements.txt` and starts the worker with:

```bash
python -m app.workers.document_worker
```

Recommended Render setup:

1. Add a new **Background Worker** service from the same repository.
2. Select Docker runtime.
3. Set Docker build context to `backend` and Dockerfile path to `backend/Dockerfile.worker` (if Render's form resolves paths from the repository root; with the service root set to `backend`, use `Dockerfile.worker`).
4. Keep the image `CMD` unchanged, or set the start command to `python -m app.workers.document_worker`.
5. Configure the worker's backend-only Supabase environment values and the M2 OCR settings below.
6. Deploy and inspect logs for `Tesseract`/worker startup and job processing. A running worker process is not proof of a database connection; verify an actual synthetic document job.

The FastAPI API service should stay responsive and does not need an in-memory background task. It uses the durable database job queue. The API's legacy synchronous `/api/v1/documents/analyze` route can invoke OCR inline; configure Tesseract on the API container too if that legacy route is expected to process scanned files.

## 6. Environment variables

New M2 settings added to `backend/.env.example` (non-secret defaults shown):

```dotenv
MAX_IMAGE_PIXELS=40000000
MAX_IMAGE_UPLOAD_MB=8
MAX_PDF_PAGES=500
OCR_LANGUAGES=ben+eng
TESSERACT_CMD=tesseract
OCR_DPI=200
OCR_MIN_TEXT_CHARS=30
DOCUMENT_SEGMENT_CHARS=6000
DOCUMENT_SEGMENT_OVERLAP_CHARS=300
DOCUMENT_WORKER_POLL_SECONDS=5
MAX_DOCUMENT_RESPONSE_TEXT_CHARS=12000
```

Existing backend-only variables remain required as appropriate:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=SET_IN_RENDER_BACKEND_AND_WORKER_ONLY
GEMINI_API_KEY=SET_IN_RENDER_API_ONLY
GEMINI_MODEL=gemini-3.8-flash
CORS_ORIGINS=https://YOUR_FRONTEND_ORIGIN
```

The values above are names/placeholders only; do not copy secret values into source control or the frontend. `SUPABASE_SERVICE_ROLE_KEY` may contain the current server-side Supabase secret/service-role credential. Keep it only on Render API/worker and local backend `.env`.

**Vercel:** no new environment variable is required. Keep only the existing public `NEXT_PUBLIC_API_URL`; do not add Supabase or Gemini secrets to Vercel or any `NEXT_PUBLIC_*` variable.

## 7. API examples

Set placeholders in a local shell; do not include real user secrets in source files:

```bash
export API_URL="https://YOUR-RENDER-API"
export WORKSPACE_ID="YOUR-M1-WORKSPACE-UUID"
export DOCUMENT_ID="DOCUMENT-UUID-RETURNED-BY-UPLOAD"
```

Check status:

```bash
curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/status"
```

Retrieve analysis:

```bash
curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/analysis"
```

Retrieve pages and evidence:

```bash
curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/pages?limit=25&offset=0"

curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/facts?limit=25&offset=0"

curl -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/segments?limit=25&offset=0"
```

Retry a non-active job:

```bash
curl -X POST -H "X-Workspace-ID: $WORKSPACE_ID" \
  "$API_URL/api/v1/documents/$DOCUMENT_ID/retry"
```

For API validation, invalid UUID/workspace headers return 400, missing/out-of-scope document returns 404, persistence errors return 503, and retry of an already queued/processing job returns 409.

## 8. Test and run commands

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall -q app tests
python -m unittest discover -s tests -v
uvicorn app.main:app --reload --port 8000
```

Run one queued job:

```bash
cd backend
python -m app.workers.document_worker --once
```

Run the durable worker loop:

```bash
cd backend
python -m app.workers.document_worker
```

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local  # only if .env.local does not already exist
npm run typecheck
npm run build
npm run dev
```

Do not overwrite an existing `.env.local`; add only `NEXT_PUBLIC_API_URL` if needed. `npm ci` must be run in a network-enabled environment because the supplied archive did not include `node_modules`.

### Exact results in this implementation environment

- `python3 -m compileall -q app tests` — passed.
- `python3 -m unittest discover -s tests -v` — **35 tests passed**.
- Actual local Tesseract smoke test — passed on a synthetic image; Tesseract `5.5.0` found both `ben` and `eng`, recognized the test phrase, and returned confidence `0.949`. This is a smoke test, not an OCR accuracy benchmark.
- `npm run typecheck` — attempted, blocked because `frontend/node_modules` is absent; dependencies could not be restored because registry/network access was unavailable.
- `npm run build` — not run; frontend dependencies unavailable.
- FastAPI application startup was not verified because the execution environment lacks the declared `langgraph` package (and the Supabase SDK is not installed); these remain declared in `requirements.txt`. Network restrictions prevented restoring missing dependencies.
- Supabase migration / database / Storage / Render worker / Vercel deployment — not run or verified; no live credentials used. PostgreSQL tooling/parser was not available to execute/parse the migration locally.

## 9. Known gaps and M3 dependencies

- Tesseract OCR is not guaranteed for handwriting, poor scans, tables, stamps, seals or multi-column/complex layouts. Review all OCR-derived evidence.
- The deterministic fact extractor is deliberately conservative and may miss facts or identify a phrase without understanding its legal significance. Every candidate requires human review.
- DOCX embedded-image-only content is not yet OCR'd; when no paragraph/table text exists, the upload path returns an explicit error instead of pretending extraction succeeded.
- M2 summary is an extractive preview, not a model-written summary. Image vision analysis is not active.
- Password-protected PDFs are rejected. Parser isolation/malware scanning/CDR, production rate limits, audit log, retention/deletion controls and verified user identity remain future security requirements.
- `X-Workspace-ID` is still temporary device scope. Do not treat it as authentication.
- M3 owns authoritative Bangladesh statute/case corpus ingestion, source version/status, vector embeddings, pgvector, hybrid legal RAG and retrieval evaluation. M2 segment rows are not embeddings or verified legal-source chunks.
- M2 does not calculate legal deadlines, verify statute validity/citations or give definitive legal conclusions.

## 10. Completion decision

**M2 is partially complete, not fully operationally accepted.** The source implementation, migration, worker and documentation are included, and all 35 backend tests pass. Completion still depends on the project owner applying migration 003 in a verified staging/live environment, deploying/configuring the Render worker and private Storage, completing frontend typecheck/build/browser validation, and running a full integration smoke test. M3 work has not been started.
