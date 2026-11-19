# ViewBox Panel System

Full-stack prototype for Concave Insights: a respondent panel with phone/OTP login,
source and referral attribution, a deterministic eligibility engine, operations tooling,
messy-CSV import, exports and a mock Meta Lead Ads webhook.

## Project Overview

ViewBox models three actors:

| Actor | What they can do |
|---|---|
| **Prospective member** | Register through a tracked source or referral link and complete a profile. |
| **Member** | Log in with OTP, see matched surveys and decisions, share a referral link, track referral stages and rewards. |
| **Operations / Admin** | Manage sources, links, surveys and rules; search/export respondents; stage referrals; review imports; monitor Meta leads and payouts. |

The prototype is database-backed end to end — no dashboard number or eligibility decision
is hardcoded. The Day 2 design baseline is frozen in [`design/`](design/); implementation
clarifications are recorded in [`design/v2/change-log.md`](design/v2/change-log.md).

## Tech Stack

**Backend**

- Python 3.12 (3.11+ supported), FastAPI, Uvicorn
- SQLAlchemy 2.x, Alembic, PostgreSQL 16/18 (`psycopg[binary]`)
- Pydantic v2 / pydantic-settings, python-jose JWT, passlib
- CSV processing with the standard library plus `openpyxl` for XLSX export
- Pytest, HTTPX TestClient, SQLite in-memory test database

**Frontend**

- React 18, Vite 6, React Router 6, Axios
- Tailwind CSS 3, Lucide icons, Recharts
- Vitest + Testing Library for component/behavior tests

## Setup and Run

### 1. Backend prerequisites

Python 3.11+ and either Docker (recommended) or a local PostgreSQL instance.

```powershell
# From the repository root (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy .env.example .env
```

Update `.env` if you changed the PostgreSQL user, password or port.

Start PostgreSQL with Docker:

```powershell
docker compose up -d
```

Or create the database manually in a local PostgreSQL instance:

```sql
CREATE USER viewbox WITH PASSWORD 'change-me-locally';
CREATE DATABASE viewbox OWNER viewbox;
```

Apply the migration, seed demo data and start the API:

```powershell
cd backend
alembic upgrade head
python -m scripts.seed_demo --with-csv
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`, and the health check at `/health`.

### 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend defaults to
`http://localhost:8000/api/v1`; set `VITE_API_BASE_URL` in `frontend/.env` only if
the backend runs elsewhere.

### 3. Verification commands

```powershell
# Backend: 23 tests
cd backend
python -m pytest tests -q

# Frontend: 6 behavior tests and a production build
cd ../frontend
npm test
npm run build
```

For a quick SQLite-only smoke test without PostgreSQL, set
`DATABASE_URL=sqlite:///./viewbox.db` before running
`python -m scripts.seed_demo --with-csv` and `uvicorn app.main:app --reload`.
The seed script calls `create_all` for this convenience; PostgreSQL deployments should
use `alembic upgrade head`.

## Demo Logins and Test Data

The seed script is idempotent. Sign in with any of these phone numbers; the mock OTP is
always **`123456`** and is also displayed by the login screen.

| Phone | Role | Landing area |
|---|---|---|
| `9000000001` | `ADMIN` | Full operations panel, including payout approval and source edits |
| `9000000002` | `OPERATIONS` | Operations panel (read-only for full-admin-only actions) |
| `9000000003` | `MEMBER` | Member portal with a complete profile and referral link |

Seed data also includes nine dynamic sources, source signup links, referral links for
demo members, one live survey (`Urban Mobility Survey 2026`) and one closed survey used to
demonstrate history. Exact link tokens are generated at seed time and can be viewed in
**Sources** (admin) or **Referral link** (member).

`--with-csv` imports the provided `viewbox_respondents_sample.csv`. Verified outcome:
**160 imported**, **29 skipped**, **245 corrections**, **169 warning/error entries**.
Skipped rows and warnings are preserved in `import_row_errors` and can be downloaded from
**CSV Import → Errors**. See [`docs/data-quality-report.md`](docs/data-quality-report.md)
for the initial inspection of the messy file.

No real SMS, payment, or personal data provider is connected.

## Features

| Feature | Status | Notes |
|---|---|---|
| Mock OTP login and JWT role checks | Implemented | Fixed dev code `123456`; one-time challenge with expiry; member/admin/operations routing |
| Registration and profile completion | Implemented | Normalizes phone, gender, city, income and interests; duplicate phones are rejected and flagged |
| Dynamic sources and signed-up links | Implemented | CRUD plus unique `SRC-` tokens; sources are database rows, not enums |
| Referral links and staging | Implemented | Unique `REF-` tokens; referrer sees name, masked phone, stage and failure reason only |
| Source/referral conflict | Implemented | Acquisition source and referral relationship are credited independently |
| Eligibility engine | Implemented | Deadline → strict rules → 3-month calendar cool-off → quota → flexible rules → approved |
| Quota concurrency | Implemented | `SELECT … FOR UPDATE` on the survey row; only APPROVED applications consume a slot |
| Survey/rule administration | Implemented | Create and update surveys, strict/flexible rules, review applications, record completions |
| CSV import | Implemented | Hash-based idempotency, staging, preview, per-row transactional confirm, audit error CSV |
| CSV/XLSX export | Implemented | Uses the currently active search and filters, including server-side pagination |
| Fraud flags | Implemented | Duplicate phone, self-referral, referral cycle and Meta duplicate flags |
| Payout ledger | Implemented | Pending/approved/paid transitions; `PAID` requires prior `APPROVED` and full `ADMIN` role |
| Meta Lead Ads mock | Implemented | Idempotent by `meta_lead_id`; accepts webhook envelope or merged lead payload |
| Responsive UI | Implemented | Admin sidebar, member bottom navigation, loading/empty/error states, toasts |
| Automated tests | Implemented | 23 backend + 6 frontend tests passing |

## Database Design

The frozen Day 2 ERD and rationale are in
[`design/database-diagram.md`](design/database-diagram.md); user flows are in
[`design/user-flow.md`](design/user-flow.md). The initial Alembic revision is
`backend/migrations/versions/756a4a3af8c6_initial_schema.py`.

There are 18 tables grouped by concern:

| Group | Tables |
|---|---|
| Identity | `users`, `otp_challenges` |
| People & attribution | `members`, `referrals`, `fraud_flags`, `sources`, `source_links`, `referral_links`, `attribution_history` |
| Surveys | `surveys`, `survey_rules`, `survey_applications`, `survey_completions` |
| Operations | `import_jobs`, `import_staged_rows`, `import_row_errors`, `meta_leads`, `payout_ledgers` |

Key design points:

* `members.source_id` is the **last-touch** acquisition source; first touch and every
  later touch remain in `attribution_history`.
* Referrals live in their own table so a source link and a member referral can coexist.
* Survey eligibility decisions are persisted per survey/member and recalculated after
  profile or rule changes.
* Import staging and error tables keep the original row values for audit; problematic rows
  are skipped, never silently deleted or guessed.
* Payouts append a ledger row per completion or completed referral; status changes are
  role-gated.

## API Endpoints

All application routes are prefixed with **`/api/v1`**. Protected routes require
`Authorization: Bearer <access_token>`. `ADMIN` and `OPERATIONS` may use admin read/action
routes; source creation/edits and payout payment require `ADMIN`.

### Public and authentication

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/request-otp` | Create a mock OTP challenge; returns `dev_otp` outside production |
| POST | `/auth/verify-otp` | Verify OTP and receive JWT plus role/profile flags |
| GET | `/auth/me` | Current user summary |
| GET | `/public/sources` | Active sources for the registration form |
| GET | `/public/attribution/resolve` | Resolve `token` and/or `referral_token` |
| POST | `/public/register` | Register a member with optional attribution tokens |
| GET | `/surveys` | Public list of live surveys |
| GET | `/health` | API and database health |

### Member portal

| Method | Path | Purpose |
|---|---|---|
| GET | `/members/me` | Member profile |
| PUT | `/members/me/profile` | Update profile and recalculate live-survey decisions |
| GET | `/members/me/referral-link` | Return the member's `REF-` token and share URL |
| GET | `/members/me/referrals` | Referral dashboard with masked phones |
| GET | `/members/me/surveys` | Live surveys with evaluated eligibility |
| POST | `/members/me/surveys/{survey_id}/apply` | Persist the decision under a quota lock |
| GET | `/members/me/payouts` | Member reward ledger |

### Administration

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/admin/sources` | List or create sources and default links |
| PATCH | `/admin/sources/{source_id}` | Update source fields or active flag |
| GET | `/admin/sources/links` | List all source links |
| POST | `/admin/sources/{source_id}/links` | Create a campaign link |
| GET / POST | `/admin/surveys` | List or create surveys with rules |
| PATCH | `/admin/surveys/{survey_id}` | Update survey fields and rules |
| GET | `/admin/surveys/{survey_id}/applications` | Review eligibility decisions |
| POST | `/admin/surveys/{survey_id}/completions/{member_id}` | Record a completion and start cool-off |
| GET | `/admin/referrals` | List referrals, optionally filtered by stage |
| PATCH | `/admin/referrals/{referral_id}/stage` | Move LEAD/FIT/COMPLETED/FAILED |
| POST | `/admin/imports/upload` | Analyse CSV and create a preview job |
| GET | `/admin/imports` | List import jobs |
| GET | `/admin/imports/{job_id}/preview` | Row-by-row corrections and warnings |
| POST | `/admin/imports/{job_id}/confirm` | Commit valid rows with per-row isolation |
| GET | `/admin/imports/{job_id}/errors.csv` | Download the audit error report |
| GET | `/admin/dashboard/sources` | SQL-aggregated signup/fit/completed counts |
| GET | `/admin/members` | Search, filter and paginate respondents |
| GET | `/admin/members/export` | Export current filters as `csv` or `xlsx` |
| GET | `/admin/fraud-flags` | Review fraud flags |
| GET / PATCH | `/admin/payouts` / `/admin/payouts/{payout_id}` | List or transition payouts (`?status_value=...`) |
| GET | `/admin/meta-leads` | Inspect processed/flagged Meta leads |

### Meta Ads Lead Endpoint

`POST /api/v1/webhooks/meta/leads` accepts either the documented page webhook envelope
(`entry[].changes[].value` with IDs such as `leadgen_id`, `form_id`, `campaign_id`,
`ad_id`, `created_time`) or a merged lead object with `field_data` for local testing.
Duplicate IDs return `already_processed` and never create a second member.

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/meta/leads \
  -H "Content-Type: application/json" \
  -d '{
    "meta_lead_id": "123123123123",
    "form_id": "999",
    "campaign_id": "888",
    "ad_id": "777",
    "created_time": 1440120384,
    "field_data": [
      {"name": "full_name", "values": ["Joe Example"]},
      {"name": "phone", "values": ["+91 99887 76655"]},
      {"name": "city", "values": ["Mumbai"]}
    ]
  }'
```

Per [Meta's Lead Ads webhook documentation](https://developers.facebook.com/docs/marketing-api/guides/lead-ads/webhooks/),
a live webhook notification carries IDs only and field values are retrieved from
`GET /{lead_id}`. The mock endpoint intentionally accepts a merged representation so the
full flow can be exercised locally without a Meta app.

## Assumptions and Decisions

| Decision | Detail |
|---|---|
| Primary acquisition attribution | **Last touch** wins in `members.source_id`; all touches are kept in `attribution_history`. |
| Source/referral conflict | Both are credited: the source stays on the member and the referral row is created separately. |
| Quota | An `APPROVED` application consumes a slot; `WAITLISTED` and `REJECTED` do not. Approvals are serialized with `SELECT … FOR UPDATE`. |
| Cool-off | Three **calendar** months from the latest `PASSED` completion; the member sees `Eligible again on DD-MM-YYYY.` |
| Dates | Day-first parsing with a `26` century pivot; ambiguous values are imported with `AMBIGUOUS_DATE`, impossible dates are skipped. |
| OTP | Fixed development code `123456`, displayed in the UI and returned by the API. No SMS provider. |
| Invalid CSV emails | Set to `NULL` with `INVALID_EMAIL`; the original value stays in the audit report. |
| Unknown referrers / self-referrals | No referral is created; self-referrals and cycles are flagged. No personal data is invented. |
| Privacy | Referrers see only name, member code, masked phone, stage and failure reason. |
| Import safety | Rows are staged and previewed first; confirm uses per-row savepoints so one bad row cannot discard good rows. |
| Roles | `MEMBER`, `OPERATIONS` and `ADMIN`; full-admin-only actions are enforced server-side, not just in the UI. |
| Meta integration | Mock only: no Graph API fetch, webhook signature verification or live Meta app is required. |

## Known Issues and Next Steps

* This is a prototype: change `SECRET_KEY`, remove the returned `dev_otp`, and add rate
  limiting before any production use.
* No real SMS, UPI/payment gateway or Meta Graph API integration is included.
* Meta webhook signature verification is not implemented; the mock endpoint is intended for
  local assessment/demo traffic only.
* The Vite build emits a chunk-size warning (Recharts); route-level code splitting is a
  straightforward follow-up.
* `npm audit` reports dev-dependency advisories from the frontend toolchain; upgrade
  Vite/Vitest transitive dependencies before deployment.
* Local PostgreSQL installation on the assessment machine needed a repeated unattended
  installer run. If `pg_isready` fails, either rerun the installer or use
  `docker compose up -d`; backend tests use SQLite and are unaffected.
* Next steps: add email/SMS adapters, real payout disbursement, webhook signature checks,
  scheduled eligibility recalculation, and role-based audit logs for every admin mutation.
