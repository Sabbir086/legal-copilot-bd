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
cp .env.example .env
```

Edit `backend/.env` and set `GEMINI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` locally. The default model ID is `gemini-3.8-flash`.

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

## Supabase setup for M1

1. Create a Supabase project.
2. If the initial M0 schema has not already been applied, run `supabase/migrations/001_initial_schema.sql` once. Then run `supabase/migrations/002_conversational_workspace.sql` in the Supabase SQL Editor.
3. Copy the Project URL and a server-side secret key from Supabase Project Settings → API Keys. Prefer the new `sb_secret_...` key; the legacy `service_role` key is also supported during Supabase’s key transition.
4. Put these values in `backend/.env` as `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (the environment variable name stays the same even when its value is the new `sb_secret_...` key).
5. Add the same two keys to Render's backend service Environment settings, then redeploy.
6. Confirm `https://YOUR-RENDER-SERVICE/health` reports `workspace_persistence: true`. This only confirms the two environment values are present; it is not a live database/storage test.

The private bucket `conversation-attachments` is created by migration 002. Do not make it public.

## Configuration

- Backend secrets belong only in `backend/.env` and Render's backend Environment settings.
- Frontend `.env.local` may contain only public configuration such as `NEXT_PUBLIC_API_URL`.
- Never commit `.env`, `.env.local`, API keys or service-role keys.

## Known limitations

The project is not yet a complete AI Builders Congress solution. M1 code is implemented, but Supabase must be configured by the project owner before persistence works. OCR for scanned documents, authoritative Bangladesh law corpus, RAG/pgvector, independent citation verification, the full multi-agent workflow, CrPC legal triage, plaintiff/defendant analysis, Bangla PDF font embedding and production security remain pending. M1 uses a device-scoped workspace UUID, not authentication; do not upload confidential case files until M8 authorization and RLS are implemented.

## Documentation

- `docs/PROJECT_SCOPE.md` — product scope and separation from LDIS.
- `docs/MILESTONES.md` — M0–M8 roadmap.
- `docs/ARCHITECTURE.md` — current and target architecture.
- `docs/AGENT_CONTRACTS.md` — agent/evidence contracts.
- `docs/LEGAL_SOURCES.md` — legal source strategy and CrPC acquisition notes.
- `docs/SECURITY.md` — security limitations and release blockers.
- `docs/DEVELOPMENT_STATUS.md` — implemented vs pending status.

## Legal disclaimer

Legal Copilot is an AI-assisted information and document-analysis tool, not a law firm or substitute for advice from a qualified lawyer. It cannot guarantee outcomes or determine guilt, liability, ownership or legal validity. Any legal claim must be evaluated against current authoritative law and the complete facts.
