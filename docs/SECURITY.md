# Security and Privacy Baseline

## Identity and workspace scope (M1/M2 prototype boundary)

M1/M2 use a random browser-local `X-Workspace-ID` to scope conversation and document queries. This is a temporary device-scope identifier, **not authentication**, not a verified user identity and not equivalent to `auth.uid()`. A person who obtains or spoofs a workspace UUID may be able to access that workspace through the API. Do not use this prototype for confidential client/case files or sensitive personal information.

M8 is a release blocker: implement Supabase Auth, derive ownership from verified JWT claims (never trust a caller-supplied workspace UUID), bind every database row and storage path to `auth.uid()`, apply and test per-user RLS policies, and remove the prototype workspace-ID authorization path.

## Secrets

- Keep `backend/.env` and `frontend/.env.local` local.
- Gemini API keys, Supabase service-role/secret keys and database credentials are backend-only.
- Never use `NEXT_PUBLIC_` for secrets.
- Never commit secret files or paste secret values into source control, screenshots or agent chat.
- The Render API and worker need server-only Supabase credentials; the Vercel frontend does not.

## Upload and parser controls

- The browser MIME header is not trusted. The backend derives/validates file format from extension and actual signature/decoder.
- PDF/DOCX document size uses `MAX_UPLOAD_MB` (default 20 MB); each image is limited by `MAX_IMAGE_UPLOAD_MB` (default 8 MB) and `MAX_IMAGE_PIXELS` (default 40 million pixels).
- Pillow verifies images and converts decompression-bomb warnings/errors to blocked uploads. DOCX ZIP entries, total uncompressed bytes, compression ratio and internal paths are checked before XML extraction.
- PDFs are capped by `MAX_PDF_PAGES` (default 500). Render dimensions are downscaled before page rasterization to remain within the pixel limit.
- The parser is not a malware scanner, antivirus, content-disarm/reconstruction engine or fully sandboxed process. For production, isolate workers, apply CPU/memory/time limits, patch OS/Python libraries, and consider malware scanning/CDR.
- Stored files are revalidated by the worker before processing. User filenames are not used as shell commands; Tesseract is invoked with argument arrays and byte pipes.

## OCR and evidence provenance

- `OCRProvider` is an abstraction; current local provider is Tesseract. `OCR_LANGUAGES` defaults to `ben+eng`; missing binary/language data produces explicit `ocr_unavailable` or `partial` state, never a successful empty extraction.
- OCR output is separate from selectable PDF text/DOCX source text, and carries engine, language, confidence and page/block locator where available.
- DOCX page numbers are not fabricated. Paragraph/table/cell/block anchors are used instead.
- Derived page renders/normalized images are private Storage objects with workspace/conversation/document-scoped keys.
- M2 image vision-model analysis is not enabled; it is not conflated with OCR text.
- Every stored candidate fact must have an exact quote found in extracted source blocks, a locator, confidence, extraction method and `needs_review`. Unsupported candidate values are withheld as null. Facts are not verified legal conclusions.

## Prompt injection and LLM boundary

- Treat every original file, extracted span, OCR result and model-generated description as untrusted data.
- Prompt-like phrases are flagged as signals. They are never executed as system/developer instructions.
- M1 chat attachment context is bounded by `MAX_CHAT_CONTEXT_CHARS`; omitted portions are recorded in message metadata. Document Analysis pages are paginated and text is clipped with omitted-character metadata.
- M2 summary is an extractive source-text preview, not an LLM legal opinion. No LLM-generated fact is persisted by the M2 pipeline.
- Never use uploaded content as tool instructions, SQL, shell commands or trusted prompts.

## Storage and database

- The existing `conversation-attachments` bucket remains private. The M2 migration does not make it public.
- M2 child tables have RLS enabled and client-role table grants revoked; application access uses backend service credentials.
- `workspace_id` is still the M1 device-scope UUID. RLS/service-role setup does not magically convert it into secure per-user authorization.
- Do not execute migrations against production without backup, migration-history review, and a tested staging rollout. Apply only the next unapplied migration.

## Legal safety

- Distinguish user allegations from established facts and court findings.
- Distinguish document text from proof of authenticity, truth, ownership or legal effect.
- Distinguish literal statute/section strings from current/verified law.
- M2 does not implement authoritative Bangladesh-law RAG or independent citation verification. Never invent a section, case, citation, procedural deadline or court service.
- Escalate urgent/high-risk situations to qualified human/legal assistance; the system is informational and is not a lawyer.

## Before public/production use

Supabase Auth, user-bound RLS, retention/deletion controls, malware-safe processing, worker isolation/quotas, rate limiting, CORS review, audit trails, monitoring, incident response, legal-source verification and independent security testing remain release blockers.

## Authentication/admin add-on (20 November 2026)

The latest source now includes Supabase email/password Auth, server-verified bearer-token middleware, `profiles` role checks, immutable `super_admin` role handling, and first-claim workspace ownership in `workspace_owners`. M2 conversation and document endpoints require a verified user and a workspace UUID already bound to that user. Admin analytics and role changes use server-side service credentials; only Super Admin can assign/demote `admin` roles.

This is a first implementation, not a production security certification. Session tokens currently live in browser local storage; use secure HttpOnly cookies/CSRF protection for a hardened production release. Add rate limiting, abuse monitoring, audit logging, privacy/retention controls and independent penetration testing before public launch. Search-event rows include user-submitted query text, so Admin visibility must be described in a privacy notice and governed by retention rules.
