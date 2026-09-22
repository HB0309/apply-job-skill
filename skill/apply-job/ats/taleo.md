# Taleo (Oracle Taleo career sections) — playbook

**Detect:** `*.taleo.net/careersection/...`  ·  First seen 2026-08-21 (MassCareers / Commonwealth of Massachusetts)
**Auto-submit risk:** LOW — an explicit "Review and Submit" step exists and Save-and-Continue never submits.
**No schema API.** Job *detail* pages are AJAX-rendered: `curl` returns the shell only, and
`/careersection/rest/jobboard/v1/job/<id>` 404s. Use Chrome + `get_page_text` for the posting.

## Flow shape
`Apply Online` → **Privacy Agreement** (I Accept / I Decline) → **account sign-in/creation** →
numbered wizard. MassCareers ran 11 steps, renumbering to 10 after the résumé step:
1 Personal Information · 2 General Questions · 3 Job Specific Questions · 4 Education ·
5 Employment History · 6 Licenses and Certifications · 7 File Attachments ·
8 Electronic Signature · 9 Diversity Survey · 10 Review and Submit.

## Hand-offs required (do not do these yourself)
- **Privacy Agreement** — accepting terms is the user's call.
- **Account creation / sign-in** — prohibited.
- **Electronic Signature (step 8)** — a full-name field that is explicitly "the electronic
  equivalent of a hand-written signature" and authorizes a **full background investigation**
  plus transmission of PII to a third party. Always hand this to the user. When handing it over,
  say that this one takes the **legal** name (`<Full Name>` / `<legal last name>`), not the everyday one —
  it feeds the background check, which is matched against the work-authorization record.
  See `form-data.md` → **Name convention**.

## Mechanics
- **`Save and Continue` is a full page navigation** (JSF postback), not AJAX. Never hold a JS
  context across it — `await sleep()` after the click dies with "Inspected target navigated".
  Click in one call, read state in the next.
- **`Add Work Experience` / `Add License` links are also full postbacks.** Element refs from
  `read_page`/`find` go stale after any of these — re-find rather than reusing a ref.
- Plain `input`/`select`/`textarea` elements: the native-setter + `input`/`change` pattern works,
  and `selectedIndex` + `change` works for dropdowns. No react-select anywhere.
- Dates are **Month/Year dropdown pairs** (`Month|Jan|Feb...`, `Year|2049|2048...`), not text.
- Repeating blocks are flat and fixed-width: Employment History is **12 fields per block** in
  order — Employer, Job Title, StartMonth, StartYear, EndMonth, EndYear, Current Job checkbox,
  Description textarea, Supervisor Name, Supervisor Title, "may be contacted" checkbox,
  Supervisor Phone. Index with `block*12 + offset`.

## ⚠ Résumé-parse prefill is WRONG — always verify
Taleo parses the uploaded PDF and pre-populates Education and Employment, **scrambled**.
Observed on the first run:
- An orphan 3rd education row: no institution, Program `INFORMATION SECURITY`, Level `Other`. Clear it.
- Employer collapsed to `<Univ>` with an **empty** Job Title.
- <filler entry>'s dates (Aug–<Mon YYYY>) paired with the **<Employer D>** job title.
Re-write every prefilled field from `form-pack.md`; never trust the parse (SKILL.md rule 9b).
Order = PDF, most recent end date first; after `Save and Continue` re-read every block's
Description textarea in full before moving on.

## File Attachments (step 7)
The résumé uploaded at step 1 appears here automatically. The **"Relevant Files" checkbox is
load-bearing** — the page states that unchecked attachments, résumé included, are NOT submitted
with the application. They defaulted to checked; verify they still are.

## Known question → answer mappings
| Question | Answer |
|---|---|
| "legally authorized to work in the US **on an unrestricted basis**" | **Not plain Yes.** Where a third option exists ("I will need employer sponsorship or a specialized training program"), pick that — it is the truthful one for <visa type>. |
| immediate family in state government | No |
| prior employment with this employer/state | No |
| Source Type | the job board the link came from if listed (hard rule 7), else `Our Web Site` → dependent sub-dropdown appears → `Career Section` |
| Primary Number | Cellular Phone |
| Supervisor contact / "may be contacted" | leave unchecked, per form-data references policy |
