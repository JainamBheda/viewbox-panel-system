# Design v2 — Questionnaire Runtime Upgrade

> This document is additive. The Day 2 files in `design/` remain frozen and unchanged.
> This upgrade was introduced after reviewing a competing implementation whose strongest area
> was questionnaire parsing, versioning, respondent runtime and survey analytics.

## Goal

ViewBox already covers member identity, acquisition attribution, referrals, eligibility,
CSV import, exports, payouts and Meta lead processing. The competitive gap is that a member
could apply to a survey but could not actually answer a questionnaire inside the product.
This v2 adds a first-class questionnaire runtime while preserving the frozen Day 2 model.

## Design principles

1. **Identity-first participation.** Unlike anonymous token links, ViewBox responses are tied to
   an authenticated member. This allows one response per member per survey, reliable quota
   accounting and enforcement of the 3-month calendar cool-off.
2. **Frozen versions.** Publishing a questionnaire creates an immutable numbered version with
   the raw source and parsed AST. Activating a new version archives the previous one. Responses
   remain pinned to the version they started on.
3. **No hardcoded dashboard values.** Runtime counts, drop-off and quality flags are computed
   from persisted response/answer rows.
4. **Auditability.** Every correction, termination reason and answer remains queryable.

## Text questionnaire DSL

A questionnaire is a plain `.txt` file. Blank lines and `#` comments are ignored.

```text
Q1 | single | What is your primary commute mode? | Car | Bike | Bus | Walk
Q2 | multi | Which factors matter to you? | Price | Safety | Time | Comfort
Q3 | rating | How satisfied are you with your commute? | 1-5
Q4 | nps | How likely are you to recommend this study? | 0-10
Q5 | text | Any suggestions? Use {Q1} in your answer.

SHOW | Q2 | IF | Q1 | EQ | Car
SKIP | Q5 | IF | Q3 | GTE | 4
TERMINATE | IF | Q1 | EQ | Walk | Walkers are out of scope for this study
QUOTA | Q1 | Car | 10
```

Supported question types: `single`, `multi`, `rating`, `nps`, `text`, `yesno`, `date`.

Supported condition operators: `EQ`, `NE`, `IN`, `CONTAINS`, `GTE`, `LTE`.

`{Q1}` placeholders in question text are replaced with the member's previous answer before
display. Validation returns line-numbered errors and publishes nothing when errors exist.

## Additive schema

### `questionnaire_versions`

| Column | Purpose |
|---|---|
| `id` PK | Version identifier |
| `survey_id` FK → `surveys.id` | Parent survey |
| `version` | Monotonic version number, unique per survey |
| `raw_text` | Original uploaded `.txt` source |
| `ast` JSON | Parsed questions, logic, terminations and quotas |
| `status` | `DRAFT` / `ACTIVE` / `ARCHIVED` |
| `created_at` | Audit timestamp |

### `survey_responses`

| Column | Purpose |
|---|---|
| `id` PK | Response identifier |
| `survey_id` FK → `surveys.id` | Parent survey |
| `member_id` FK → `members.id` | Authenticated respondent |
| `version_id` FK → `questionnaire_versions.id` | Frozen questionnaire version |
| `status` | `IN_PROGRESS` / `COMPLETED` / `TERMINATED` |
| `answers` JSON | Question-id → normalized answer map |
| `path` JSON | Ordered visited-question ids for back navigation/drop-off |
| `meta` JSON | Runtime metadata (rotation arm, language, quality notes) |
| `termination_reason` | Human-readable screener failure reason |
| `started_at` / `completed_at` | Duration and audit |
| `created_at` / `updated_at` | Audit timestamps |

Unique constraint: `(survey_id, member_id)` — one response per member per survey.

### `survey_answers`

| Column | Purpose |
|---|---|
| `id` PK | Answer identifier |
| `response_id` FK → `survey_responses.id` | Parent response |
| `question_id` | Stable DSL question id, e.g. `Q1` |
| `value` JSON | Scalar or list answer |
| `answered_at` | Audit timestamp |

Unique constraint: `(response_id, question_id)` — autosave upserts one answer per question.

## API additions

All paths are relative to `/api/v1`.

### Admin

| Method | Path | Purpose |
|---|---|---|
| POST | `/admin/surveys/{survey_id}/questionnaire/validate` | Dry-run line-aware validation |
| POST | `/admin/surveys/{survey_id}/questionnaire` | Publish and activate a new version |
| GET | `/admin/surveys/{survey_id}/questionnaire/versions` | List version history |
| GET | `/admin/surveys/{survey_id}/analytics` | Started/completed/terminated, per-question drop-off, speeders |

### Member

| Method | Path | Purpose |
|---|---|---|
| POST | `/members/me/surveys/{survey_id}/response/start` | Start or resume the member's response |
| GET | `/members/me/surveys/{survey_id}/response` | Current question/progress |
| POST | `/members/me/surveys/{survey_id}/response/answer` | Autosave answer and advance |
| POST | `/members/me/surveys/{survey_id}/response/back` | Remove the last answer and navigate back |

A response can only be started when the member's persisted application is `APPROVED`.
Completion calls the existing completion service, so payout creation, PASSED quality state,
cool-off start and eligibility recalculation stay consistent with the frozen Day 2 design.

## Competitive advantage

The competing design marks strict 3-month cool-off as out of scope because its survey links
are pseudonymous. ViewBox can enforce it because participation is authenticated. This v2
keeps that advantage while adding the questionnaire engine, frozen versions, testable DSL
validation and analytics that the competing design demonstrated.
