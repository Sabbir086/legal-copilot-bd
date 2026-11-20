# Security and Privacy Baseline

## M1 prototype boundary

M1 stores conversation/message/attachment data in Supabase and keeps original attachments in a private Storage bucket. The browser does not receive the Supabase service-role key and does not access the database or bucket directly.

However, M1 does **not** implement Supabase Auth. It uses a random browser-generated `X-Workspace-ID` to scope conversation queries. This provides device-scoped prototype history, not verified identity or strong per-user authorization. A person who obtains or spoofs a workspace UUID may be able to access that workspace through the API. Do not use this release for confidential client/case files or sensitive personal information.

M8 is a release blocker: implement Supabase Auth, derive ownership from verified JWT claims (never trust a caller-supplied workspace UUID), bind every database row and storage path to `auth.uid()`, apply and test per-user RLS policies, and remove the prototype workspace-ID authorization path.

## Secrets

- Keep `backend/.env` and `frontend/.env.local` local.
- Gemini API keys, Supabase service-role/secret keys and database credentials are backend-only.
- Never use `NEXT_PUBLIC_` for secrets.
- Never commit secret files or paste secret values into source control, screenshots or chat.

## Attachments

- M1 supports PDF, DOCX, PNG, JPG/JPEG and WEBP; maximum 20 MB for PDF/DOCX and 8 MB per image (12 MB combined image context); up to 8 attachments per conversation.
- Basic format/signature validation is performed, but this is not malware scanning, content-disarm/reconstruction, or a sandboxed parser.
- PDF/DOCX extraction is text-based. Scanned PDFs may be rejected if no selectable text is available; persistent OCR is M2.
- Images are passed to Gemini as multimodal context; the model's visual description is not a formal OCR result and may be uncertain.
- Original attachments are stored in a private Supabase Storage bucket. Extracted text is stored in the Supabase database to support conversation context.
- Conversation deletion removes private Storage objects first and then permanently deletes the conversation and cascading message/attachment rows. If Storage removal fails, the database rows are retained so deletion can be retried. Production still needs a documented retention policy and verified deletion tests.

## Legal safety controls

- Distinguish user allegations from established facts and court findings.
- Distinguish document text from proof of authenticity or truth.
- Distinguish a document quote match from statute citation verification.
- M1's general legal chat does not have live authoritative Bangladesh-law RAG or independent citation verification. The assistant must not invent or label a statute/case citation as verified.
- Never invent a section, case, citation, procedural deadline or court service.
- Escalate urgent/high-risk situations to qualified human/legal assistance; the system is informational and not a lawyer.

## Before public/production use

Authentication, authorization, user-bound RLS, signed/private object lifecycle, retention/deletion, malware-safe processing, rate limiting, CORS review, audit trails, monitoring, incident response, legal-source verification and independent security testing remain release blockers.
