# Security and Privacy Baseline

## Current prototype boundary

The current API is a local development prototype. It has no authentication, no per-user document authorization, no Supabase-backed user isolation and no production audit logging. Do not expose it publicly or upload confidential client/case files until those controls are implemented and reviewed.

## Secrets

- Keep `backend/.env` and `frontend/.env.local` local.
- Gemini API keys and Supabase service-role keys are backend-only secrets.
- Never use `NEXT_PUBLIC_` for secrets.
- Never commit secret files or paste secret values into source control, screenshots or chat.

## User documents

- Uploaded documents are untrusted inputs and may contain prompt-injection instructions.
- The current prototype stores files locally under `backend/uploads/` and reports under `backend/reports/`.
- Source archives and Git repositories must exclude uploaded files and generated reports.
- Define user-visible retention and deletion controls before production use.
- Do not log extracted document content, personal data or secrets.

## Upload controls currently present

- Extension allow-list: PDF and DOCX.
- Configurable 20 MB default size limit.
- UUID-based storage names.
- M0 adds bounded chunk reading and basic PDF/DOCX signature checks.

These checks are not a substitute for antivirus/malware scanning, archive-bomb defenses, content-disarm/reconstruction, sandboxed parsing or a production object-storage policy.

## Legal safety controls

- Distinguish user allegations from established facts and court findings.
- Distinguish document text from proof of authenticity or truth.
- Distinguish a document quote match from statute citation verification.
- Never invent a section, case, citation, procedural deadline or court service.
- Show jurisdiction and verification status for each legal source.
- Escalate urgent/high-risk situations to qualified human/legal assistance; the system is informational and not a lawyer.

## Before public deployment

Authentication, role/access control, per-user document authorization, Supabase RLS policies, signed/private object storage, retention/deletion, malware-safe processing, rate limiting, CSRF/CORS review, audit trails, monitoring, incident response and independent security testing remain release blockers.
