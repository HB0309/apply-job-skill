# Fill phase — reference (read by the `apply-job-fill` subagent at the start of every form)

This is step 9 of the main flow. SKILL.md holds the orchestrator's contract; the agent definition
`~/.claude/agents/apply-job-fill.md` holds modes, the stuck rule and the return format; this file
holds the mechanics and the handoff block. The orchestrator never reads it.

## 9. Fill the form in Chrome
Your tab is the one you created (or were handed in `resume` mode) — one tab per posting. It stays
open through handoff; the orchestrator closes it after the user confirms submission.

**`form-pack.md` from the application folder is your ONLY input.** It already holds every value,
resolved. If something is missing, that is a gap in the pack, not a reason to read the pool.

**The platform playbook is already inside the pack** ("Platform playbook" section, copied
verbatim by `jobkit formpack`) — read it there, *before* filling. Load an `ats\<platform>.md`
file yourself only when the form turns out to be on a different platform than the pack names
(Apply redirects to Workday; Phenom behind a company domain — apply route `/us/en/apply?jobSeqNo=`).
When a form misbehaves in a way the playbook does not cover, read
`<skill folder>\references\ats-quirks.md` (widget fixes that apply across platforms).

**Flags from prep.** The pack's `**Flags:**` line (e.g. `t2-h1b — no E-Verify…`, or `none`) is
copied into the handoff's `Flags:` line. It never goes into a form answer.

### 9.0 How a page is verified: the read-back script, not screenshots
`<skill folder>\references\readback.min.js` — read it once per run, then
paste it verbatim as one `javascript_tool` call on every freshly loaded page. It prints the page
header (URL, heading, `CONFIRMATION` flag, cross-site frames, visible errors) and the field
list, and defines helpers for the rest of that page:
- `__rb(<n>)` — next page of the field list when the output ends with `MORE __rb(<n>)`.
- `__rbCheck([["<label fragment>", "<expected value>"], ...])` — the verification. Pass every
  field you filled on this page, values copied from `form-pack.md` (long descriptions and
  screener answers in full; checkboxes as `"checked"` / `"unchecked"`). It prints
  `CHECK x/y ok` plus only the problems: `BAD` (with the first differing position for long
  text), `MISSING field`, `EMPTY REQ` (a required field not filled, incl. an unticked required
  box), and page errors. Fix every line, re-run, repeat until it is clean.
- `__rbHeader()` — the header alone, for the post-click check (9.4).
- If a helper throws "not defined", the page fully reloaded: paste the script again.
The tool cuts any output at about 1,000 characters, which is why the script never prints more
than that. Do not write your own dump of the page. A result reading `BLOCKED: Cookie/query
string data` is the extension's privacy filter reacting to a URL-like value: re-run the same
call wrapped as `(…).replace(/[?=&]/g, '_')`. The source with comments is `readback.js`;
(maintainers rebuild the paste file with `python bin/build_readback.py`; if the script misbehaves,
log it with `fail add`).

**When the script sees no fields.** `XFRAME` in the header means the form sits in a cross-site
frame (a Greenhouse embed on a company domain): `navigate` the tab to the URL it prints and
work there. `FIELDS 0` with no `XFRAME` means the form has not rendered yet (click Apply, wait,
paste again) or it uses a structure the script cannot read: verify that page with
`read_page(filter:"interactive")` plus the one screenshot instead, and log it as a skill
failure so the script can be taught.

**Screenshots: one per page, at the moment it matters.** Take ONE `computer screenshot` with
`scale: 0.5` right before each advancing click (Next / Continue / Save and continue), after
`__rbCheck` is clean — it catches what the DOM cannot show: a modal over the form, a banner, a
field that visibly failed. Take one more at the final Submit screen. Beyond that, screenshot
only when `__rbCheck` reports a problem you cannot explain from the text, or a click did not do
what you expected. **No screenshot after every click or keystroke, and no scrolling to look at
the page**: click by `ref` (from `read_page` or `find`), which needs no scrolling.

### 9.1 If `form-pack.md` carries a fill plan (Ashby / Greenhouse)
The prep phase already mapped every field key to a value against the platform's own schema.
1. Open the page, paste the read-back script (this is your read of the form).
2. `file_upload` the résumé FIRST (the file on the pack's `Résumé PDF:` line; needs a
   `read_page` ref). Ashby and Lever re-parse the upload into the fields, so filling before it
   gets overwritten.
3. **One `browser_batch`** executing the plan — `form_input(ref, value)` per field, refs
   resolved from one `read_page(filter:"interactive")`.
4. **`__rbCheck`** with every planned value; fix and re-check until clean.
No exploratory read of the form beyond this.

### 9.2 Otherwise — DOM path
1. Paste the read-back script for the field list, then **one `read_page(filter:"interactive")`**
   for the `ref_` ids. If fields sit behind an "Apply" button or render lazily, trigger that,
   then paste the script again.
2. **Fill with one `browser_batch`** of `form_input(ref, value)` calls — a whole page of fields
   in a single round trip. For React-controlled inputs that resist it, use the native setter
   (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,val)` then
   dispatch `input`+`change`); real checkboxes/radios via `el.click()`. Map by label, never by
   raw index — index shifts with hidden widget inputs.
3. **`__rbCheck`** covering every field on the page. This is what catches silent failures.
4. **`find` (natural-language lookup), then real clicks, only for stubborn widgets** — some
   react-select dropdowns ignore synthetic events and need a real trusted click. Click by **`ref`**
   (the `computer` tool's `ref` param, taken straight from `find` or `read_page`); fall back to
   coordinates only for what refs genuinely cannot resolve (canvas-drawn controls, hover-only
   reveals). Batch a widget's click → type → Enter in one `browser_batch` when you can predict it.
5. **Multi-step wizards:** per page — read (script) → fill → `__rbCheck` clean → one
   screenshot → advancing click → post-click check (9.4). Still stop before the final Submit.
6. **A page is never left on the assumption that the batch fill worked.** `__rbCheck` must be
   clean (or every remaining line explained and listed for the handoff) before the advancing click.

### 9.3 Batching boundary — safety, non-negotiable
**Never batch across a click** that navigates, advances, or might submit. `browser_batch` stops
on error but does **not** check page state between items, so batching across a click would
silently defeat the auto-submit guard below. Batch field fills *within* one page only.

### 9.4 You click Next yourself — the post-click check is what makes that safe
After **every** advancing click, before anything else, read the new page: paste the script (a
full reload wiped the helpers) or, on single-page-app wizards where it survives, call
`__rbHeader()`. Expected next page → carry on. Same page with an error → fix and retry. A
`CONFIRMATION YES` you did not expect → STOP, return `AUTO_SUBMITTED` with the page you were on.

Two traps where the advancing control IS the submit, so you do not click it:
- **Phenom `/hvhapply`** — uploading the résumé submits a bare application. Check the URL before
  any upload. On `hvhapply`, rewrite the URL to `/us/en/apply?jobSeqNo=<same value>` and
  `navigate` there: if the normal wizard renders, fill it like any other form. If only `hvhapply`
  works, do not upload anything — return `BLOCKED` ("hvhapply: the upload IS the submit; the user
  uploads, which submits it").
- **Oracle CX** — can submit with no Submit button once the last required field is complete
  (TI/edbz). Fill everything except the **last remaining required field**, then hand off with
  that field named under `Unanswered` and the handoff's first line saying there may be no
  Submit button: completing that field may submit.
Oracle CX and SmartRecruiters also expire idle sessions and destroy the form: fill them in one
uninterrupted block, and never stop mid-form for a question (agent brief).
**Greenhouse, Ashby and Lever are single pages** — there is no advancing click to verify; the
final `__rbCheck` plus one screenshot is the whole verification.

**Free-text answers.** Paste screener answers from `form-pack.md` exactly. If a box appears that
the pack has no answer for, it is skipped and listed (agent brief, "When to stop") — you do not write
answers. The one exception is a trivially factual box the pack covers under another label (e.g.
"LinkedIn" vs "LinkedIn profile URL").

**9a. Optional sections are not optional.** If the form offers Education, Work Experience, Certifications, Skills, Projects, Languages, or Websites — fill them **completely**, even when the section or its fields are unmarked/optional, and fill every sub-field inside each entry (start and end month/year, city/state/country, degree, major, GPA, employer, title, currently-work-here flag, description text). A half-filled section reads worse to a recruiter than the PDF alone, and some ATS parsers score these structured fields rather than the attachment. Use "Add another" until every entry is in.
- **Which entries:** exactly the Experience and Project entries on the tailored PDF, in the same order (most recent end date first — rule 9b) — the form and the résumé must tell one story. Education is always both degrees; certifications always <certification>.
- **Job description / responsibilities free text:** paste the bullets **already prepared in `form-pack.md`** for that entry. Do not re-derive them from the `.tex`.
- **Dates:** every education and employment date is already resolved in `form-pack.md`. The current role gets the "I currently work here" flag, never a fabricated end date.
- **Reason for leaving, languages, references, certification details, GPA and the standard yes/no defaults** are all in `form-pack.md`. Never improvise per form.
- **Do not fabricate to fill a field.** If a value is genuinely unknown (date of birth, a GPA not on file, a supervisor's phone), leave it blank or "N/A": nothing is ever invented. This step widens *coverage*, never invention.
- **Transcripts: attach when asked** — paths and the which-is-which rule are in the pack's Transcripts section. A required transcript upload is never a reason to skip a posting.
- **Carve-out:** an optional *cover letter* upload stays on-request only. Optional demographic questions use the pack's Locked fields answers.
- **The ATS's own review page is the source of truth, not the DOM.** Some platforms (Phenom People) accept a JS-set text value into the DOM and silently never send it — `__rbCheck` says the field is correct while the server still holds the résumé parser's original. Where a wizard has a final review/summary step, read it (`get_page_text`) and diff it against `form-pack.md` before the handoff; if a value did not stick, go back and enter it with **real keystrokes**. See `ats\phenom.md`.
- **Widget caution:** the playbook in the pack lists that platform's traps — e.g. Workday's date spinbuttons and Field-of-Study lookups reject JS-set values and need real clicks plus Enter. Read it *before* filling these sections, not after they fail.

**9b. Work experience and education are entered by hand, every time.**
Assume the form has **no usable autofill**. A résumé parse, a returning-candidate profile, or
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
3. **Check before Next, then verify after the page commits.** Before Next/Save on the experience
   or education page, `__rbCheck` every entry's fields with the full description text. After the
   commit, a DOM read proves the DOM holds the value, not that the ATS stored it — Workday keeps
   a JS-set description in the DOM and drops it on Save. So when the page re-renders, re-open or
   re-read **every** entry and `__rbCheck` its full description, title, employer and dates again.
   Any mismatch → fix → Save → re-check. Never accept a truncated preview as verification.
4. **Handoff gate.** The handoff must carry
   `Work experience: <n> of <n> entered, order = PDF, descriptions verified after save` and the
   matching Education line. If that line cannot be written truthfully the fill is not done —
   go back; do not hand off.
- Do this *after* the résumé upload, never before — on iCIMS and SuccessFactors the upload wipes
  prior work (see those playbooks).
- Description fields that reject JS-set text (Workday, SuccessFactors) are typed with real
  keystrokes (`computer` click + type). The playbook says which widgets need that.
- Ashby and Greenhouse rarely offer these sections; when they do, the same rule applies.

Upload the PDF named on the pack's `Résumé PDF:` line with `file_upload` (needs the file input's ref from `read_page`). Fill
screener questions from the screener answers in the pack.
**Locked fields: fill directly from the pack, no confirmation pause.**
**Stop at the END of the form, not at the first uncomfortable page.**
EEO / voluntary self-identification, e-signature (typed name + date), and terms-and-conditions
acknowledgement pages are part of the fill, not stop points — fill and check them like any
other page and keep going. The only stop is the final review/Submit screen.

**Consent checkboxes (standing rule).** Tick the standard ones the application needs:
privacy policy / data processing / GDPR consent, terms of the application, "the information I
provided is true" certifications, e-signature acknowledgements, and a REQUIRED "may we text you"
question (answer Yes). Leave optional marketing opt-ins unticked: job alerts, newsletters, an
optional "text me updates" box, talent-community sign-ups. List both in
the handoff.

When everything is filled: STOP before the submit button. The handoff block, inside your return:
```
Form filled through the last page — review and click Submit.   (Oracle CX: "…fill the last field; it may submit with no Submit button.")
Flags: <the pack's **Flags:** line, e.g. none>
Posted: <YYYY-MM-DD> (<N> days ago) | or: Posted: unknown
Locked fields entered: work auth <x> | sponsorship <x> | salary <x> | start date <x> | gender/race/veteran/disability <x>
Work experience: <n> of <n> entered, order = PDF, descriptions verified after save | or: no section offered
Education: <n> of 2 entered, verified after save | or: no section offered
Optional sections filled: <list, or "none offered">
Consent: ticked <list> | left unticked <list of opt-ins>
Unanswered: <every skipped question, with its exact label, or "none">
```

**Account / login walls.** Some portals (Workday, SuccessFactors, etc.) require creating an
account or signing in before the application. Get the page to the login wall and return
`BLOCKED` ("login wall"); the user signs in themselves and the orchestrator resumes you. The
never-create / never-type-a-password rule is in the agent brief.
