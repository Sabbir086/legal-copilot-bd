# MyLegal AI (Legal Copilot BD)

**AI Legal Advisory Platform — Bangladesh-first, Bengali + English**

Legal Copilot is the AI Builders Congress project. It is completely separate from **LDIS**, the user's LandTech project for digital land records and land-record workflows. Do not merge the two products' requirements or repositories.

## Product vision

MyLegal AI is a chat-first legal support platform where users can describe an incident, ask legal/procedural questions, attach raw legal documents, ask questions about attachments, analyze contracts and case files, research law, verify citations and generate evidence-linked memoranda.

Bangladesh is the default jurisdiction. International sources named in the competition brief are comparative sources and must always retain their own jurisdiction labels.

## Competition acceptance target

The supplied AI Builders Congress brief requires a functional multi-agent legal system that can ingest a raw legal document, identify at least three non-obvious compliance risks supported by document evidence, and generate a memorandum citing real-world statutes. Citations must be independently checked against authoritative text and current legal status. The system must not fabricate risks or citations to satisfy a numeric target.

## Current prototype features found in the source

- Bengali-first light-theme Next.js interface.
- PDF/DOCX upload and drag/drop.
- Text-based PDF and DOCX extraction.
- Initial document classification.
- Gemini-powered contract risk screening with rule-based fallback.
- Exact document quote matching for risk evidence.
- Chat-first general legal conversation workspace without requiring attachments.
- Persistent conversation list and message history through Supabase.
- Multiple PDF/DOCX/image attachments per conversation; private Supabase Storage bucket (20 MB documents, 8 MB per image, 12 MB combined image context).
- Separate AI Chat and Document Analysis views; document context is available across a conversation.
- Basic two-node LangGraph workflow.
- Preliminary memorandum PDF endpoint.

## Setup (macOS)

### Backend

```bash
cd ~/Documents/legal-copilot-bd/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # only if backend/.env does not already exist
```

Set backend-only `GEMINI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`. The default model ID is `gemini-3.8-flash`. Never place these values in the frontend or `NEXT_PUBLIC_*` variables.

For local Bangla/English OCR, install Tesseract and ensure `ben` and `eng` appear in `tesseract --list-langs`:

```bash
brew install tesseract
tesseract --list-langs
```

If language data is missing, install the matching `.traineddata` files from the official Tesseract tessdata repository into the installation's `tessdata` directory. The backend reports missing OCR binary/language packs explicitly.

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### Frontend (new Terminal tab)

```bash
cd ~/Documents/legal-copilot-bd/frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend: http://localhost:3000

## Supabase setup (M0 → M2)

Migration sequence is append-only. Check the actual Supabase migration history before running SQL; never rerun a migration that is already applied.

1. If this is a new database with no M0/M1 schema, apply `supabase/migrations/001_initial_schema.sql`, then `002_conversational_workspace.sql`, then `003_document_intelligence.sql`, each exactly once.
2. If `001` and `002` are already applied (as in an existing M1 environment), apply **only** `003_document_intelligence.sql`. It extends the existing M0 `documents` table and adds M2 page/segment/fact/job tables; it does not replace M1 attachment tables.
3. If only some migrations are applied, inspect and reconcile the schema/history before applying anything. Back up first and test against a staging Supabase project.
4. Keep `conversation-attachments` private. M2 stores original files and derived page/normalized images in this existing private bucket.
5. Configure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` on the Render API and the Render worker only. The existing key variable may hold a current server-side `sb_secret_...` key or legacy `service_role` key.
6. Verify API and worker logs, then upload a synthetic document and test state, evidence retrieval and retry. `/health` reports only environment-value presence; it does not test the database or worker.

### Render Background Worker

M2 extraction is queued by FastAPI and processed by a durable database-backed worker; do not rely on in-memory FastAPI background tasks. Create a Render Background Worker from the same repository using `backend/Dockerfile.worker` (Docker build context `backend`). The Docker image installs Tesseract and `ben`/`eng` language packs. Use the start command:

```bash
python -m app.workers.document_worker
```

Configure the same server-side `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` used by the API, plus the M2 OCR/segment settings from `backend/.env.example`. A one-job local smoke command is `python -m app.workers.document_worker --once` from `backend/`. See `docs/M2_IMPLEMENTATION.md` for Render details and API examples.

## Configuration

- Backend secrets belong only in `backend/.env` and Render's backend Environment settings.
- Frontend `.env.local` may contain only public configuration such as `NEXT_PUBLIC_API_URL`.
- Never commit `.env`, `.env.local`, API keys or service-role keys.

## Known limitations

M2 document-intelligence code is implemented and the backend synthetic unit suite passes, but the owner must still apply migration 003, deploy/configure the Render worker, and complete frontend/live integration checks. OCR currently uses Tesseract and may be inaccurate for handwriting, poor scans, complex layouts or embedded-image-only DOCX files. The document summary is extractive; visual-model analysis is not active. Candidate facts require human review and do not verify law or calculate legal deadlines.

The project is not yet a complete AI Builders Congress solution. M3 authoritative Bangladesh law corpus, source versioning, RAG/pgvector, citation verification, full multi-agent workflow, CrPC triage, plaintiff/defendant analysis, Bangla PDF font embedding and production security remain pending. M1/M2 still use a device-scoped workspace UUID, not authentication; do not upload confidential case files until M8 authorization and RLS are implemented.

## Documentation

- `docs/PROJECT_SCOPE.md` — product scope and separation from LDIS.
- `docs/MILESTONES.md` — M0–M8 roadmap.
- `docs/ARCHITECTURE.md` — current and target architecture.
- `docs/AGENT_CONTRACTS.md` — agent/evidence contracts.
- `docs/LEGAL_SOURCES.md` — legal source strategy and CrPC acquisition notes.
- `docs/SECURITY.md` — security limitations and release blockers.
- `docs/DEVELOPMENT_STATUS.md` — implemented vs pending status and test validation.
- `docs/M2_IMPLEMENTATION.md` — M2 architecture, migration, worker, OCR setup, API examples and handoff.

## Legal disclaimer

Legal Copilot is an AI-assisted information and document-analysis tool, not a law firm or substitute for advice from a qualified lawyer. It cannot guarantee outcomes or determine guilt, liability, ownership or legal validity. Any legal claim must be evaluated against current authoritative law and the complete facts.

## M3 law corpus + authentication/admin add-on

The latest handoff adds a Supabase-searchable Penal Code corpus and account-based access:

- Apply `supabase/migrations/004_penal_code_auth_admin.sql` once after the existing `001`–`003` migrations.
- Import `legal_data/penal_code_sections.csv` into `public.penal_code_sections` (555 extracted records from the supplied 2013 PDF snapshot).
- Configure the backend-only `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`, Supabase service key and OpenRouter key; configure only public Supabase Auth values and the API URL in the frontend.
- New signups get the `user` role; the configured Super Admin can assign or remove the `admin` role in `/admin`.
- The chatbot uses database retrieval (RAG), not model fine-tuning. It grounds candidate Penal Code sections in the imported text and flags the 2013 source snapshot for current-law verification.

See `docs/PENAL_CODE_RAG_AUTH_ADMIN_SETUP.md` for migration, CSV import, Auth setup, rollout and verification steps. Do not treat the supplied historical PDF as proof of current law.
