# Legal Copilot

**AI Legal Advisory Platform — Bangladesh-first, Bengali + English**

Legal Copilot is the AI Builders Congress project. It is completely separate from **LDIS**, the user's LandTech project for digital land records and land-record workflows. Do not merge the two products' requirements or repositories.

## Product vision

A chat-first legal support platform where users can describe an incident, ask legal/procedural questions, attach raw legal documents, ask questions about attachments, analyze contracts and case files, research law, verify citations and generate evidence-linked memoranda.

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
- Uploaded-document chat endpoint.
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

Edit `backend/.env` and set `GEMINI_API_KEY` locally. The default model ID is `gemini-3.8-flash`.

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

## Configuration

- Backend secrets belong only in `backend/.env`.
- Frontend `.env.local` may contain only public configuration such as `NEXT_PUBLIC_API_URL`.
- Never commit `.env`, `.env.local`, API keys or service-role keys.

## Known limitations

The project is not yet a complete AI Builders Congress solution. General legal chat without an attachment, persisted conversation history, multi-file attachments, OCR, authoritative Bangladesh law corpus, RAG/pgvector, independent citation verification, full multi-agent orchestration, CrPC legal triage, plaintiff/defendant analysis, live Supabase integration, Bangla PDF font embedding and production security are still pending.

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
