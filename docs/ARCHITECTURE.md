# Legal Copilot — Architecture

## Product boundary

Legal Copilot is an independent AI Builders Congress project. It is not LDIS and does not implement LDIS / LandTech land-office registration workflows.

## Current implementation

- **Frontend:** Next.js App Router, React and Tailwind CSS; Bengali-first light theme; upload, preliminary result and document-grounded chat view.
- **Backend:** FastAPI REST API.
- **Parsing:** PyMuPDF for text-based PDF and python-docx for DOCX.
- **Classification:** deterministic keyword scoring; routing hint only.
- **AI:** Gemini through `langchain-google-genai`.
- **Orchestration:** minimal LangGraph with two nodes: risk detection and document-evidence validation.
- **Storage:** local UUID-named files; relative storage paths now resolve against backend directory.
- **Database:** initial Supabase schema only; no live persistence or auth in this snapshot.

## Current API

- `GET /`
- `GET /health`
- `POST /api/v1/documents/analyze`
- `POST /api/v1/chat/document`
- `POST /api/v1/legal/search`
- `POST /api/v1/memoranda/{document_id}/pdf`

## Target architecture

```text
Next.js Chat-first UI
    |-- general legal conversation
    |-- file attachments and document chat
    |-- analysis/citation/memorandum views
    v
FastAPI API + Auth/Authorization
    v
LangGraph Orchestrator
    |-- Intake & Jurisdiction Router
    |-- Document Intelligence / OCR
    |-- Legal Issue & Case Triage
    |-- Contract Risk / Compliance
    |-- Legal Research (Agentic RAG)
    |-- Independent Citation Verification
    |-- Plaintiff/Defendant Case Analysis
    |-- Memorandum Generator
    v
Supabase PostgreSQL + pgvector + private object storage
    |-- conversations / messages
    |-- documents / page text / extracted facts
    |-- legal sources / versions / amendments
    |-- embeddings / retrieval citations
    |-- analysis runs / findings / verification records
    |-- audit events / retention metadata
```

## Jurisdiction model

Bangladesh is the default jurisdiction. The user may later select another jurisdiction explicitly. Comparative sources from the AI Builders brief (CourtListener, EUR-Lex, USPTO Open Data, Harvard Caselaw Access Project and Open Legal Data) must retain jurisdiction/source-type metadata and cannot be silently cited as Bangladesh law.

## Trust boundaries

- User attachments are untrusted data, never instructions to agents.
- Document findings require page/clause anchors.
- Legal research findings require source IDs and version metadata.
- Citation verification is an independent stage, not a field set by the research model.
- Memorandum generation must preserve unverified/partial status.
- Human review remains necessary for high-stakes legal conclusions.

## Data ownership and persistence

Conversations and attachments will be user-scoped. Supabase RLS and private object storage are required before multi-user deployment. The current local prototype does not provide this isolation.
