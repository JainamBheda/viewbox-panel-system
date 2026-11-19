# ViewBox Respondent CSV — Initial Data-Quality Report

Source file: `viewbox_respondents_sample.csv` (repository root).
Inspected before any importer or schema was designed. 189 data rows, 13 columns:

`member_id, name, phone, email, gender, date_of_birth, city, income_range,
interests, source, referred_by, joined_on, last_survey_completed_on`

## Findings

| Area | Finding | Handling rule adopted |
|---|---|---|
| Blank identifiers | 2 rows have a blank `member_id` | Skipped; original retained in `import_row_errors` |
| Duplicate IDs | `VB10011` appears twice with identical data; `VB10099` is reused by two different people | First row imported; later row skipped with `DUPLICATE_MEMBER_ID`; original kept |
| Duplicate phones | 3 normalized duplicate phone groups | First row imported; later row skipped and `DUPLICATE_PHONE` fraud flag raised |
| Invalid phones | 20 values are not valid 10-digit Indian mobiles | Skipped with `INVALID_PHONE`; no phone invented |
| Invalid emails | 44 malformed values | Stored as `NULL` with `INVALID_EMAIL`; original value preserved in the error report |
| Dates | Mixed ISO and day-first formats; ambiguous day/month values; `31/02/1995` is impossible; `12/12/2027` is a future join date; `15/03/2010` implies an implausible age | Day-first parsing with a `26` century pivot; impossible dates skipped; ambiguous dates imported with `AMBIGUOUS_DATE` warning |
| Gender | 6 spelling/case variants | Alias-normalized (`M` → `MALE`, etc.); unknown values flagged, never guessed |
| City | 17 casing/spacing variants | Alias-normalized (e.g. `navi mumbai` → `Navi Mumbai`) |
| Income | `5 lakh` does not match the configured ranges | Imported as `NULL` with `UNKNOWN_INCOME`; original preserved |
| Source | 14 spelling/alias variants | Alias-normalized to dynamically managed source rows; unknown/blank source stays `NULL` and is reported |
| Referrals | `VB99999` does not exist in the file; `VB10014` refers to itself | No referral relationship created; `UNKNOWN_REFERRAL_ID` / `SELF_REFERRAL` logged, self-referral flagged |
| Blank row | One fully blank row (line 26 in the source file) | Skipped with `BLANK_ROW`; no data invented |

## Import outcome (verified with the sample file)

The confirmed prototype import produced **160 imported rows** and **29 skipped rows** from the
189 source rows, with 245 safe normalizations/corrections and 169 warning/error entries.
Every skipped or corrected row can be traced back to its original values through the
`import_row_errors` audit table and the downloadable error CSV.

No source row was physically deleted, no personal data was invented, and no unknown
referral relationship was created.
