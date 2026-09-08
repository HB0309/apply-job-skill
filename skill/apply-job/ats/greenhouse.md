# Greenhouse — playbook

**Detect:** `job-boards.greenhouse.io/<org>/jobs/<id>`, `boards.greenhouse.io`, embedded iframes
**45 applications** · **Auto-submit risk: low** (downgraded 2026-09-08 — see below).

## Schema-first (preferred)
`python bin/jobkit.py schema <url>` → `GET boards-api.greenhouse.io/v1/boards/<org>/jobs/<id>?questions=true`
Returns every field's exact `name` attribute, type, required flag and all option labels,
plus `demographic_questions` and `compliance` blocks.

Stable keys: `first_name`, `last_name`, `email`, `phone`, `resume`, `cover_letter`.
Custom questions are `question_<digits>` — map by label from the schema.

Types: `input_text` · `input_file` · `multi_value_single_select` · `textarea`.

## Auto-submit — not a Greenhouse problem (2026-09-08)
Rows logged as Greenhouse auto-submits (Skild AI, Nuro, Watershed) were the user submitting the
finished form themselves while a multi-link run was still filling other tabs. The single genuine
case is Twitch 2026-08-01 (embed form, fields still blank, nobody clicked) — the user has decided
that one incident does not justify a per-click state read on every Greenhouse form. Fill Greenhouse like Ashby: no per-click state read needed. If a tab comes
back showing a confirmation page, apply SKILL.md 9.4 — ask whether they clicked it, log `applied`.
Still never batch across the final Submit click yourself.

## Quirks
- Name is **split** into first/last, unlike Ashby.
- Some orgs embed the form in an iframe on their own domain; the schema call still works
  if you can recover org + job id from the page.
- Submit validates a reCAPTCHA Enterprise token minted in-page. Never attempt an API submit.
- Demographic questions come as a separate block with their own option ids.

## Known question → answer mappings
| Question contains | Answer |
|---|---|
| "require Visa Sponsorship now, or in the future" | Yes |
| "authorization to work in the country" | I am authorized to work in this country |
| "currently based in" / "live in one of the following" | United States |
| "How did you hear" / "where did you first hear" | the job board the link came from (hard rule 7: Handshake / Jobright / LinkedIn / Indeed / …), else Company website |
| LinkedIn Profile | <linkedin-url> |
| Github | <github-url> |
| Website / Portfolio | leave blank |
