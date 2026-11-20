# M0 Repository Audit

## Input snapshot

- Input: user-supplied `project_backup.zip`.
- Archive contained 389 entries and approximately 73.6 MB uncompressed.
- A large portion was generated Next.js `.next` output.
- The archive included four PDFs under `backend/uploads/` and one generated PDF under `backend/reports/`. These were excluded from the M0 redistribution package. They must not be committed or re-shared as source code.

## Source inventory

- `frontend/`: Next.js App Router, Bengali-first interface, light theme, document attachment and document-grounded chat UI.
- `backend/app/api/routes/`: document analysis, document chat and legal keyword-search routes.
- `backend/app/agents/`: Gemini risk screening and evidence matching.
- `backend/app/graph/`: two-node LangGraph workflow.
- `backend/app/services/`: PDF/DOCX parser, document classifier, local legal-source keyword search and report generation.
- `supabase/migrations/001_initial_schema.sql`: initial schema and vector extension.
- `legal_data/statutes/sources.json`: two unverified placeholder Contract Act entries.

## Findings

1. No general chat endpoint exists without a document ID; current chat is document-grounded only.
2. Conversation history is supplied by the client and is not persisted in Supabase.
3. Multiple attachments per conversation are not modeled.
4. The current LangGraph pipeline contains risk detection and document-evidence validation only.
5. Legal source records are placeholders; current legal search is keyword discovery, not RAG or legal research verification.
6. Citation verification, amendment/current-status reconciliation and applicability checking are not implemented.
7. Initial Supabase tables have RLS enabled, but user-specific policies/live authenticated persistence are not wired. This is fail-closed for those tables but not a complete user-facing access model.
8. Document chat is not protected by user authentication/ownership authorization; the current API is safe only as a local prototype.
9. Upload/report paths were relative to the process working directory. M0 makes them backend-relative.
10. The uploaded archive had no root `.gitignore` and no `backend/.env.example` / `frontend/.env.example`, although setup docs expected those files. M0 adds them.
11. Uploaded PDFs and generated reports were bundled in the user's backup snapshot. M0 release archives exclude these, generated caches and build output.

## M0 checks executed in the packaging environment

- Python AST parse: passed.
- `compileall` for backend app/tests: passed.
- Backend unit tests: 4 passed.
- `bash -n install-update-mac.sh`: passed.
- Full live FastAPI/Gemini/Supabase run: not executed in this packaging environment because the LangGraph and Google GenAI packages were not installed here and the user's private API credentials are not available.
- Next.js typecheck/production build: not re-run in this packaging environment; the user should run these locally with their installed Node dependencies.
