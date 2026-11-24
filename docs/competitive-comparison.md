# Competitive Comparison — Concave Survey System

Prepared from a read-only review of the public repository
`https://github.com/harshit-soni-2004/concave-survey-system` at commit
`6e5b3d9` (24 Nov 2026). No competitor code was copied into ViewBox.

## Summary

The competing project is a **strong five-minute demo**: polished Angular UI, a broad
questionnaire DSL and rich seeded data. It is **weaker as a system**: hardcoded demo
auto-login, several broken advertised routes, inflated test claims and no CI.

ViewBox's original strength was **panel operations** — identity, acquisition attribution,
referrals, eligibility, import audit, payouts and Meta leads. Its gap was that a member
could apply to a survey but not answer one. The v2 questionnaire runtime closes that gap
without touching the frozen Day 2 design.

Positioning: **same research workflow, but truthful, secure and maintainable.**

## Feature matrix

| Area | Friend's project | ViewBox before v2 | ViewBox after v2 |
|---|---|---|---|
| Questionnaire authoring | XML-like tags, 13 types, line-numbered editor | Admin created surveys/rules only | Pipe-separated text DSL, 7 types, line-numbered errors and click-to-line |
| Logic | AND/OR, skip-to, piping, shuffle, rotation | Eligibility rules only (strict/flexible) | SHOW/SKIP, `{Qn}` piping, TERMINATE, rotation arm metadata |
| Versioning | DRAFT/LIVE/CLOSED, respondent pinned to version | None | Numbered immutable versions, previous version archived, responses pinned |
| Respondent runtime | Anonymous token links, autosave, back navigation | Apply/approve only | Authenticated one-response-per-member runner with autosave and back |
| Quota | Dynamic counts + `SELECT FOR UPDATE` at completion | `SELECT FOR UPDATE` on approval | Approval lock plus completion-time quota check |
| Analytics | Dashboards, drop-off, quality flags | Source/referral dashboards | Per-question drop-off, termination reasons, speeders from persisted responses |
| Identity | Email/password, frontend silently logs in as hardcoded admin | Mock OTP + JWT RBAC, no auto-login | Unchanged — a real differentiator |
| Attribution | Not present | Last-touch source, full history, referrals and conflict handling | Unchanged — a real differentiator |
| Cool-off | Explicitly out of scope | 3 calendar months enforced | Still enforced through questionnaire completion |
| Import/audit | Not present | Staged messy CSV, per-row isolation, error CSV | Unchanged — a real differentiator |
| Payouts/Meta | Not present | Ledger and Mock Lead Ads webhook | Unchanged — a real differentiator |
| Export | CSV/XLSX, but formula mitigation and streaming claims are false | CSV/XLSX from active filters | Added dangerous-prefix escaping for spreadsheet safety |
| Testing | ~50 pytest cases, ~201 manual checklist rows, no CI, MySQL-destructive fixture | 25 backend + 6 frontend tests | **32 backend + 8 frontend tests plus CI** (tests, build, clean Alembic upgrade) |
| Documentation | Good README/demo script, but broken links and mismatched credentials | README, design docs, data-quality report | Added v2 design note, comparison and CI evidence |
| Devops | Docker Compose + Nginx | Local run + Alembic | Added GitHub Actions CI |

## What we deliberately did not copy

* **Hardcoded demo auto-login** and silent re-auth as admin. ViewBox keeps explicit OTP login.
* **Regex line scanner presented as an XML parser.** Our DSL parser produces a validated AST
  with line-numbered errors and refuses to publish invalid input.
* **Unverified claims** such as "201/201 automated tests", "streaming exports",
  "formula-injection mitigation" (in their code) and "WCAG AA compliant".
* **Destructive `DROP TABLE` test fixtures** and startup that swallows migration errors.
* **Angular monolith components** exceeding 2,500 lines; our React screens stay small and tested.

## What we adopted and improved

1. Config-driven questionnaires (`design/v2/questionnaire-runtime.md`).
2. Line-aware validation UI with clickable errors that select the offending line.
3. Frozen versions with activation history, so in-flight responses are never rewritten.
4. Transactional quota check on completion and one response per member.
5. Analytics derived from `survey_responses` / `survey_answers`, not seeded numbers.
6. Export formula-prefix escaping.
7. CI as published evidence rather than a checklist spreadsheet.

## Honest limitations to keep in mind

* The OTP is still a fixed development code and there is no rate limiting.
* Question types cover the common research cases (single, multi, rating, NPS, text, yes/no,
  date), not all thirteen of the competitor's parser; matrix shuffling and bilingual content
  are not implemented.
* Exports are generated in memory; we do not claim streaming.
* The frontend build still emits a Recharts chunk-size warning.
* Meta webhook signature verification, real SMS and real payouts remain out of scope.

## Highest-value next steps

1. Add seeded questionnaire responses so analytics are visually rich on first launch.
2. Add test sessions (`is_test`) that do not consume quota.
3. Add matrix and rotation question blocks with per-respondent shuffling.
4. Add frontend route smoke tests covering every step of the demo script.
5. Move JWT storage to HttpOnly cookies before any production deployment.
