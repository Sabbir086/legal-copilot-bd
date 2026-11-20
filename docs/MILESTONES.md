# Legal Copilot — Milestone Roadmap

This roadmap is specific to **Legal Copilot / AI Builders Congress**. It is not the LDIS / LandTech roadmap.

## M0 — Scope lock and repository foundation

- Separate product identity and boundaries from LDIS.
- Audit the existing codebase and establish current vs planned capabilities.
- Add environment templates and secret/data exclusions.
- Resolve local upload/report paths independently of the shell working directory.
- Establish legal-source, evidence, agent and release contracts.

**Exit criteria:** a clean, reproducible source package; no uploaded user documents or secrets in the source archive; compile/syntax and unit checks pass; documented API and security limitations.

## M1 — Unified conversational legal workspace (implementation delivered; Supabase setup pending)

- Chat-first Bengali/English UI.
- Conversations and persisted message history.
- General legal chat without requiring an attachment.
- Attach multiple PDF/DOCX files and PNG/JPG/WEBP images to a conversation.
- Attachments become conversation context; user can ask questions and receive page/clause citations.
- Separate Document Analysis panel with synchronous upload/text-extraction status (background job queue and live progress are deferred).
- Conversation/session APIs and Supabase storage model.
- M1 uses a device-scoped workspace UUID as a prototype only; authentication and ownership-bound RLS remain M8 release blockers.

**Exit criteria:** users can start a conversation, describe an incident, attach a document, continue asking questions, and reopen a prior conversation without losing context.

## M2 — Document intelligence and multimodal ingestion

- Secure PDF/DOCX/image ingestion.
- Text extraction, OCR for scanned documents and image/PDF page processing.
- Long-document page/section segmentation and contextual indexing.
- Classification for contract, court filing/order, notice, statute, correspondence and other document types.
- Structured extraction of parties, dates, amounts, provisions, claims, evidence, court and procedural posture.
- Document summary and extraction confidence/provenance.

**Exit criteria:** extracted facts retain page/section anchors and uncertain fields are flagged rather than silently guessed.

## M3 — Bangladesh legal corpus and Agentic RAG

- Authoritative statutory corpus, including CrPC and amendments.
- Source metadata, versioning, commencement/effective dates, repeal/status history.
- Embeddings, pgvector, hybrid keyword/vector retrieval and jurisdiction filters.
- Retrieval evaluation set and source provenance.
- Official case-law and judicial-services source catalog.

**Exit criteria:** retrieved passages are traceable to exact source versions; corpus coverage gaps are visible.

## M4 — AI Builders mandatory multi-agent document workflow

- Document Intelligence Agent.
- Clause/obligation extraction agent.
- Compliance/Risk Detection Agent.
- Legal Research Agent.
- Independent Citation Verification Agent.
- Memorandum Generation Agent.
- LangGraph orchestration, retries, state, evidence gates and audit trail.

**Exit criteria:** on a prepared benchmark contract, produce at least three distinct non-obvious risks when supported, exact source-document evidence for each, real statutory citations independently checked against authoritative text/status, and a memorandum that distinguishes verified and unverified material.

## M5 — Bangladesh legal advisory and judicial-services guidance

- Incident intake and clarification workflow.
- Criminal procedure, police/court routing information and procedural next steps.
- CrPC/other relevant law retrieval with section-level source citations.
- Official judicial-services directory and safe external links.
- Urgency and deadline warning with explicit uncertainty and referral to qualified counsel.

**Exit criteria:** case triage is grounded in current official sources, distinguishes allegation from fact, and abstains when required facts or authority are missing.

## M6 — Plaintiff/defendant case analysis

- Case document ingestion and structured case chronology.
- Party-role selection.
- Allegation-to-evidence mapping.
- Strengths, weaknesses, counterarguments and missing evidence.
- Procedural posture and potential next-step options.
- Separate factual assertions, party submissions, court findings and AI inferences.

**Exit criteria:** balanced two-sided analysis with every factual point linked to a document passage/source, and no advice to fabricate or suppress evidence.

## M7 — Verified memorandum and collaboration features

- Bengali and English memorandum generation.
- Embedded Bangla fonts and accessible PDF output.
- Source bibliography, citation status, evidence anchors and review date.
- Exportable case brief, chronology and evidence index.
- User feedback/correction loop.

**Exit criteria:** report content can be independently traced to supplied facts and verified authorities.

## M8 — Security, evaluation and deployment

- Authentication, authorization and per-user document isolation.
- RLS, encrypted storage, retention/deletion controls and audit logging.
- Rate limits, file validation, safe error handling and monitoring.
- Prompt-injection tests, privacy tests, retrieval/citation benchmarks, hallucination/abstention evaluation.
- Deployment, backups, incident response and user-facing limitations.

**Exit criteria:** documented security review and test results; no claim of production readiness until all release gates pass.
