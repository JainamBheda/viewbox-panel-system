# Design v2 — Implementation Notes

The Day 2 files in `design/` are frozen and were not edited. This file records endpoint and
workflow details that were clarified while implementing the prototype.

## API path clarifications

| Frozen Day 2 document | Implemented endpoint | Reason |
|---|---|---|
| `POST /admin/source-links` | `POST /api/v1/admin/sources/{source_id}/links` | Links are nested under their parent source; the collection listing is `GET /api/v1/admin/sources/links`. |
| `PUT /members/me` | `PUT /api/v1/members/me/profile` | Makes profile editing distinct from reading the member record. |
| `GET /surveys/live` | `GET /api/v1/surveys` | Shorter public read endpoint; it still returns only live surveys. |
| `POST /surveys/{id}/applications` | `POST /api/v1/members/me/surveys/{survey_id}/apply` | The member is derived from the authenticated token, not from the request body. |
| Payout status change | `PATCH /api/v1/admin/payouts/{payout_id}?status_value=...` | Query parameter keeps the small admin action explicit and testable. |

All paths above are relative to the `/api/v1` prefix configured in `main.py`.

## Behaviour clarifications

* The public survey list is also embedded in `GET /api/v1/members/me/surveys` so the
  member portal receives each survey together with its evaluated eligibility result.
* `GET /api/v1/public/attribution/resolve` accepts `token` and `referral_token` separately.
  The registration endpoint may send both when one URL contains both kinds of links.
* Invalid CSV emails are set to `NULL` rather than skipping the whole respondent; the raw
  value is preserved in `import_row_errors.original_data`.
* Payout rows are append-only in intent; status transitions are controlled by
  `payout_service.change_payout_status` and `PAID` requires prior `APPROVED` plus `ADMIN` role.
* The Meta webhook mock accepts either the documented webhook envelope (IDs only) or a
  merged lead object including `field_data`. No live Graph API call or webhook signature
  verification is performed in this prototype.

No frozen design file was modified; these notes are additive.
