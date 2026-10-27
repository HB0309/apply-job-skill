# Greenhouse — playbook

**Detect:** `job-boards.greenhouse.io/<org>/jobs/<id>`, `boards.greenhouse.io`, embedded iframes
**45 applications** · **Auto-submit risk: low.**

## Schema-first (preferred)
`python bin/jobkit.py schema <url>` → `GET boards-api.greenhouse.io/v1/boards/<org>/jobs/<id>?questions=true`
Returns every field's exact `name` attribute, type, required flag and all option labels,
plus `demographic_questions` and `compliance` blocks.

Stable keys: `first_name`, `last_name`, `email`, `phone`, `resume`, `cover_letter`.
Custom questions are `question_<digits>` — map by label from the schema.

Types: `input_text` · `input_file` · `multi_value_single_select` · `textarea`.

## Auto-submit
No per-click state read is needed: fill Greenhouse like Ashby. If a tab already shows a
confirmation page before you touched it, return `BLOCKED` ("confirmation already shown"); the
orchestrator asks the user (SKILL.md step 9, "Multi-link runs"). Never batch across the final
Submit click.

## Education block — the school list is US-only (2026-09-10)

When a Greenhouse form renders an Education block, School / Degree / Discipline are typeahead
selects that accept **only** values from Greenhouse's own list. Real clicks; typing then Enter
is the reliable pattern (`ref` + type + `Return`), not coordinate clicks.

- **A non-US university may not be in the list.** Searching its name can return unrelated
  colleges or nothing. **Delete the second education
  entry rather than substitute a different school** — hard rule 1. The résumé PDF still carries it, so nothing is lost.
- **Discipline: neither `<field of study>` nor `Information Security` exists.** Fall back
  to `Computer Science`.
- Degree: `Master's Degree` matches exactly (also `Master of Business Administration (M.B.A.)`
  etc. — pick the plain one).
- Education entries are usually optional; one entry satisfies the block.

## Transcript uploads (2026-09-10)

Some new-grad postings add a **required** file question for an undergraduate transcript
(Verkada: `question_12557165007`). Attach `master\<University B>_Official Marksheets_<Full Name>.pdf`
— see `form-data.md` → Transcripts for which document maps to which request.

## Multi-select demographic widgets

The U.S. Standard Demographic block uses **multi-value** comboboxes that render selections as
removable chips. Typing into one while another is focused appends text to the *wrong* field —
always click the specific combobox by `ref` first, then type, then `Return`. Verify by reading
the chip text, not the input value.

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
