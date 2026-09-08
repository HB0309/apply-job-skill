---
name: apply-job
description: Auto job-application pipeline. Use when the user pastes a job link to apply for (tailors resume, fills the form in Chrome, pauses before submit), says "apply-job inbox" (morning Gmail check that updates the tracker), "apply-job insights" (analyzes which applications convert), "apply-job sweep" (process pre-scored candidates from the job-matcher project), or "apply-job scan" (browse Handshake/Jobright/LinkedIn recommended pages via the user's live session and queue matches). Triggers on job posting URLs, "apply to this job", "check my application inbox", "application insights", "sweep", "scan", "process job-matcher candidates".
---

# /apply-job — Auto Job-Application Pipeline

Paste a job link → tailored one-page resume → form filled in Chrome → user clicks Submit.

## Fixed paths
- Workspace: `<WORKSPACE>\`
- **Read layer: `bin\jobkit.py`** — ALWAYS use this instead of reading the big files.
  `dup <url>` · `posted <url>` · `count` · `pool tex|notes` · `qa list|get` ·
  `pagefit <pdf>` · `atscheck <pdf>` · `atsfix <pdf>` · `similar <job-posting.md>` · `schema <url>` · `insights` ·
  `sweep-list` · `sweep-done <job_id>` · `sweep-prune` · `scan-add` · `track add|set|active|employer|audit`.
  Reading `tracker.md`, `qa-bank.md`, or `content-pool.tex` in full is a bug, not a fallback.
- job-matcher feed (sweep mode only): `job-matcher-feed\<track>\<date>\<job_id>.json`, written by a
  separate project's scheduler — query via `jobkit sweep-list`/`sweep-done`, never read directly.
- Content pool: `master\content-pool.tex` + `master\resume.cls` — **READ-ONLY, never edit.**
  Access it via `jobkit pool tex`, never directly.
- Profile: `master\profile.md` — read-only for you.
- Form-only data: `form-data.md` (this folder) — education start dates, certification details,
  reason-for-leaving lines, languages, standard yes/no defaults. READ before filling any form.
- Tracker: `tracker.md` — **never edit it directly.** Rows are written only by
  `jobkit track add` (step 10) and changed only by `jobkit track set`; the script escapes pipes,
  enforces the closed status vocabulary (`prepped filled applied viewed oa interview offer
  rejected withdrawn skipped duplicate blocked held review`) and dates the update. Narrative goes
  in `--notes`, never in the status.
- Compiler: `bin\tectonic.exe`
- Style guide: `resume-style.md` (this folder) — prep phase only.
- **ATS playbooks: `ats\<platform>.md`** — load ONLY the one matching the form's URL.
  `ashby` `greenhouse` `workday` `oracle-cx` `smartrecruiters` `icims` `taleo` `successfactors`
  `talemetry`, else `_unknown`. Workday also hides behind company domains (careers.homedepot.com,
  corporate.target.com, jobs.boeing.com) — if the Apply click lands on `*.myworkdayjobs.com`, or the
  form-pack says Workday, load `workday.md`.
- **References (load on demand, never all):**
  `references\tailoring.md` (steps 1–8, prep subagent) · `references\inbox.md` ·
  `references\insights.md` · `references\ats-quirks.md` (when a form misbehaves)
- Interview prep: `interview-prep\<company-slug>\` — one folder per company.
- Gmail reader: `bin\gmail\gmail_search.py`

## Modes
- `/apply-job <link> [<link> ...]` — apply to one or more jobs (main flow below)
- `/apply-job <link> --review` — force the full review checkpoint, tailoring stays inline
- `/apply-job <link> --fresh` — skip the variant cache, tailor from scratch
- `/apply-job inbox` — morning Gmail sweep (`references\inbox.md`)
- `/apply-job insights` — conversion analysis (`references\insights.md`)
- `/apply-job sweep [N]` — process job-matcher's pre-scored candidates (below). `N` optional, default 5.
- `/apply-job scan` — browse Handshake/Jobright/LinkedIn via the user's live Chrome session and queue matches (below). Meant to be run on a loop (`/loop 8h /apply-job scan`), not manually every time.

## Hard rules (apply to every mode)
1. **Never invent facts.** Every claim in any output must trace to a specific line in `content-pool.tex` or `profile.md`. No new skills, metrics, employers, titles, or dates. Reword, reorder, select — never fabricate.
2. **Never click Submit.** The user always clicks the final submit button.
3. **Never edit master files** (`master\content-pool.tex`, `master\profile.md`).
4. **Locked fields — FILL them, don't ask (changed 2026-08-21, replaces the old propose-then-confirm rule).** Work authorization, visa sponsorship, salary, notice period, and voluntary EEO self-ID all have stored answers. Fill them straight from those answers like any other field, in every mode, and verify each one with the JS read-back of step 9.3 — the read-back is the real safety net, not a prompt. Do NOT stop mid-form to confirm them. Recap every locked value actually entered in the step-9 handoff message, where the user reviews before clicking Submit. (The old confirmation rule was added 2026-08-06 after a mis-clicked race field; read-back verification catches that case, and pausing conflicts with Oracle CX session expiry — see the Oracle CX playbook.)

   **Canonical answers live in `master\profile.md` (identity, work authorization, visa,
   salary, notice period, EEO self-ID) and `form-data.md` (education dates, certifications,
   standard yes/no defaults).** The prep phase resolves every one of them into `form-pack.md`,
   so the fill phase never has to interpret them. Typical mappings the profile must settle:
   - Visa sponsorship asked as one *combined* "now or in the future" question vs. as two
     separate questions — the profile states both answers.
   - Salary: a range, plus the wording to use when a form forces a single number.
   - EEO: gender, race/ethnicity (closest option; fall back to "decline to self-identify"
     only if nothing maps), veteran status, disability status — each a direct answer.
   - Notice period / earliest start date.

   **Pause ONLY when** — this list is exhaustive; anything not on it gets filled:
   1. no stored answer exists for the question at all (it isn't in `profile.md`, `form-data.md`, or above), and the field is required;
   2. the widget's options genuinely don't map — e.g. a salary *band* picker whose every band sits outside <salary range>. (An EEO dropdown with no matching ethnicity option is NOT a pause: "decline" is the documented fallback.);
   3. the posting's own published pay range falls outside <salary range> — flag it before entering a number;
   4. a locked-*category* question never answered before (a genuinely new category, not a new phrasing of an old one).
5. **Behavior during runs: near-silent.** One short status line per step. The user sees the match-report headline and, at the end, the handoff recap of locked-field values; everything else is quiet. Reports are blunt — no false encouragement.
6. **`qa-bank.md` is answer-only.** `<WORKSPACE>\qa-bank.md` holds behavioral/story answers for screener text boxes and interview prep. NEVER read it into a résumé bullet, skill, or summary — it is walled off from résumé tailoring. It IS the source for narrative screener answers (challenge/proud-of/why questions); résumé facts still come only from master + profile.
7. **Referral source = the job board the link came from (added 2026-09-05).** Every pasted link
   carries its origin — check the URL's source/referral params (`gh_src`, `src`, `source`,
   `utm_source`, `lever-source`, `rcid`, …) and the surrounding context to identify the board:
   **Handshake, Jobright, LinkedIn, Indeed, Wellfound, or any other**. When the form asks "How did
   you hear about us?" / "Source" / "Referral source", pick **that board** from the options. If the
   identified board is not offered, fall back to the **company careers site / company website**
   option (then "Other" with the board's name typed in, if the widget allows free text). Always
   apply through the exact link given — never re-find the posting on a different board. Carry the
   identified source into `form-pack.md` during prep so the fill phase does not re-derive it.

---
## Main flow: `/apply-job <link> [<link> ...]`

**Two phases. Prep is delegated and parallel; filling is serial and stays in this thread.**

```
step -1  jobkit posted <url>           per link, here, ~30 tokens each
step 0   jobkit dup <url>              per link, here, ~100 tokens each
PREP     one subagent per surviving link, launched IN PARALLEL
           each reads references/tailoring.md and runs steps 1-8 for its posting
           each writes  job-posting.md, resume .tex/.pdf, match-report.md,
                        screener-answers.md, form-pack.md
           each returns VERDICT + reason + folder + pagefit verdict + reuse note
FILL     serial, here, one job at a time  -> steps 9, 9a
step 10  append the tracker row
```

### Posting-date check (standing rule)
Runs FIRST — before the duplicate check, before prep, before the browser. A stale posting
is usually already deep in a pipeline, and catching it here costs ~30 tokens instead of a
full tailoring run.

`python bin/jobkit.py posted "<url>"` → one line, one of three verdicts:
1. `FRESH date=<YYYY-MM-DD> age=<N>d confidence=<level>` — 0–3 days old. Continue to
   step 0 silently. **Carry the date and age forward** — every later step needs them.
2. `STALE date=<YYYY-MM-DD> age=<N>d confidence=<level>` — older than 3 days. STOP for
   that link. Report and wait:
   `<Company> <Role> — posted <YYYY-MM-DD> (<N> days ago, confidence <level>). Older than
   3 days. Apply anyway?`
   Do not run the duplicate check, do not launch prep, do not open the browser until they
   answer. On yes, resume the normal flow from step 0 and carry the date forward.
3. `UNKNOWN date=unknown reason=<r>` — the service could not date the page. **This is not
   a stop.** Record the date as `unknown` and continue the normal flow.

The gate is **age only**. Never infer freshness from a repost, an `updated` timestamp, or
a low-confidence guess — only the returned date counts. With several links, check them all
first and report the stale ones together, then proceed with the fresh ones rather than
blocking the whole batch. the user can override per posting.

If `jobkit posted` itself is broken (not merely unable to date a page), fall back once to
the **whenthisjobwasposted** MCP server — `mcp__whenthisjobwasposted__get_job_posting_date`,
deferred, load it with ToolSearch first. Never curl the API raw: the response is ~400
tokens of fields this gate does not use.

### 0. Duplicate check
`python bin/jobkit.py dup "<url>" --company "<C>" --role "<R>"` (company/role optional; they
catch the same job posted under two URLs). On `MATCH` or `FUZZY MATCH`: STOP for that link,
reply `Duplicate — applied to <company> <role> on <date>, status: <status>. Folder: <path>`,
and move to the next link. On `NONE`, continue. This first check sees only the URL; the prep subagent runs it again with
`--company --role` once the posting is fetched (tailoring.md step 1), which is what catches the
same job reached through Jobright, LinkedIn and the employer's own ATS.

### Pre-filter: auto-skip (standing rule — assumes the profile says sponsorship will be needed)
Before launching prep, skip the posting outright when **both** are true:
1. the posting's stated salary band tops out **below the profile's salary floor** (entire band under the floor —
   an overlapping range is fine and gets filled normally), **and**
2. the employer is a type that effectively cannot sponsor a work visa — **state or federal government,
   public agency, or defense**.
Either one alone is not enough: a below-floor role that sponsors still gets surfaced, and a
well-paid government role still gets surfaced. Report the skip, log the tracker row, stop.
the user can override per posting.

### Employer count and caps (check before fill, not before prep)
Before filling any posting run `python bin/jobkit.py track employer "<Company>"`. It prints how
many applications went to that employer in the last 30 days and, for employers with a published
cap (table in `bin\jobtrack.py`: OpenAI 5 per 6 months, TikTok 2 per program window, Canonical 4
per 6 months), the running count against the cap. State the line next to the match assessment
(`3rd application to Scale AI in 30 days` / `2 of 5 OpenAI used`). **A count is information,
not a stop** — the user applies to the same employer repeatedly on purpose. Only `AT CAP` pauses:
prep the posting, do not fill, and log it with `track add --status held --notes "cap"` (the
`applications\2026-08-22_openai_security-engineer-infrasec\` pattern).

### PREP — delegate steps 1–8
Launch one subagent per surviving link, **all in one message so they run in parallel**. Give
each: the link, its application folder path, the posting date and age from the gate above
(or `unknown`), and hard rules 1–7 **inline** (a subagent starts cold and must not depend on
recalling them). Tell it to read `references/tailoring.md`.

A subagent never clicks Submit and never drives the browser except to fetch a JS-rendered
posting. Links the hard filter verdicts **Skip** never reach the browser — report them, log
the tracker row, and drop them from the fill queue.

### Spot-check (parity test closed 2026-08-23, 7/7 scored — see the README's architecture section)
Delegated prep is the default: 87.5% selection agreement across 7 scored runs, zero shipped
factual-audit misses, sound framing including a proactive honesty catch on the hardest test
case. No inline dual-tailor comparison required anymore. Still spot-check every subagent's
output before filling the form: read the match report's Genuine Gaps section, and skim the
compiled résumé for any claim not traceable to a `jobkit pool notes` entry — same discipline
as any other review, not a full re-tailor. If a future run ships an actual fabrication (the
Honda driver's-licence class of error) or a scale-inflation claim, treat it as a new finding
and consider reopening spot verification, not a reason to silently lower the bar.

### 8. Checkpoint (trust-aware)
`--review` only: FULL REVIEW / teaching mode — show the tailored résumé changes with reasons, the full match report
and every screener answer, and wait for approval. When the user corrects voice or phrasing, apply
the fix AND append the lesson to `resume-style.md` under "## Learned corrections".
Otherwise: spot-check — show only the match-report headline, then go to the browser.
Either way, state the posting age in the same breath as the match assessment — one clause,
`posted <YYYY-MM-DD>, <N> days ago` (or `posting date unknown`), alongside the `track employer` count line.

### 9. Fill the form in Chrome
Invoke claude-in-chrome skill if not already active. Open the job link in a new tab.

**Read `form-pack.md` from the application folder. That is your ONLY input.** It already holds
every value, resolved. Do not open `content-pool.tex`, `qa-bank.md`, `resume-style.md`, or the
`.tex` — if something is missing, that is a gap in the pack, not a reason to read the pool.

**Load exactly one playbook:** `ats\<platform>.md` matching the URL, else `ats\_unknown.md`.

#### 9.1 If `form-pack.md` carries a fill plan (Ashby / Greenhouse)
The prep phase already mapped every field key to a value against the platform's own schema.
1. Open the page.
2. **One `browser_batch`** executing the plan — `form_input(ref, value)` per field, refs
   resolved from one `read_page(filter:"interactive")`.
3. **One JS read-back** verifying every field.
4. `file_upload` the résumé PDF (needs a `read_page` ref).
No exploratory read of the form. Expect ~5–8k tokens instead of 40–60k.

#### 9.2 Otherwise — DOM path (validated 2026-07-30 Netwrix/Rippling)
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
6. **Page check before every Next / Save / Continue (standing rule).** Before any click that
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

#### 9.4 Auto-submit and "already submitted" states (revised 2026-09-08)
Oracle CX is the one ATS that has actually submitted an application on its own (TI/edbz,
session-expiry flow — `ats\oracle-cx.md`). Treat Oracle CX and any **unfamiliar** ATS as
unverified after every click: re-read page state via `javascript_tool` (confirmation text, URL
change, fields disappearing) and STOP if a click advanced further than a normal Next should.
**Greenhouse does not need per-click verification (standing rule).** One genuine embed
auto-submit exists on record (Twitch 2026-08-01, the Greenhouse playbook); the
later ones logged as auto-submits (Skild AI, Nuro, Watershed) were the user submitting finished forms
themselves during multi-link runs — see below. Fill Greenhouse like Ashby; if a confirmation page
appears, apply the rule below instead of stopping the run.

**Multi-link runs: a form found in a submitted state was submitted by the user.** When several
applications are open in one session they submit the ones that are complete while the fill
continues elsewhere. If a tab you return to shows a confirmation page, do not report an
auto-submit and do not stop the run: ask one line (`<Company> shows submitted — you clicked
it?`), and on yes log the row as `applied`. Report an auto-submit only when the state changed
during **your own** click on a form that had not been handed to them.

**9a. Optional sections are not optional (added 2026-08-21).** If the form offers Education, Work Experience, Certifications, Skills, Projects, Languages, or Websites — fill them **completely**, even when the section or its fields are unmarked/optional, and fill every sub-field inside each entry (start and end month/year, city/state/country, degree, major, GPA, employer, title, currently-work-here flag, description text). A half-filled section reads worse to a recruiter than the PDF alone, and some ATS parsers score these structured fields rather than the attachment. Use "Add another" until every entry is in.
- **Which entries:** exactly the Experience and Project entries that survived step 3a onto the tailored PDF, in the same order (most recent end date first — rule 9b) — the form and the résumé must tell one story. Education is always both degrees; certifications always <certification>.
- **Job description / responsibilities free text:** paste the bullets **already prepared in `form-pack.md`** for that entry — the prep phase copied them from the compiled PDF and stripped the LaTeX. Do not re-derive them from the `.tex`.
- **Dates:** every education and employment date is already resolved in `form-pack.md`. The current role gets the "I currently work here" flag, never a fabricated end date.
- **Reason for leaving, languages, references, certification details, GPA and the standard yes/no defaults** are all in `form-pack.md` (sourced from `form-data.md`). Never improvise per form.
- **Do not fabricate to fill a field.** If a value is genuinely unknown (date of birth, a GPA not on file, a supervisor's phone), leave it blank or "N/A" — hard rule 1 still governs. This step widens *coverage*, never invention.
- **Carve-out:** an optional *cover letter* upload stays on-request only (§7a). Optional demographic questions follow hard rule 4.
- **Widget caution:** the loaded `ats\<platform>.md` playbook lists that platform's traps — e.g. Workday's date spinbuttons and Field-of-Study lookups reject JS-set values and need real clicks plus Enter. Read the playbook *before* filling these sections, not after they fail.

**9b. Work experience and education are entered by hand, every time (rewritten 2026-09-08 —
replaces the conditional "verify parsed autofill" rule).**
Assume the form has **no usable autofill**. A resume parse, a returning-candidate profile, or
"Use my last application" may pre-populate these sections; that data is treated as absent, not
as a head start — it has shipped wrong on Workday (AT&T, Baker Hughes, HPE, a Workday employer, Home
Depot), Taleo, Talemetry and SuccessFactors.
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
   drops it on Save (Aderant 2026-09-03). So: fill → Save / Next → when the page re-renders,
   re-open or re-read **every** entry and compare its full description against the pack bullet
   for bullet, plus title, employer and dates. Any mismatch → fix → Save → re-read again. Never
   accept a truncated preview as verification (that is exactly how a Workday employer shipped short).
4. **Handoff gate.** The step-9 handoff must carry
   `Work experience: <n> of <n> entered, order = PDF, descriptions verified after save` and the
   matching Education line. If that line cannot be written truthfully the fill is not done —
   go back; do not hand off.
- Do this *after* the résumé upload, never before — on iCIMS and SuccessFactors the upload wipes
  prior work (the iCIMS playbook).
- Description fields that reject JS-set text (Workday, SuccessFactors) are typed with real
  keystrokes (`computer` click + type). The loaded playbook says which widgets need that.
- Ashby and Greenhouse rarely offer these sections; when they do, the same rule applies.

Upload the compiled PDF with `file_upload` (needs the file input's ref from `read_page`). Fill screener questions from the approved `screener-answers.md`.
**Locked fields: fill directly, no confirmation pause (hard rule 4).**
**Stop at the END of the form, not at the first uncomfortable page (restated 2026-09-05).**
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

### 10. Update tracker — through the script only
```
python bin/jobkit.py track add --company "<C>" --role "<R>" --link "<url as given>" \
  --folder "<application folder>" --status filled --keywords "<comma list>" \
  --framing "<short phrase>" --posted <YYYY-MM-DD|unknown> --source <Handshake|Jobright|LinkedIn|Indeed|job-matcher|direct> \
  --notes "<anything worth remembering: overrides, pay-band decision, what was left blank>"
```
Status at handoff is `filled` (or `skipped` / `duplicate` / `blocked` / `held` / `prepped` for the
other terminal states — one word, the reason goes in `--notes`). `--source` is the board hard
rule 7 identified. Never write a row by hand. When the user confirms they submitted:
`python bin/jobkit.py track set <folder> --status applied`. Any later outcome, same command with
`--status rejected|oa|interview|offer|withdrawn --notes "..."`.


---
## Sweep flow: `/apply-job sweep [N]`

A separate personal project (`job-matcher`, a job aggregator with its own LLM-based
matching) runs unattended every 3 hours across 3 resume tracks (Security, Software, AI
Engineer) and drops its pre-scored candidates into `job-matcher-feed\<track>\<date>\<job_id>.json`
via `bin\jobkit.py sweep-list` / `sweep-done`. This mode is a thin wrapper — job-matcher only
*finds and scores* candidates; every candidate still goes through the **exact same** tailoring,
factual-audit, and fill pipeline as a pasted link. Nothing about hard rules 1–7 changes.

1. `python bin/jobkit.py sweep-prune` first — moves every candidate older than 3 days by the
   feed's own date (`posted_at`, else first-seen, else the feed folder date) into `processed/`
   so stale evergreen listings never occupy the top slots. Then
   `python bin/jobkit.py sweep-list --limit N` — one line per pending candidate, newest first,
   score as tie-break: `<job_id> | <track> | <company> | <title> | score=<0-1> | feed_age=<N>d | <url>`.
   `NONE` means nothing is queued — say so and stop.
2. Take those `N` (default 5) URLs and feed them into the **main flow above, unchanged** —
   same posting-date gate, same duplicate check, same auto-skip pre-filter, same parallel prep,
   same serial fill, same tracker row. job-matcher's score is extra context for the prep
   subagent (pass it along, it's a useful signal), never a substitute for the hard filter or the
   factual audit — job-matcher's matcher scores structurally, it does not read the posting.
3. After each link reaches a terminal state in the main flow (skipped, duplicate, stale, or
   filled), run `python bin/jobkit.py sweep-done <job_id>` so it isn't picked up again next
   sweep. Do this **regardless of outcome** — a skip/duplicate/stale verdict is still a terminal
   state for that candidate, not a reason to leave it queued.
4. Report same as the main flow's step-9 handoff, plus a one-line sweep summary: how many
   processed, how many filled/skipped/duplicate/stale, how many remain queued.

---
## Scan flow: `/apply-job scan`

Three sites (Handshake, Jobright, LinkedIn) offer their own "recommended for you" / "top
applicant" pages that job-matcher's connectors can't reach — they need the user's real logged-in
session, not a public API. This mode uses claude-in-chrome with their already-logged-in browser
to read those pages and queue anything that's a plausible fit, same downstream queue as sweep.

**URLs (fixed for now — update here if the user gives new ones):**
- Handshake: `<your saved Handshake job-search URL>`
- Jobright: `https://jobright.ai/jobs/recommend`
- LinkedIn, one search per track (the `f_TPR=r86400` filter = past 24 hours — keep it, it's what
  makes this worth re-running periodically instead of once):
  - `https://www.linkedin.com/jobs/search-results/?keywords=Security%20Engineer&geoId=<your geoId>&f_TPR=r86400`
  - `https://www.linkedin.com/jobs/search-results/?keywords=Software%20Engineer%20New%20Grad&geoId=<your geoId>&f_TPR=r86400`
  - `https://www.linkedin.com/jobs/search-results/?keywords=AI%20Engineer%20Entry%20Level&geoId=<your geoId>&f_TPR=r86400`

**Procedure, once per site:**
1. Invoke claude-in-chrome if not already active. Navigate to the site's URL in a new tab.
2. `get_page_text` for a quick read; `read_page(filter:"interactive")` to get each job card's
   link/ref (Handshake job cards carry a real `href`; Jobright and LinkedIn are click-through —
   click each candidate card and read the URL it navigates to, e.g. LinkedIn's `currentJobId=`
   query param or Jobright's `/jobs/info/<id>` path).
3. **Filter before queuing — don't queue everything on the page:**
   - Keep only postings that plausibly fit one of the 3 tracks (Security/Software/AI Engineer) —
     use the same judgment as `content-pool.tex`'s title/skill matching, not a strict keyword rule.
   - Drop anything already marked "Applied" on the site itself.
   - Drop obvious seniority mismatches (Principal/Staff/Director-level).
   - **Apply the user's standing defense/gov auto-skip** even at this stage, not just at apply time —
     drop Anduril, L3Harris, RTX/Raytheon, Lockheed Martin, Northrop Grumman, General Dynamics,
     Cubic, Huntington Ingalls, Textron defense, Booz Allen Hamilton, Cherokee Federal, any
     `DoD`/`GovCloud`/"Public Sector"/"Locals ONLY"-flagged posting, and gov-cleared roles
     generally — for an applicant who is not a US Person, ITAR-restricted work is a legal bar,
     not a judgment call to make per-posting later. Edit this list to match your own situation.
4. For each kept job, pipe a JSON array into `jobkit.py scan-add` (one call per site is fine):
   `{"title", "company", "url", "location", "track", "connector": "<site>_live", "score" (0-1,
   the site's own match % if it shows one, else a reasonable estimate), "note" (why/site context)}`.
   `scan-add` is idempotent by URL hash — safe to re-run without duplicating.
5. Report: how many found per site, how many queued, how many dropped and why (auto-skip vs.
   seniority vs. off-track) — same terse style as sweep's summary.

**This mode never applies to anything itself** — it only queues. Processing still happens via
`/apply-job sweep`, with the same hard filter, tailoring, and factual audit as any other link.

---

For the inbox sweep, insights, and cross-platform form troubleshooting, load the matching file
in `references\`. For a specific ATS, load `ats\<platform>.md` — only that one.
