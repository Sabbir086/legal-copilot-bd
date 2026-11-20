# Legal Copilot — Development Status (M0 audit)

Last audited against the supplied `project_backup.zip` on 20 November 2026.

## Existing code found in the backup

- Bengali-first light-theme Next.js interface.
- PDF/DOCX upload and drag/drop UI.
- FastAPI document upload and text extraction.
- Initial document classification for contract, land record, deed, court document and other.
- Gemini contract-risk screening with heuristic fallback.
- Exact quote matching against source text before risk findings are retained.
- Uploaded-document chat endpoint.
- Minimal LangGraph flow with risk detection and document-evidence validation nodes.
- Preliminary memorandum PDF generation.
- Initial Supabase schema with pgvector column and RLS enabled.

## M0 changes in this update

- Product scope is explicitly separated from LDIS / LandTech.
- Added M0–M8 milestone roadmap and agent/source/evidence contracts.
- Added backend and frontend environment templates.
- Added `.gitignore` for secrets, caches, virtual environments, uploaded documents and reports.
- Resolved upload and report directories relative to `backend/`, independent of shell working directory.
- Added bounded upload reads and basic file-signature checks for PDF and DOCX.
- Sanitized the distributable source package by excluding local uploads, reports, `.next`, caches and build artifacts.

## Not implemented yet

- General legal chat without an attachment.
- Durable conversation/message history.
- Multiple attachments per conversation.
- Complete OCR/multimodal document ingestion.
- Official Bangladesh statutory corpus acquisition and reconciliation.
- RAG and pgvector ingestion/retrieval.
- Independent legal citation verifier.
- Complete multi-agent flow for legal research and memorandum generation.
- CrPC-based incident triage and judicial-services guidance.
- Plaintiff/defendant case analysis.
- Supabase live persistence/authentication and per-user RLS policies.
- Bangla font embedding in PDFs.
- Production authentication, authorization, audit logging, retention/deletion and deployment hardening.

## Honest validation status

The M0 source archive is checked for inclusion/exclusion rules. Python syntax and available backend unit tests are run as part of this packaging step. A full live Gemini request, Supabase connection and Next.js production build are not claimed unless executed against the user's own configured environment.
