# Legal Copilot — Development Status (M1 implementation)

Last updated 20 November 2026 against the M0 source package used for the deployed `main` branch.

## M0 — completed foundation

- Product scope separated from LDIS / LandTech.
- Environment templates, `.gitignore`, architecture, source, evidence and security contracts.
- Backend upload/report directories anchored to the backend project directory.
- Basic PDF/DOCX upload validation and local preliminary document workflow.
- M0 tests and packaging checks were run in the previous M0 delivery; that did not verify the user's live Render/Vercel/Supabase deployment.

## M1 — implementation delivered; Supabase rollout required

- Chat-first Bengali/English workspace with a ChatGPT-style conversation layout.
- General legal chat without requiring an attachment.
- Device-scoped conversation list, create, reopen and permanent-delete APIs.
- Conversation messages persisted in Supabase PostgreSQL.
- Multiple PDF, DOCX, PNG, JPG/JPEG and WEBP attachments per conversation.
- PDF/DOCX text extraction and document-type hinting at attachment time.
- Image attachments passed to Gemini as multimodal context; this is visual model input, not a persistent OCR pipeline.
- All attached documents/images become context for subsequent questions in that conversation.
- Separate AI Chat and Document Analysis views.
- Private Supabase Storage bucket for original attachments.
- Server-only Supabase client; the browser receives no Supabase service key.
- `X-Workspace-ID` device identifier is used to retrieve the browser's history.

### M1 setup still required by the project owner

1. Create/choose the Supabase project.
2. Run `001_initial_schema.sql` and then `002_conversational_workspace.sql` in Supabase SQL Editor.
3. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to local `backend/.env` and Render's backend Environment settings.
4. Redeploy Render, verify `/health` reports `workspace_persistence: true`, then test conversation creation, reopen, attachment upload and chat.
5. Keep Render `CORS_ORIGINS` in sync with the Vercel/custom Frontend origin.

M1 code is delivered, but its persistence functionality is not live until the steps above succeed. File extraction currently runs synchronously during upload; a separate background job queue and live progress monitor are deferred. M1's workspace UUID is a prototype device identifier, not authentication or secure per-user identity. Do not upload confidential client/case files until M8 authentication, ownership-bound RLS and security review are complete.

## Not implemented — later milestones

- M2: OCR for scanned PDFs/images, long-document segmentation/indexing, richer structured extraction, document-summary/analysis pipeline, page-level confidence/provenance.
- M3: authoritative Bangladesh legal corpus, source/version metadata, pgvector embeddings, hybrid RAG and retrieval evaluation.
- M4: full AI Builders multi-agent workflow, 3+ evidence-supported non-obvious risks, independent legal citation verifier and evidence-linked verified memorandum.
- M5: current CrPC-based incident triage, official court/police/judicial-services directory and checked procedural guidance.
- M6: plaintiff/defendant case analysis, chronology, allegations/evidence mapping, strengths/weaknesses and remedies.
- M7: verified Bengali/English memoranda, Bangla-font PDF export and case brief/chronology export.
- M8: Supabase Auth, authorization, per-user RLS, auditable lifecycle, rate limiting, malware scanning, privacy/deletion controls, evaluation and production hardening.

## Validation boundary

The update must pass Python compile/unit tests and a Next.js type/build check before it is described as code-validated. Live Supabase, Gemini, Render or Vercel behaviour is not claimed unless verified using the owner's configured services.
