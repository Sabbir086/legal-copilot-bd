# MyLegal AI — Architecture

## Product boundary

MyLegal AI (repository: `legal-copilot-bd`) is the independent AI Builders Congress legal-assistance project. It is not LDIS and does not implement LDIS / LandTech land-office registration workflows. Bangladesh is the default legal jurisdiction.

## Current implementation (M0 + M1)

- **Frontend:** Next.js App Router, React and Tailwind CSS; Bengali-first, responsive, chat-first workspace with conversation history, AI Chat and Document Analysis views.
- **Backend:** FastAPI REST API; Gemini is called only by the backend.
- **Parsing:** PyMuPDF for selectable PDF text and python-docx for DOCX text. DOCX page layout is represented as page 1; scanned-PDF OCR is not enabled.
- **Classification:** deterministic keyword scoring; labels are routing hints, not legal determinations.
- **AI:** Gemini via `langchain-google-genai`, using bounded recent chat history and optional attachment context. Images are supplied as multimodal input; visual model output is not a persistent OCR record.
- **Orchestration:** existing M0 LangGraph preliminary document workflow remains available; M1 general chat is conversational and does not yet invoke the complete multi-agent legal research/risk/citation pipeline.
- **Database:** Supabase PostgreSQL for conversations, messages and attachment metadata. Migration `002_conversational_workspace.sql` must be applied after `001_initial_schema.sql`.
- **File storage:** private Supabase Storage bucket `conversation-attachments`; original attachment objects are not public.
- **Workspace scoping:** `X-Workspace-ID` is a random browser-local UUID in M1. It is not user authentication. M8 must replace it with Supabase Auth/JWT identity and ownership-bound RLS before confidential/multi-user production use.

## M1 conversation flow

```text
Browser (Next.js)
  |-- create/list/open/delete conversation
  |-- send ordinary legal question (no file required)
  |-- upload multiple PDF/DOCX/images
  |-- AI Chat / Document Analysis views
  |
  | X-Workspace-ID (prototype device identifier)
  v
FastAPI (Render)
  |-- validates workspace and conversation scope
  |-- extracts selectable PDF/DOCX text
  |-- stores attachments in private Storage
  |-- loads recent messages + bounded attachment context
  |-- calls Gemini server-side
  v
Supabase
  |-- conversations
  |-- conversation_messages
  |-- conversation_attachments + extracted_pages JSONB
  |-- private conversation-attachments bucket
```

## Current API

- `GET /`
- `GET /health`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`
- `DELETE /api/v1/conversations/{conversation_id}`
- `POST /api/v1/conversations/{conversation_id}/attachments`
- `POST /api/v1/conversations/{conversation_id}/messages`
- `POST /api/v1/documents/analyze` (M0 preliminary workflow)
- `POST /api/v1/chat/document` (legacy M0 endpoint)
- `POST /api/v1/legal/search` (local placeholder source catalog; not verified research)
- `POST /api/v1/memoranda/{document_id}/pdf` (preliminary report export)

## Target architecture

```text
Next.js conversational workspace
  -> FastAPI + Supabase Auth/JWT authorization
  -> LangGraph orchestrator
       -> intake / jurisdiction routing
       -> document intelligence + OCR
       -> legal issue and case triage
       -> evidence-linked risk detection
       -> Bangladesh legal RAG (pgvector + hybrid search)
       -> independent citation verification
       -> plaintiff/defendant case analysis
       -> verified memorandum generation
  -> Supabase PostgreSQL + pgvector + private Storage
```

## Trust boundaries

- User attachments are untrusted data, never instructions to agents.
- Document findings require page/clause anchors; extracted text does not prove authenticity or truth.
- Legal research findings require authoritative source IDs, jurisdiction and version metadata.
- Citation verification must be independent of citation generation.
- Memoranda must preserve verified, unverified and conflicting citation states.
- Human legal review remains necessary for high-stakes matters.

## Deployment environment

- Vercel frontend: `NEXT_PUBLIC_API_URL` points to the Render API origin. No Supabase secret is placed in Vercel.
- Render backend: `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are configured as server-side environment variables. A Supabase secret key (`sb_secret_...`) can be used as the value of `SUPABASE_SERVICE_ROLE_KEY`; the legacy `service_role` key also remains supported during the transition.
- `GET /health` reports whether both Supabase environment values are present; this is configuration presence, not a database/storage integration test.
