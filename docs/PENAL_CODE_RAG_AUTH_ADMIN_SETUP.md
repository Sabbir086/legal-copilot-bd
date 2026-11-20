# Penal Code RAG, Supabase Auth and Admin Portal Setup

Last updated: 20 November 2026

This handoff extends the existing M2 application. It does not replace the conversation/document architecture.

## 1. What is implemented

- A searchable corpus for the supplied **Penal Code, 1860 (Act XLV of 1860)** PDF.
- `penal_code_sections` stores the full extracted section text, section number/title/chapter, a best-effort punishment excerpt, PDF page locators and source-version metadata.
- The chat service identifies an explicit section number or asks the LLM to turn a described incident/case statement into compact English search keywords. It retrieves source text from Supabase before drafting an answer.
- The assistant is instructed to map each possible section to the incident facts, list missing facts/elements, quote only the punishment wording available in the retrieved text, distinguish allegations from proven facts, and never invent a section or punishment when retrieval fails.
- Email/password signup and sign-in through Supabase Auth; new public accounts receive `user` role.
- `admin` and immutable `super_admin` roles, an admin dashboard, account search, role promotion/demotion by Super Admin, usage counts, recent search activity, query categories and frequent searches.
- Workspace UUIDs are bound server-side to the first authenticated account that claims them. Another account cannot reuse that workspace ID.

## 2. Important legal-source limitation

The source PDF is an older snapshot (visible print date: 26 August 2013). This import is **not** proof that each provision or punishment remains in force in 2026. It does not independently reconcile amendments, repeals, commencement, special statutes, case law or later judicial interpretation.

The CSV contains 555 extracted records: 511 numbered sections plus 44 letter-suffixed section records. Full extracted text is retained. A separate best-effort `punishment_excerpt` is present for 381 records; the other 174 have no separate excerpt. An empty excerpt does not mean that the full section contains no punishment or that the offence carries no punishment. The excerpt may omit provisos or sentencing options; the chatbot must refer to the full section text. Some text extraction/section boundaries can still require manual review. The dataset is in English as supplied; this update does not claim an authoritative Bangla translation.

The model has **not** been fine-tuned. The implementation uses retrieval-augmented generation (RAG): it searches the database and provides matching source sections to the existing model at answer time. This is easier to update, inspect and cite than model fine-tuning, and does not make the answer legally verified.

## 3. Safe migration and CSV import

Before touching production, take a Supabase backup and inspect the migration history.

For the existing project where migrations `001_initial_schema.sql`, `002_conversational_workspace.sql` and `003_document_intelligence.sql` are already applied:

1. Open Supabase Dashboard → SQL Editor.
2. Run **only once**: `supabase/migrations/004_penal_code_auth_admin.sql`.
3. Confirm the migration completes. It adds profile/role, workspace ownership, Penal Code corpus, retrieval RPC and chatbot analytics objects. It does not drop or recreate existing conversation/document tables.
4. Open Table Editor → `penal_code_sections` → Import data from CSV.
5. Upload `legal_data/penal_code_sections.csv` (also supplied separately with this handoff). Match columns by CSV header. The expected import is **555 rows**.
6. Confirm `select count(*) from public.penal_code_sections;` returns `555` and try `select * from public.search_penal_code_sections('theft', 10);` in SQL Editor.

Do not rerun migrations `001`–`003` if they are already present. If this database has a different migration history, reconcile the actual schema before running `004`; do not assume the local ZIP proves what is deployed.

## 4. Backend environment

Copy `backend/.env.example` to `backend/.env` for local development (or set the same variables in the backend hosting provider). Keep the following on the backend only:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVER_ONLY_SUPABASE_SECRET
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY
OPENROUTER_MODEL=openrouter/free
SUPER_ADMIN_EMAIL=joysabbir086@gmail.com
SUPER_ADMIN_PASSWORD=PASTE_THE_SUPER_ADMIN_PASSWORD_AS_A_LOCAL_SERVER_SECRET
CORS_ORIGINS=http://localhost:3000
```

Use the exact Super Admin password supplied by the project owner in the local/backend hosting secret store. Do not place it in the ZIP, Git, frontend `.env.local`, client JavaScript, SQL migration or screenshots. `SUPABASE_SERVICE_ROLE_KEY` and `OPENROUTER_API_KEY` must never use a `NEXT_PUBLIC_` variable.

## 5. Frontend environment

Copy `frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY
```

The public Supabase URL and anon/publishable key are intended for browser Auth flows. Do not copy the backend service-role secret into this file.

## 6. Create the Super Admin and use the application

1. Start the API from `backend/`: `uvicorn app.main:app --reload --port 8000`.
2. Start the frontend from `frontend/`: `npm run dev`.
3. In Supabase Dashboard → Authentication → Providers → Email, turn **Confirm email** off if the desired flow is immediate signup/sign-in without email verification. Configure the Site URL and redirect allow-list to include the frontend origin and `/reset-password`.
4. Open `/signin` and enter the server-configured Super Admin email/password. The sign-in flow first calls a one-time bootstrap route. That route only provisions the Super Admin when the submitted email/password match the backend-only secrets. It does not return or store the password in the browser. Then normal Supabase sign-in completes.
5. After sign-in, the account has `super_admin` role and opens `/admin`.
6. New signups at `/signup` receive `user` role and open `/dashboard` after authentication.
7. Super Admin can promote a User to Admin or demote an Admin to User from User management. Admin can view dashboard data but cannot change roles. A Super Admin account cannot be promoted/demoted or deleted via this app's role-management API.

The configured Super Admin email is reserved. If it already exists as an ordinary `user` or `admin`, bootstrap will reset that account to the backend-configured password and assign `super_admin` only after the submitted email/password exactly match the backend-only secrets. Do not configure an email that belongs to someone else.

## 7. Signup, reset and workspace behaviour

- Signup fields: email, password and confirm password. Minimum password length in the UI is eight characters; Supabase password policy may be stricter.
- Forgot password sends a Supabase recovery email. Set the Supabase Auth redirect allow-list to your deployed frontend `/reset-password` URL.
- Each account receives a separate browser-local workspace UUID. The backend claims this UUID in `workspace_owners` and rejects attempts by a different account to reuse it.
- The browser stores the Supabase session token in local storage and refreshes it when nearing expiry. For a high-security production release, move session handling to secure HttpOnly cookies and add CSRF protection, rate limits, monitoring and formal retention controls.

## 8. Admin analytics and privacy

The application stores a limited chatbot search event (`query_text`, category, retrieved section numbers, user ID, conversation ID and timestamp). The Admin dashboard displays totals, recent activity, frequent queries and category counts. Since legal narratives can contain personal or sensitive information, publish a privacy/retention policy, restrict Admin access, and decide how long to retain raw query text before public use. No query text is sent to other users.

## 9. Local validation and rollout boundary

- Backend Python syntax: `python -m compileall -q backend/app`.
- Backend tests in this work session: `python -m pytest -q` → 35 passed.
- Frontend dependency installation timed out in the build environment, so `next build`, browser flow and live Supabase calls were not verified here.
- No migration was applied to the user's live Supabase project, no hosting environment was changed, and no real Super Admin account was created from this local workspace.

Before production: run migration `004` against staging first, import the CSV and verify counts/RPC, set server secrets, test regular signup and the Super Admin bootstrap, test role boundaries with three separate accounts, test cross-account workspace access denial, verify password recovery, inspect logs and deploy the frontend/backend with the correct CORS and redirect URLs.
