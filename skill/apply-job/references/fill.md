# Fill phase — reference (loaded by the fill phase only)

This is step 9 of the main flow. SKILL.md holds the contract; this file holds the mechanics and
the handoff block. Load it once per session, when the first form is about to be filled. Never
load it for inbox, insights, scan, or the prep phase.

## 9. Fill the form in Chrome
Invoke claude-in-chrome skill if not already active. Open the job link in a new tab inside the
session's tab group — one tab per posting, created when that posting's fill begins, never a tab
reused from another posting. The filled tab stays open through handoff; close it only after the user
confirms submission and `jobkit track set … --status applied` has run.

**Read `form-pack.md` from the application folder. That is your ONLY input.** It already holds
every value, resolved. Do not open `content-pool.tex`, `qa-bank.md`, `resume-style.md`, or the
`.tex` — if something is missing, that is a gap in the pack, not a reason to read the pool.

**The platform playbook is already inside the pack** ("Platform playbook" section, copied
verbatim by `jobkit formpack`) — read it there, *before* filling. Load an `ats\<platform>.md`
file yourself only when the form turns out to be on a different platform than the pack names
(Apply redirects to Workday; Phenom behind a company domain — apply route `/us/en/apply?jobSeqNo=`).

#### 9.1 If `form-pack.md` carries a fill plan (Ashby / Greenhouse)
The prep phase already mapped every field key to a value against the platform's own schema.
1. Open the page.
2. **One `browser_batch`** executing the plan — `form_input(ref, value)` per field, refs
   resolved from one `read_page(filter:"interactive")`.
3. **One JS read-back** verifying every field.
4. `file_upload` the résumé PDF (needs a `read_page` ref).
No exploratory read of the form. Expect ~5–8k tokens instead of 40–60k.

#### 9.2 Otherwise — DOM path
Screenshots and scrolling are the expensive, error-prone way; the DOM covers the whole form
regardless of viewport.
1. **One `read_page(filter:"interactive")`** → accessibility tree with `ref_` ids and labels.
   Add ONE `javascript_tool` enumeration only if labels are ambiguous. If fields are behind an
   "Apply" button or lazy-render, trigger it, then re-read.
2. **Fill with one `browser_batch`** of `form_input(ref, value)` calls — a whole page of fields
   in a single round trip. For React-controlled inputs that resist it, use the native setter
   (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,val)` then
   dispatch `input`+`change`); real checkboxes/radios via `el.click()`. Map by label, never by
   raw index — index shifts with hidden widget inputs.
3. **Verify EVERY field via ONE JS read-back** (value / checked / the react-select's shown text
   or selected-state class). This is what catches silent failures. **Never report "filled" from
   a screenshot.**
4. **`find` (natural-language lookup), then real clicks, only for stubborn widgets** — some
   react-select dropdowns ignore synthetic events and need a real trusted click. Get coords via
   `getBoundingClientRect()` after `scrollIntoView`, then one `computer` click to open and one
   to pick. Use sparingly.
5. **Multi-step wizards:** read → fill → **page check** → Next, per page, re-reading on each new
   page. Still stop before the final Submit.
6. **Page check before every Next / Save / Continue.** Before any click that
   leaves the page, do ONE full read-back of every field on that page — text values, selected
   option text, checkbox/radio state, uploaded file name, and the full text of every long-text
   field — and compare it against `form-pack.md`. Fix every mismatch and re-read before clicking.
   Then, on the page that appears after the click, confirm it is the expected next step and not a
   validation error or the same page re-rendered with fields dropped. A page is never left on the
   assumption that the batch fill worked.

#### 9.3 Batching boundary — safety, non-negotiable
**Never batch across a click** that navigates, advances, or might submit. `browser_batch` stops
on error but does **not** check page state between items, so batching across a click would
silently defeat the auto-submit guard below. Batch field fills *within* one page only.

#### 9.4 You click Next yourself — the post-click check is what makes that safe
Since 2026-09-19 there is no per-click handoff: you advance every page on every platform. After
**every** advancing click, before anything else, run one `javascript_tool` that returns
`location.href`, `document.title`, the first `h1`/`h2` text and whether the body contains
"thank you" / "application received" / "successfully submitted". Expected next page → carry on.
Same page with a validation error → fix and retry. A confirmation you did not expect → STOP,
report an auto-submit, log the row `applied --notes "auto-submitted at <page>"`.

Two traps where the advancing control IS the submit, so you do not click it:
- **Phenom `/hvhapply`** — uploading the résumé submits. Check the URL before any upload; if it
  contains `hvhapply`, hand the tab to the user.
- **Oracle CX** — can submit with no Submit button once the last required field is complete
  (TI/edbz). Fill everything except the final field of the last section, then hand off.
Oracle CX and SmartRecruiters also expire idle sessions and destroy the form: fill them in one
uninterrupted block, never while waiting on the user.
**Greenhouse is a single page — there is no advancing click to verify.** One genuine embed auto-submit exists on
record; the later ones logged as auto-submits were the user submitting finished forms themselves
during multi-link runs — see below. Fill Greenhouse like Ashby; if a confirmation page
appears, apply the rule below instead of stopping the run.

**Multi-link runs: a form found in a submitted state was submitted by the user.** When several
applications are open in one session they submit the ones that are complete while the fill
continues elsewhere. If a tab you return to shows a confirmation page, do not report an
auto-submit and do not stop the run: ask one line (`<Company> shows submitted — you clicked
it?`), and on yes log the row as `applied`. Report an auto-submit only when the state changed
during **your own** click on a form that had not been handed to them.

**Free-text answers (standing rule).** Paste screener answers from `form-pack.md` exactly.
If a box appears that the pack has no answer for and you write one, use only commas and
periods: no colons, semicolons or dashes as sentence punctuation, and never describe
<product> as "implemented validation rules" or "reviewed every pull request" (they leads the
team, reviewed its token handling, and wrote the error handling).

**9a. Optional sections are not optional.** If the form offers Education, Work Experience, Certifications, Skills, Projects, Languages, or Websites — fill them **completely**, even when the section or its fields are unmarked/optional, and fill every sub-field inside each entry (start and end month/year, city/state/country, degree, major, GPA, employer, title, currently-work-here flag, description text). A half-filled section reads worse to a recruiter than the PDF alone, and some ATS parsers score these structured fields rather than the attachment. Use "Add another" until every entry is in.
- **Which entries:** exactly the Experience and Project entries that survived step 3a onto the tailored PDF, in the same order (most recent end date first — rule 9b) — the form and the résumé must tell one story. Education is always both degrees; certifications always <certification>.
- **Job description / responsibilities free text:** paste the bullets **already prepared in `form-pack.md`** for that entry — the prep phase copied them from the compiled PDF and stripped the LaTeX. Do not re-derive them from the `.tex`.
- **Dates:** every education and employment date is already resolved in `form-pack.md`. The current role gets the "I currently work here" flag, never a fabricated end date.
- **Reason for leaving, languages, references, certification details, GPA and the standard yes/no defaults** are all in `form-pack.md` (sourced from `form-data.md`). Never improvise per form.
- **Do not fabricate to fill a field.** If a value is genuinely unknown (date of birth, a GPA not on file, a supervisor's phone), leave it blank or "N/A" — hard rule 1 still governs. This step widens *coverage*, never invention.
- **Transcripts: attach when asked** — paths and the which-is-which rule are in the pack's Transcripts section. A required transcript upload is never a reason to skip a posting.
- **Carve-out:** an optional *cover letter* upload stays on-request only (§7a). Optional demographic questions follow hard rule 4.
- **The ATS's own review page is the source of truth, not the DOM.** Some platforms (Phenom People, confirmed Rocket 2026-09-10) accept a JS-set text value into the DOM and silently never send it — a read-back says the field is correct while the server still holds the resume-parser's original. Where a wizard has a final review/summary step, read it and diff it against `form-pack.md` before the handoff; if a value did not stick, go back and enter it with **real keystrokes**. See `ats\phenom.md`.
- **Widget caution:** the loaded `ats\<platform>.md` playbook lists that platform's traps — e.g. Workday's date spinbuttons and Field-of-Study lookups reject JS-set values and need real clicks plus Enter. Read the playbook *before* filling these sections, not after they fail.

**9b. Work experience and education are entered by hand, every time.**
Assume the form has **no usable autofill**. A resume parse, a returning-candidate profile, or
"Use my last application" may pre-populate these sections; that data is treated as absent, not
as a head start — it has shipped wrong on Workday, Taleo, Talemetry and SuccessFactors.
1. **Every entry, every field.** For each Experience entry in `form-pack.md` — exactly the
   entries on the PDF — enter title, employer, location, start month/year, end month/year or the
   currently-work-here flag, reason for leaving where asked, and the **full description text**
   pasted from the pack. Same for both Education entries. Use "Add another" until the count
   matches the pack; delete every parser-invented extra, duplicate or merged block.
2. **Order = the PDF = most recent END date first, current role at the top** (today: Community
   Dreams, <Employer B>, <filler entry>, <Employer D>). Start date does not decide order. If the widget
   sorts by creation order or start date and offers no reorder control, clear the section and
   re-enter in PDF order so the recruiter sees the same sequence as the résumé.
3. **Page check before Next, then verify after the page commits.** Before clicking Next/Save on
   the experience or education page, read back every entry on it (all fields, full description
   text) and compare to the pack — 9.2 step 6. Then, after the commit: A JS read-back proves the DOM holds
   the value, not that the ATS stored it — Workday keeps a JS-set description in the DOM and
   drops it on Save. So: fill → Save / Next → when the page re-renders,
   re-open or re-read **every** entry and compare its full description against the pack bullet
   for bullet, plus title, employer and dates. Any mismatch → fix → Save → re-read again. Never
   accept a truncated preview as verification (that is exactly how a truncated entry has shipped before).
4. **Handoff gate.** The step-9 handoff must carry
   `Work experience: <n> of <n> entered, order = PDF, descriptions verified after save` and the
   matching Education line. If that line cannot be written truthfully the fill is not done —
   go back; do not hand off.
- Do this *after* the résumé upload, never before — on iCIMS and SuccessFactors the upload wipes
  prior work (see those playbooks).
- Description fields that reject JS-set text (Workday, SuccessFactors) are typed with real
  keystrokes (`computer` click + type). The loaded playbook says which widgets need that.
- Ashby and Greenhouse rarely offer these sections; when they do, the same rule applies.

Upload the compiled PDF with `file_upload` (needs the file input's ref from `read_page`). Fill screener questions from the approved `screener-answers.md`.
**Locked fields: fill directly, no confirmation pause (hard rule 4).**
**Stop at the END of the form, not at the first uncomfortable page.**
EEO / voluntary self-identification, e-signature (typed name + date), and terms-and-conditions
acknowledgement pages are part of the fill, not stop points — fill and check them like any
other page and keep going. The only stop is the final review/Submit screen. If the run halts on
an EEO, signature, or T&C page, it stopped too early.

When everything is filled: STOP before the submit button. Tell the user:
```
Form filled through the last page — review and click Submit.
Posted: <YYYY-MM-DD> (<N> days ago) | or: Posted: unknown
Locked fields entered: work auth <x> | sponsorship <x> | salary <x> | start date <x> | gender/race/veteran/disability <x>
Work experience: <n> of <n> entered, order = PDF, descriptions verified after save | or: no section offered
Education: <n> of 2 entered, verified after save | or: no section offered
Optional sections filled: <list, or "none offered">
Unanswered: <any pause-trigger question left blank, or "none">
```
Never click Submit yourself. If a pause trigger from rule 4 fired mid-fill, leave that field blank and list it under `Unanswered` rather than stopping the fill — unless a blank there blocks Submit, in which case stop and ask right then.

**Account / login walls.** Some portals (Workday, SuccessFactors/L3Harris, etc.) require creating an account or signing in before the application. NEVER create accounts or enter passwords/OTPs to authenticate — this is a prohibited action even if the user offers credentials (do not store or reuse any password they paste; if they share one, tell them to rotate it). Instead: get the page to the login wall, then STOP and hand them the browser — "your turn to log in." They create the account, sign in, or enter any OTP themselves. When they say they're logged in, take back over and fill everything else (tailor, fields, resume upload, screeners), stopping before Submit as usual.
