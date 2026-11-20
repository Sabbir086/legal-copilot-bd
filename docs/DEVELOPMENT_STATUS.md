# Legal Copilot — Development Status (M2 code implementation)

Last updated 20 November 2026 against the uploaded `legal-copilot-bd-main(3).zip` source archive. The archive has no `.git` directory, so its original branch, recent commits and upstream dirty state cannot be inspected. The actual deployed Render/Vercel/Supabase revisions are also not verifiable from this local source package.

## M0 — foundation retained

- Product scope remains separate from LDIS / LandTech.
- Existing M0 `public.documents` table remains the base document table; M2 extends it.
- Existing M0 parser/report/API compatibility remains; the legacy document route uses the new pipeline synchronously.

## M1 — conversation workspace retained

- Chat-first Bengali/English workspace and conversation history remain.
- General legal chat does not require an attachment.
- Existing conversation, message and attachment tables are preserved.
- Multiple PDF, DOCX, PNG, JPG/JPEG and WEBP attachments remain supported.
- Original files remain in the existing private Supabase Storage bucket.
- Images remain available to M1 Gemini multimodal chat; OCR is now separately persisted by M2.
- `X-Workspace-ID` is a device-scope prototype identifier, not authentication or secure per-user identity.

## M2 — implemented in source; operational rollout pending

- Unified signature-based file validation, upload-size checks, image pixel/decompression checks, DOCX ZIP expansion/path protections and PDF page limits.
- PDF selectable text extraction page by page, scanned/low-text detection, safe page rendering and Tesseract provider abstraction.
- Bangla/English OCR configuration (`ben+eng`) and explicit OCR-unavailable/needs-OCR/partial states.
- DOCX paragraph/table extraction in reading order with real block anchors and no fabricated PDF page numbers.
- Image OCR metadata (dimensions, engine, language, confidence, locator); visual/vision model analysis remains distinct and is marked not requested.
- Explainable classification for contract, court filing, court order/judgment, legal notice, statute, correspondence, identity/supporting evidence and other/unknown. Legacy land-record/deed hints are preserved for M1 compatibility.
- Rule-based candidate facts for visible party roles, dates, amounts, case/court/district/procedural posture, literal law references, clause categories, allegations and evidence references. Exact supporting quotes are validated before persistence.
- Bounded page/block/heading/clause segments with offsets, parent/overlap metadata; no embeddings (M3 scope).
- New durable jobs, atomic job claiming, worker lease heartbeat, deterministic upserts, private derived page-image paths and scoped retry.
- Document status/details/analysis/pages/segments/facts/retry APIs.
- Bilingual Document Analysis interface with processing/partial/error/retry, classification, summary provenance, evidence locator, confidence, uncertainty and prompt-injection notice.
- Existing M1 chat/conversation routes and M0 legacy endpoints remain.

### Backend validation run in the supplied execution environment

```text
python3 -m compileall -q app tests                         PASSED
python3 -m unittest discover -s tests -v                    PASSED (35 tests)
```

The suite uses synthetic PDF/DOCX/image fixtures and mocks for OCR/database/storage/worker behavior. It does not require live Gemini or Supabase credentials. A separate synthetic real-Tesseract smoke test passed (Tesseract 5.5.0, both `ben` and `eng` found, recognized the generated image text at confidence 0.949).

### Frontend validation boundary

The repository does not pin a Python or Node runtime version. The supplied environment is Python 3.13.5, Node v22.16.0 and npm 10.9.2. `frontend/package-lock.json` resolves Next.js 16.4.6, React/React DOM 19.3.1, TypeScript 5.9.3 and Tailwind CSS 4.3.5.

`npm run typecheck` was attempted but could not complete because `frontend/node_modules` is absent from the supplied archive/environment. `npm ci` could not restore packages because outbound package registry access was unavailable. Consequently Next.js typecheck/build and browser smoke testing are **not run/verified**. A TSX syntax-only transpile with the globally installed TypeScript 5.8.3 passed; this is not a typecheck.

FastAPI application startup was not verified because the execution environment does not have the declared LangGraph dependency installed; the network restriction prevented restoring missing Python dependencies. The Supabase SDK is also absent locally, so live persistence was not tested.

### Required project-owner rollout

1. Confirm the live database has migrations `001` and `002` already applied. If they are, apply only `003_document_intelligence.sql`. Do not rerun/renumber applied migrations.
2. Ensure the existing `conversation-attachments` Storage bucket is private, then deploy the API with Pillow and M2 environment settings.
3. Deploy a separate Render Background Worker from `backend/Dockerfile.worker`, sharing the backend-only Supabase URL/secret. The image installs Tesseract and Bangla/English language packages.
4. Verify one synthetic test document through upload, queued/processing/completed or explicit OCR state, pages/facts retrieval and retry in a staging Supabase project.
5. Install frontend dependencies and complete typecheck/build/browser checks.

## Known limitations / not implemented in M2

- Live Supabase schema, SQL function execution, storage behavior, Render worker and Vercel deployment are not verified. No migration was run against the user's live account.
- No `.git` metadata was present, so branch/commit/uncommitted-work checks and comparison with remote/deployed source were impossible.
- OCR is Tesseract-only. It depends on binary plus Bangla/English traineddata being installed in the worker image. Some handwriting, low-resolution pages, skewed scans and complex layouts will be inaccurate; OCR confidence is not legal certainty.
- M2 summary is an extractive preview, not an LLM-generated summary. Persistent image vision analysis is not enabled.
- Candidate extraction is deterministic/rule-based and is not exhaustive. Parties/clauses/dates may be missed; every fact is flagged for human review. No legal deadlines are calculated.
- Encrypted/password-protected PDFs are rejected. Embedded-image-only DOCX documents do not yet have embedded-media OCR; they fail explicitly if no paragraph/table text is extractable.
- This is not malware scanning/CDR or fully sandboxed parsing. Production worker isolation, quotas, rate limits, monitoring and retention controls are still required.
- M1/M2 remain device-scope workspace only. Do not use with confidential client/case documents until M8 authentication, per-user RLS and a security review.
- M3 legal corpus, embeddings, pgvector RAG, statute-status verification and citation verification have not been started.

## Completion statement

**M2 is partially complete overall.** The M2 implementation is present in the source archive and the backend compile/unit suite passes. Operational acceptance remains pending because the live migration, Supabase/Storage integration, Render worker deployment, frontend typecheck/build and browser smoke tests could not be executed or verified from this archive-only environment. No M3 implementation was started.
