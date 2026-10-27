# Lever — playbook

**Detect:** `jobs.lever.co/<company>/<uuid>` (the form is at `…/<uuid>/apply`).
**Auto-submit risk: none known.** One page, one "Submit application" button at the bottom.
Single-page form: eligible for one-form-ahead mode (SKILL.md step 9).

## Layout (seen 2026-09-28, Palantir, read-only)
- Top card: `Resume/CV` file input ("ATTACH RESUME/CV"), `Full name` (single box: legal-name
  rule, `<legal full name>`), `Email`, `Phone`, `Current location`, `Current company`.
- Links card: `LinkedIn URL`, `GitHub URL`, `Portfolio URL`, sometimes `Other website`.
- Custom question cards below: text boxes, dropdowns, radio groups, and multi-select checkbox
  groups (e.g. a list of languages, each box marked required as a group).
- Optional EEO card at the end (gender, race, veteran, disability dropdowns).
- Plain server-rendered HTML inputs: `form_input` by `read_page` ref works; the read-back sees
  every field with its label.

## Method
Upload the résumé first (Lever may parse it into name, email, phone, company), then fill every
field from the pack and `__rbCheck` the whole page, so a parser overwrite is caught.

## Unverified
Whether the résumé parse ever overwrites a field already typed, and whether any tenant adds a
second page. Log a skill failure the first time either is seen.
