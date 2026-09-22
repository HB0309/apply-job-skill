---
name: apply-job
description: Auto job-application pipeline. Use when the user pastes a job link to apply for (tailors resume, fills the form in Chrome, pauses before submit), says "apply-job inbox" (morning Gmail check that updates the tracker), "apply-job insights" (analyzes which applications convert), "apply-job sweep" (harvest job alerts from Gmail, then process pre-scored candidates from the <Project B> project), or "apply-job scan" (browse Handshake/Jobright/LinkedIn recommended pages via the user's live session and queue matches), or "apply-job fixes" (review the failure log and update the skill). Triggers on job posting URLs, "apply to this job", "check my application inbox", "application insights", "sweep", "scan", "process <Project B> candidates".
---

# /apply-job — Auto Job-Application Pipeline

Paste a job link → tailored one-page resume → form filled in Chrome → user clicks Submit.

## Fixed paths
- Workspace: `<WORKSPACE>\`
- **Read layer: `bin\jobkit.py`** — ALWAYS use this instead of reading the big files.
  Orchestrator: `posted <url>` · `dup <url>` · `meta <url> --write` · `triage <folder>` ·
  `track add|set|active|employer|audit` · `count` · `insights` ·
  `sweep-list` · `sweep-done <job_id>` · `sweep-prune` · `scan-add` · `fail add|list|close` (hard rule 8).
  Prep agent: `similar` · `base use <track> <folder>` · `pool tex|notes|entry` · `qa list|get` ·
  `pagefit <pdf>` · `atsfix <pdf>` (self-checking) · `audit <tex>` · `formpack <folder>` · `schema <url>` ·
  `skills <folder> [--pdf <resume.pdf>]` (posting vs. the skills inventory: TRUE / BANNED / GAP, and the keyword-coverage gate line).
  the user only: `base set <track> <folder>` · `base list` (track base résumés in `bases\`).
  Reading `tracker.md`, `qa-bank.md`, or `content-pool.tex` in full is a bug, not a fallback.
- <Project B> feed (sweep mode only): `job-matcher-feed\<track>\<date>\<job_id>.json`, written by a
  separate project's scheduler — query via `jobkit sweep-list`/`sweep-done`, never read directly.
- Content pool: `master\content-pool.tex` + `master\resume.cls` — **READ-ONLY, never edit.**
  Access it via `jobkit pool tex`, never directly.
- Profile: `master\profile.md` — read-only for you.
- **Metrics ledger: `master\metrics-ledger.md`** — one row per number on any résumé (value, how
  measured, date, n, status, how to say it). No row, no number. Editable only to add a `measured`
  or `counted` row with its evidence; `stated` rows are the user's own figures.
- **Skills inventory: `master\skills-inventory.md`** — every skill the user can truthfully claim, with
  evidence, level, the only allowed page wording and a never-say list; banned rows record what
  must never be claimed. Read it through `jobkit skills`, never whole. Editable only to add or
  change a row the user confirmed or that is verified in a repo / evidence folder.
- **Transcripts (read-only, attach when a form asks):**
  `master\<University A>_Transcript_<Full Name>.pdf` (graduate) ·
  `master\<University B>_Official Marksheets_<Full Name>.pdf` (**undergraduate**, ~3.5 MB — over
  the 1 MB cap some ATSs impose). Which one maps to which request, and the size caveat,
  are in `form-data.md` → Transcripts.
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
  `ashby` `greenhouse` `workday` `oracle-cx` `smartrecruiters` `icims` `taleo` `successfactors` `pageup`
  `talemetry` `phenom`, else `_unknown`. **Phenom** hides behind company domains too
  (`careers.rocket.com`) — the tell is an apply route of `/us/en/apply?jobSeqNo=` or
  `/us/en/hvhapply?jobSeqNo=`, or assets from `phenompeople.com`.
  Workday also hides behind company domains (careers.homedepot.com, corporate.target.com,
  jobs.boeing.com) — if the Apply click lands on `*.myworkdayjobs.com`, or the form-pack says
  Workday, load `workday.md`.
- **References (load on demand, never all):**
  `references\tailoring.md` (steps 1–8, prep subagent) · `references\inbox.md` ·
  `references\insights.md` · `references\ats-quirks.md` (when a form misbehaves) · `references\setup.md` (first run) ·
  `references\fill.md` (step 9, fill phase) · `references\prep-brief.md` (the subagent
  prompt template) · `references\scan-sources.md` (scan URLs) ·
  `references\mail-harvest.md` (job alerts in Gmail → sweep queue) · `references\sweep.md` ·
  `references\scan.md` · `references\hybrid-swaps.md` (prep, HYBRID postings only). Provenance and dated history live
  in `references\changelog.md` — never loaded, never published. `references\fixes.md` is loaded
  only by `/apply-job fixes`.
- Interview prep: `interview-prep\<company-slug>\` — one folder per company.
- Gmail reader: `bin\gmail\gmail_search.py` (inbox mode) ·
  `bin\gmail\mailjobs.py` (sweep mode: `harvest` · `enrich <url>…` · `seen <url>` · `sources`)

## Modes
- `/apply-job <link> [<link> ...]` — apply to one or more jobs (main flow below)
- `/apply-job <link> --review` — force the full review checkpoint, tailoring stays inline
- `/apply-job <link> --fresh` — skip the variant cache and the track base, tailor from the raw pool
- `/apply-job <link> --force` — the user overrides a Skip (from `triage` or from prep). Skip the
  triage step, put `--force` on the brief's `Triage:` line, and do not re-argue the skip.
- `/apply-job inbox` — morning Gmail sweep (`references\inbox.md`)
- `/apply-job insights` — conversion analysis (`references\insights.md`)
- `/apply-job sweep [N]` — harvest job alerts from Gmail, then process the queue (below).
  `N` optional, default 5. `--no-mail` skips the harvest; `--mail-only` harvests and reports only.
- `/apply-job fixes` — review the failure log and turn its open entries into skill edits (`references/fixes.md`)
- `/apply-job setup` — first-run interview that builds profile.md, content-pool.tex, form-data.md and qa-bank.md (`references\setup.md`)
- `/apply-job scan` — browse Handshake/Jobright/LinkedIn via the user's live Chrome session and queue matches (below). Meant to be run on a loop (`/loop 8h /apply-job scan`), not manually every time.

## Hard rules (apply to every mode)
1. **Never invent facts.** Every claim in any output must trace to a specific line in `content-pool.tex` or `profile.md`. No new skills, metrics, employers, titles, or dates. Reword, reorder, select — never fabricate. Two companion files narrow this further, neither widens it: for SKILLS and keyword spelling a non-banned row of `master\skills-inventory.md` is also a valid source (read via `jobkit skills`), and every NUMBER on the page must have a row in `master\metrics-ledger.md` saying how it was measured.
2. **Never click Submit.** The user always clicks the final submit button.
3. **Never edit master files** (`master\content-pool.tex`, `master\profile.md`).
4. **Locked fields — FILL them, don't ask.** Work authorization, visa sponsorship, salary, notice period, and voluntary EEO self-ID all have stored answers. Fill them straight from those answers like any other field, in every mode, and verify each one with the JS read-back of step 9.3 — the read-back is the real safety net, not a prompt. Do NOT stop mid-form to confirm them. Recap every locked value actually entered in the step-9 handoff message, where the user reviews before clicking Submit.

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
7. **Referral source = the job board the link came from.** Every pasted link
   carries its origin — check the URL's source/referral params (`gh_src`, `src`, `source`,
   `utm_source`, `lever-source`, `rcid`, …) and the surrounding context to identify the board:
   **Handshake, Jobright, LinkedIn, Indeed, Wellfound, or any other**. When the form asks "How did
   you hear about us?" / "Source" / "Referral source", pick **that board** from the options. If the
   identified board is not offered, fall back to the **company careers site / company website**
   option (then "Other" with the board's name typed in, if the widget allows free text). Always
   apply through the exact link given — never re-find the posting on a different board. Carry the
   identified source into `form-pack.md` during prep so the fill phase does not re-derive it.
8. **Log every failure of the SKILL, the moment it happens — then carry on.** One command, in
   every mode and every phase (prep agents too):
   `python bin/jobkit.py fail add --phase <gate|prep|fill|sweep|scan|inbox|script|instructions> --where "<platform, jobkit command, or skill file>" --happened "<what went wrong, concretely>" --expected "<what should have happened>" --workaround "<what you did instead>" --fix "<which file should change, and how>" --folder "<application folder>"`
   It appends to `<WORKSPACE>/failures.md`; a repeat of the same open failure
   is counted, not duplicated. **Never read that file during a run** and never stop a run to
   fix the skill — log, work around, continue. Mention the count in the final report
   (`2 skill failures logged: F-0012, F-0013`).
   **Log when:** a `jobkit`/`mailjobs` command errors, tracebacks or prints something wrong
   (`FORMPACK_FAILED`, a false `audit` FAIL/WARN, a wrong `triage` SKIP, `NO_META` on a host
   that has an API, a `meta` field that was wrong) · a widget could not be filled the way the
   playbook or `fill.md` says · a value did not persist after save · the playbook was wrong,
   missing a trap, or there was no playbook for the platform · an unexpected auto-submit or
   session expiry · a prep agent failed or returned an unusable folder · an instruction in the
   skill was ambiguous, contradictory, or pointed at something that does not exist · a form
   asked something with no stored answer (a gap in `form-data.md`) · the user corrected you on
   something the skill should have told you.
   **Do not log:** ordinary outcomes — skips, duplicates, stale postings, caps, closed
   postings, login walls, OTP dialogs, a pause trigger working as designed.

---
## Main flow: `/apply-job <link> [<link> ...]`

**Two phases. Prep is delegated and parallel; filling is serial and stays in this thread.**
Run the gates below **in this exact order, for every link, before launching any prep** — each
one is a script call costing 30–200 tokens, and each one can save a whole Opus prep run.

```
G1  jobkit posted <url>                      STALE -> stop and ask (all modes)   UNKNOWN -> continue
G2  jobkit dup <url>                         MATCH -> report, next link
G3  jobkit meta <url> --write --posted "…" --source <board>
        -> company | role | location | platform | pay | apply_url | folder   (job-posting.md written)
        CLOSED?  -> open the link once to confirm; if gone, log `skipped --notes "posting closed"`
        NO_META  -> no API for this host; skip G4–G6, prep fetches the posting and runs them itself
G4  jobkit dup <url> --company "<C>" --role "<R>"      catches the same job under another URL
G5  jobkit track employer "<C>"              AT CAP -> log `held --notes "cap"`, no prep, tell the user
G6  jobkit triage <folder>                   SKIP -> log `skipped`, no prep;  Ua university employerRE -> read the lines, decide
PREP   one `apply-job-prep` subagent per surviving link, all launched in ONE message (parallel)
FILL   serial, here, one tab per posting -> step 9 (references/fill.md).
       PIPELINED: start filling a posting the moment ITS prep returns — never wait for the batch.
step 10  jobkit track add … (once per link, whatever the outcome)
```

### G1 Posting-date check
Runs FIRST: before the duplicate check, before prep, before the browser.

`python bin/jobkit.py posted "<url>"` → one line, one of three verdicts:
1. `FRESH date=<YYYY-MM-DD> age=<N>d confidence=<level>` — 0–3 days old. Continue to
   G2 silently. **Carry the date and age forward** — every later step needs them.
2. `STALE date=<YYYY-MM-DD> age=<N>d confidence=<level>` — older than 3 days. STOP for
   that link. Report and wait:
   `<Company> <Role> — posted <YYYY-MM-DD> (<N> days ago, confidence <level>). Older than
   3 days. Apply anyway?`
   Do not run the duplicate check, do not launch prep, do not open the browser until they
   answer. On yes, resume the normal flow from G2 and carry the date forward.
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

### G2 Duplicate check
`python bin/jobkit.py dup "<url>" --company "<C>" --role "<R>"` (company/role optional; they
catch the same job posted under two URLs). On `MATCH` or `FUZZY MATCH`: STOP for that link,
reply `Duplicate — applied to <company> <role> on <date>, status: <status>. Folder: <path>`,
and move to the next link. On `NONE`, continue. G2 sees only the URL. G4 repeats it with the
company and role `meta` returned, which is what catches the same job reached through Jobright,
LinkedIn and the employer's own ATS. On `NO_META` the prep agent runs G4 itself.

### G3 `meta` — posting facts without a model
`python bin/jobkit.py meta "<url>" --write --posted "<date (N days ago) | unknown>" --source <board>`
reads the ATS's own public job API (Greenhouse incl. `?gh_jid=` on employer domains, Ashby, Lever,
SmartRecruiters, Workday, Eightfold), creates
the application folder, writes `job-posting.md` verbatim, and prints one line with everything
the later gates and the prep brief need. Never fetch the posting yourself to fill the brief —
if `meta` says `NO_META`, the brief simply says so and prep does the fetching.

### G5 Employer count and caps — before prep
`python bin/jobkit.py track employer "<Company>"` prints how many applications went to that
employer in the last 30 days and, for employers with a published cap (table in
`bin\jobtrack.py`: OpenAI 5/6mo, TikTok 2/6mo, Canonical 4/6mo, Google 3/30d, Retell 2/60d), the
running count. State the line next to the match assessment (`3rd application to Scale AI in 30
days` / `2 of 3 Google used`). **A count is information, not a stop** — the user applies to the same
employer repeatedly on purpose, if that is your policy. Only `AT CAP` stops: no prep, log `track add --status held
--notes "cap"`, tell the user. On `NO_META` the company is unknown until prep returns — run G5 then,
before filling.

### G6 `triage` — the auto-skip pre-filter, as a script
`python bin/jobkit.py triage "<folder>"` prints one of:
- `SKIP <reason>` — strict matches only. Log `skipped` with the reason, list it with its link in
  the final report so the user can re-run it with `--force`. No prep. **The eligibility rules, stated
  here once** (tailoring.md, scan.md, mail-harvest.md and the agent definition point here):
  - a defense / gov / space-launch employer on the auto-skip list (`form-data.md` → Auto-skip
    employers), a required clearance, required US citizenship, an ITAR / US-person requirement;
  - the employer refusing visa sponsorship **in its own voice** ("we are unable to sponsor");
    never a prep agent's note line, a guess ("startups often do not sponsor") or a screener question;
  - the **first stated experience requirement being 3+ years** (the profile states how many years the user's degree covers, 2 here; "2-6 years" reads as 2; a softened or Master's-path line is only a `YOE` flag);
  - a Principal / Staff / Director title, or a Senior / Sr / Lead title with no entry tier beside
    it and no 2-years-or-less bar in the body;
  - **both** the whole pay band under <salary floor> **and** a government employer (either alone is
    never a skip). Hourly pay is annualised at 2,080 hours; government-CONTRACTOR wording
    (national security, federal agencies, DoD / DHS customers) counts as government, and on its
    own is only a `GOV-CONTRACTOR` flag.
- `Ua university employerRE` + flagged lines — read them (they are the only posting text you ever read). Skip only
  on a genuine eligibility bar from the list above, a graduation cohort they are outside of (a
  `COHORT` flag: they do apply to some "New Grad 2027" programs, so judge it), or a non-US
  location. `RESIDENCY` is a skip only when the posting rules out relocating. `YOE`: skip when the
  real bar is 3+ years, keep when 2 or less. Boilerplate ("must be authorized to work in the US")
  or a Senior title on an otherwise entry-level posting is **not** a skip: pass the lines to prep
  on the brief's `Triage:` line and let it judge against the pool.
- `PASS` — launch prep. `note:` lines (pay band outside <salary range>) go on the brief too.

### PREP — delegate steps 1–8
Launch one subagent per surviving link, **all in one message so they run in parallel**, with
**`subagent_type: "apply-job-prep"`** — never `general-purpose`. That agent is defined in
`<agents folder>\apply-job-prep.md`, which pins the model (**Opus**) and a tool set
with no `file_upload` / `form_input` / `Agent`, so prep cannot fill a form or spawn sub-agents. Do not pass a
`model` override in the launch; the definition is the single source of truth. **The prompt is
only the ~10-line variable block in `references\prep-brief.md`** (you know its shape: link,
company, role, location, platform, apply URL, folder, whether `meta` wrote the posting, posted
date, source, pay, triage line, extras). The hard rules, canonical answers and return format
live in the agent definition — never paste them into the prompt. If the `apply-job-prep` agent
type is missing from the session, stop and tell the user.

A subagent never clicks Submit and never drives the browser except to read a posting in its own
tab. Links prep verdicts **Skip** never reach the browser — report them, log the tracker row,
and drop them from the fill queue.

**A prep that fails.** If a subagent errors out, returns nothing usable, or returns without a
compiled PDF and a `form-pack.md` in the folder: relaunch it **once** with the same brief. If it
fails again, log `track add --status blocked --notes "prep failed: <what>"`, tell the user in the
final report, and carry on with the other links. Never fill a form from a half-written folder.

### Spot-check before fill — read the verdict lines, not the résumé
The prep return carries `pagefit`, `atsfix` and `audit` verdicts. Proceed to fill only when
`pagefit` is `FULL`, `atsfix` is `verdict=OK` and `audit` is not `FAIL`. An `audit WARN` the
agent accepted comes with a one-line justification each — read them; one that names a technology
or a number with no justification goes back to the agent, do not fill. Then read the match
report's Genuine Gaps section. **Do not open the PDF, the `.tex` or the pool** — the script
checks every number and term against the pool more reliably than a skim, at a fiftieth of the cost.

### 8. Checkpoint (trust-aware)
`--review` only: FULL REVIEW / teaching mode — show the tailored résumé changes with reasons, the full match report
and every screener answer, and wait for approval. When the user corrects voice or phrasing, apply
the fix AND append the lesson to `resume-style.md` under "## Learned corrections".
Otherwise: spot-check — show only the match-report headline, then go to the browser.
Either way, state the posting age in the same breath as the match assessment — one clause,
`posted <YYYY-MM-DD>, <N> days ago` (or `posting date unknown`), alongside the `track employer` count line.

### 9. Fill the form in Chrome
Read `references/fill.md` now, once per session — it holds all the mechanics and the handoff
block. This section is only the contract; nothing here is repeated there.
- **Input is `form-pack.md` only.** It already contains the platform playbook verbatim, so do
  not load `ats/<platform>.md` separately — unless the form lands on a different platform than
  the pack names (an Apply click that redirects to Workday, Phenom behind a company domain). Then
  load that one playbook before touching a field. Never open the pool, `qa-bank.md`, the style
  guide or the `.tex`: a missing value is a gap in the pack, reported at handoff.
- **You fill every page and click every Next / Continue / Save yourself**, on every platform. The ONLY stop is the final
  review/Submit screen. **Never click Submit.**
- What keeps that safe, all mandatory: never batch across a click; one full read-back of the
  page before each advancing click; after each click, check the URL and the page heading before
  doing anything else. If the page is a confirmation / "thank you" / "application received"
  screen that you did not expect, STOP and report it as an auto-submit.
- Two platform traps that stay, because on these the advancing control IS the submit:
  **Phenom** — if the URL contains `/hvhapply`, the resume upload submits the application: do
  not upload, hand the tab to the user. **Oracle CX** — fill everything except the final field of
  the last section, then hand off; the form can submit with no Submit button once complete.
- **Idle-timeout platforms (Oracle CX, SmartRecruiters): fill in one uninterrupted block.** Do
  not start one while waiting on the user for something else, and do not pause mid-form.
- Account / login walls and OTP dialogs: stop and hand the user the browser. Never create accounts
  or enter passwords or OTPs, even if offered.
- One tab per posting; filled tabs stay open until the user confirms they submitted (details in fill.md).

When everything is filled, STOP before the submit button and give the handoff block from
`fill.md` (posted date, locked fields entered, work-experience and education counts, optional
sections, unanswered).

### 10. Update tracker — through the script only
```
python bin/jobkit.py track add --company "<C>" --role "<R>" --link "<url as given>" \
  --folder "<application folder>" --status filled --keywords "<comma list>" \
  --framing "<short phrase>" --posted <YYYY-MM-DD|unknown> --source <Handshake|Jobright|LinkedIn|Indeed|<Project B>|direct> \
  --notes "<anything worth remembering: overrides, pay-band decision, what was left blank>"
```
Status at handoff is `filled` (or `skipped` / `duplicate` / `blocked` / `held` / `prepped` for the
other terminal states — one word, the reason goes in `--notes`). `--source` is the board hard
rule 7 identified. Never write a row by hand. When the user confirms they submitted:
`python bin/jobkit.py track set <folder> --status applied`. Any later outcome, same command with
`--status rejected|oa|interview|offer|withdrawn --notes "..."`.


---
## Sweep and scan modes
`/apply-job sweep [N]` → read `references\sweep.md` first. `/apply-job scan` → read
`references\scan.md` first. Both only QUEUE or FEED links; every link still goes through the
main flow above, unchanged, with the same hard rules, gates, tailoring and factual audit.

---
## Setup flow: `/apply-job setup`

First-run onboarding. Builds the four data files the pipeline depends on from whatever the
user already has (a PDF or Word résumé, a LinkedIn export, or just a conversation). Full
procedure in `references\setup.md`. It is an **interview**, not a conversion: every metric,
title, date and tool goes in only after the user confirms where it comes from. A number the
user cannot source is left out, and recorded under "NOT ON THE RESUME, DELIBERATELY" so it is
never reintroduced.

Outputs, in order: `master\profile.md` → `master\content-pool.tex` (compiled once as a sanity
check, one page is NOT required) → `form-data.md` → `qa-bank.md` (at least one story per
entry, tagged by angle). Ends with `jobkit pool tex`, `jobkit pool notes`, `jobkit qa list` and
`jobkit track audit` all running clean, and tells the user to run their first three real
applications with `--review`.

---

For the inbox sweep, insights, and cross-platform form troubleshooting, load the matching file
in `references\`. For a specific ATS, load `ats\<platform>.md` — only that one.
