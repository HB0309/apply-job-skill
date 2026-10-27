---
name: apply-job
description: Auto job-application pipeline. Use when the user pastes a job link to apply for (tailors resume, fills the form in Chrome, pauses before submit), says "apply-job inbox" (morning Gmail check that updates the tracker), "apply-job insights" (analyzes which applications convert), "apply-job sweep" (harvest job alerts from Gmail, then process pre-scored candidates from the <Project B> project), or "apply-job scan" (browse Handshake/Jobright/LinkedIn recommended pages via the user's live session and queue matches), or "apply-job fixes" (review the failure log and update the skill). Triggers on job posting URLs, "apply to this job", "check my application inbox", "application insights", "sweep", "scan", "process <Project B> candidates".
---

# /apply-job — Auto Job-Application Pipeline

Paste a job link → tailored one-page resume → form filled in Chrome → user clicks Submit.

## Fixed paths
- Workspace: `<WORKSPACE>\`
- **Read layer: `bin\jobkit.py`** — use it instead of reading the big files.
  Orchestrator: `gate <url> --source <board>` (G1–G6 in one call) · `posted <url>` · `dup <url>` · `meta <url> --write` · `triage <folder>` ·
  `track add|set|active|employer|audit` · `count` · `insights` ·
  `sweep-list` · `sweep-done <job_id>` · `sweep-prune` · `scan-add` · `fail add|list|close` (hard rule 8).
  Prep agent: `similar` · `base use <track> <folder>` · `pool tex|notes|entry` · `qa list|get` ·
  `pagefit <pdf>` · `atsfix <pdf>` (self-checking) · `audit <tex>` · `formpack <folder>` · `schema <url>` · `salary "<band>"` ·
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
  reason-for-leaving lines, languages, standard yes/no defaults. Read by `jobkit formpack` at prep;
  the fill phase reads only `form-pack.md`.
- Tracker: `tracker.md` — **never edit it directly.** Rows are written only by
  `jobkit track add` (step 10) and changed only by `jobkit track set`; the script escapes pipes,
  enforces the closed status vocabulary (`prepped filled applied viewed oa interview offer
  rejected withdrawn skipped duplicate blocked held review`) and dates the update. Narrative goes
  in `--notes`, never in the status.
- Compiler: `bin\tectonic.exe`
- Style guide: `resume-style.md` (this folder) — prep phase only.
- **ATS playbooks: `ats\<platform>.md`** — load ONLY the one matching the form's URL.
  `ashby` `greenhouse` `workday` `oracle-cx` `smartrecruiters` `icims` `taleo` `successfactors` `pageup`
  `talemetry` `phenom` `lever` `amazon-jobs`, else `_unknown`. **Phenom** hides behind company domains too
  (`careers.rocket.com`) — the tell is an apply route of `/us/en/apply?jobSeqNo=` or
  `/us/en/hvhapply?jobSeqNo=`, or assets from `phenompeople.com`.
  Workday also hides behind company domains (careers.homedepot.com, corporate.target.com,
  jobs.boeing.com) — if the Apply click lands on `*.myworkdayjobs.com`, or the form-pack says
  Workday, load `workday.md`.
- **References (load on demand, never all):**
  `references\tailoring.md` (steps 1–8, prep subagent) · `references\inbox.md` ·
  `references\insights.md` · `references\ats-quirks.md` (when a form misbehaves) · `references\setup.md` (first run) ·
  `references\fill.md` + `readback.min.js` (step 9, read by the fill subagent, never here) · `references\prep-brief.md` (the subagent
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
- `/apply-job <link> --review` — force the full review checkpoint (step 8) after prep returns
- `/apply-job <link> --fresh` — skip the variant cache and the track base, tailor from the raw pool
- `/apply-job <link> --force` — the user overrides a Skip (from `triage`, from **G7**, or from prep).
  Rerun `jobkit gate … --force` (triage still runs and only reports) and skip G7, put `--force` on the brief's `Triage:` line — and on its `Visa:` line
  when the override was a G7 skip — and do not re-argue the skip.
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
4. **Locked fields — FILL them, don't ask.** Work authorization, visa sponsorship, salary, notice period, and voluntary EEO self-ID all have stored answers. `jobkit formpack` writes them into `form-pack.md` and the fill agent enters them without asking; its handoff recaps every locked value it entered, which is where the user reviews them before clicking Submit.

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

   **When a fill stops.** The fill agent's brief decides when it returns `BLOCKED` and what it skips
   and lists under `Unanswered`. For `BLOCKED`, relay the blocker and pass the user's answers back in
   `resume` mode (step 9); `Unanswered` items they fills in the form themselves before they click Submit.
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
   postings, login walls, OTP dialogs, a `BLOCKED` return working as designed.

---
## Main flow: `/apply-job <link> [<link> ...]`

**Two phases, both delegated. Prep runs in parallel; each form is filled by its own fresh fill
subagent, so this thread never carries one form's screenshots or field lists into the next.**
Gate every link **before launching any prep**: one `jobkit gate` call runs G1–G6 in order and
prints one verdict, so each link costs one turn here and a stopped link never costs a prep run.

```
G0  jobkit gate <url> --source <board> [--force] [--stale-ok]   runs G1-G6, one verdict:
    GATE PASS | folder= | company= | role= | platform= | pay= | apply= | posted= | employer=
        -> G7, then prep. Read ONLY the indented lines: `  unsure:` decide, `  note:` carry,
           `  dup: FUZZY DIFFERENT_REQ` ignore, `  dup: FUZZY UNKNOWN_REQ` judge on location/team,
           `  skip(forced):` / `  dup: PRIOR_SKIPPED|PRIOR_HELD` copy to the brief's `Triage:` line.
    GATE STOP G1 STALE        -> ask the user (all modes); on yes rerun with --stale-ok
    GATE STOP G2|G4 DUPLICATE -> report the printed row, next link (MATCH or FUZZY SAME_REQ)
    GATE STOP G3 CLOSED       -> open the link once; if gone, log `skipped --notes "posting closed"`
    GATE STOP G5 AT_CAP       -> log `held --notes "cap"`, no prep, tell the user
    GATE STOP G6 SKIP         -> log `skipped` with the reason; the user overrides with --force
    GATE NO_META              -> no API for this host; prep fetches the posting and runs G4 (dup)
                                 and G6 (triage) itself; run G5 (`track employer`) when prep returns
    The folder is written only once the gate reaches G6. If `gate` itself errors, log the
    failure and run the same gates by hand:
      G1 jobkit posted <url> · G2 jobkit dup <url> · G3 jobkit meta <url> --write --posted "…"
      --source <board> · G4 jobkit dup <url> --company "<C>" --role "<R>" · G5 jobkit track
      employer "<C>" · G6 jobkit triage <folder>
G7  visa eligibility (E-Verify + work visa)       work visa at entry level is sufficient -> APPLY (E-Verify is a
        flag, not a veto). Neither -> log `skipped` with the named reason. Always record the tier.
PREP   one `apply-job-prep` subagent per surviving link, all launched in ONE message (parallel)
FILL   one `apply-job-fill` subagent per form, one tab per posting -> step 9.
       PIPELINED: start filling a posting the moment ITS prep returns — never wait for the batch.
       One form ahead only for Greenhouse / Ashby / Lever; everything else strictly serial.
step 10  jobkit track add … (once per link, whatever the outcome)
```

### G1 Posting-date check
Runs FIRST: before the duplicate check, before prep, before the browser.

`python bin/jobkit.py posted "<url>"` → one line, one of three verdicts:
1. `FRESH date=<YYYY-MM-DD> age=<N>d confidence=<level>` — 0–3 days old. Continue to
   G2 silently. **Carry the date and age forward** — every later step needs them.
2. `STALE date=<YYYY-MM-DD> age=<N>d confidence=<level>` — older than 3 days. STOP for
   that link. Report and wait:
   `<Company> <Role, or the link when the gate stopped before meta> — posted <YYYY-MM-DD> (<N> days ago, confidence <level>). Older than
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
catch the same job posted under two URLs). On `MATCH`: stop for that link, reply
`Duplicate — applied to <company> <role> on <date>, status: <status>. Folder: <path>`, and move
to the next link. A fuzzy hit prints its requisition verdict: `FUZZY SAME_REQ` is a duplicate;
`FUZZY DIFFERENT_REQ` is not (a different req at the same employer); `FUZZY UNKNOWN_REQ` (an
aggregator link with no id) is a duplicate only when location and team also match, and never a
row this run wrote itself. On `NONE`, continue. G2 sees only the URL. G4 repeats it with the
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
  the final report so the user can re-run it with `--force`. No prep. **The eligibility rules that are
  readable from the posting text** (scan.md and mail-harvest.md point here). **Visa/sponsorship eligibility is NOT one of them — it needs an
  employer lookup and lives in G7 below.** A posting's own "we cannot sponsor" wording is still a G6
  skip; whether the employer *files* work visa is G7's question:
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
- `UNSURE` + flagged lines — read them (they are the only posting text you ever read). Skip only
  on a genuine eligibility bar from the list above, a graduation cohort they are outside of (a
  `COHORT` flag: they do apply to some "New Grad 2027" programs, so judge it), or a non-US
  location. `RESIDENCY` is a skip only when the posting rules out relocating. `YOE`: skip when the
  real bar is 3+ years, keep when 2 or less. Boilerplate ("must be authorized to work in the US")
  or a Senior title on an otherwise entry-level posting is **not** a skip: pass the lines to prep
  on the brief's `Triage:` line and let it judge against the pool.
- `PASS` — launch prep. `note:` lines (pay band outside <salary range>) go on the brief too.

### G7 Visa eligibility — E-Verify and work visa filing history, checked separately
Runs after `triage` PASS/UNSURE, before prep. Neither fact is in the posting text — both need an
employer lookup, so this is its own gate. **Both checks always run; only work visa can veto.**

**Check 1 — E-Verify enrollment.** Recorded, never a veto (decision rule below). It matters because the work-authorization
extension is only filable through an E-Verify-enrolled employer, and the user's filing window is
**<filing window start> → <EAD end date>** (EAD expiry). So E-Verify determines whether *that* path stays open at a
given employer, and a `no` triggers a warning, never a skip.
Source: the E-Verify participating-employer search / published employer list.

**Check 2 — work visa filing history at entry level.** Check the employer has filed, and filed for
entry-level titles — big employers that sponsor broadly sometimes do not sponsor new grads.
Sources, in order: **USCIS work visa Employer Data Hub** (primary), `h1bdata.info` with the year filter set
to All years (mirror). A company-level hit is not enough on its own; note the titles.

**Young-startup carve-out (standing rule).** A funded company **under ~3 years old** with no filing
history has usually never *needed* to file — missing data, not a refusal. The research is explicit that
*funding stage, not company size, predicts sponsorship*, and that small-company hesitancy is *"often
ignorance, not policy."* So for a funded startup under ~3 years: **no work visa history → `UNSURE`, not
`t4-neither`.** Apply, and resolve sponsorship by asking the founder, who is already the contact in the
outreach plan's startup lane. Keep the hard skip for established employers that have had years of
opportunity to file and never have.

**Check 3 — company size and stage (outreach sizing only, never eligibility).** While looking the
employer up for checks 1 and 2, capture **estimated headcount** and **funding stage** (`seed` |
`series-a` | `series-b` | `series-c+` | `public` | `private-unknown`). One lookup, three outputs. This
feeds outreach scoring in prep and nothing else — **it can never cause a skip**, and `unknown` is missing
data, never a negative.

**The decision rule (standing rule): visa sponsorship at entry level is sufficient on its own.**
If the employer sponsors, apply — **even with no E-Verify**. E-Verify stays a recorded property, because
it decides whether the work-authorization extension can be filed at that employer, but it is **never a veto**.

**Four tiers. Two apply, two skip:**

| Tier | E-Verify | work visa at entry level | Action | Why |
|---|---|---|---|---|
| `t1-both` | yes | yes | **APPLY** | Both paths open: work-authorization extension filable here *and* the employer sponsors. Strongest — prefer these, and spend referral capital only here. |
| `t2-h1b` | no | yes | **APPLY** | Sponsors, but **work-authorization extension cannot be filed here.** See the gap warning below. |
| `t3-everify` | yes | no | SKIP, labelled | Could carry the work-authorization extension filing (runway to ~2029 + two clean lottery attempts) but no sponsorship record. Recoverable pool — keep the label so `insights`/`fail` can surface it later without re-running lookups. |
| `t4-neither` | no | no | SKIP | No path. |

**⚠️ Warn on every `t2-h1b` application, in the brief and in the step-9 handoff.** A non-E-Verify
employer cannot support the work-authorization extension, so the user's EAD still ends **<EAD end date>** while cap-subject
work visa petitions are not filed until **<next cap filing date>**. Cap-gap grants student status but **no work authorization**
once they are in the 60-day grace period — so even a lottery win implies **no work from <EAD end date> to
<cap start date>**. `t2-h1b` is therefore worth an application but is strictly worse than `t1-both`, and at offer
stage the ask changes: **will they enroll in E-Verify** (free, ~1–2 weeks) so the STEM filing stays open,
or will they hold the role through the gap? Surface this before the final round, never after signing.

**Verdicts and the reason that must accompany each one.** A skip is never logged as a bare `SKIP` —
name which check failed, what was looked up, and what was found:
```
PASS  t1-both      "<C>" in E-Verify list (<source>, <date>) + work visa filings at <title> (<source>)
PASS  t2-h1b       "<C>" work visa filings at <title> (<source>); NOT in E-Verify list (<source>, <date>)
                   -> carry the STEM-OPT-gap warning onto the brief
SKIP  t3-everify   "<C>" in E-Verify list but no work visa filings on record (<source>, all years)
SKIP  t3-everify   "<C>" in E-Verify list; files work visa but not below <title/level> (<source>)
                   -> new-grad pipeline does not sponsor; same tier, both are
                      "STEM-OPT-capable but will not sponsor the user at their level"
SKIP  t4-neither   "<C>" not in E-Verify list (<source>, <date>) and no work visa filings (<source>)
UNSURE             lookup inconclusive (name ambiguity, subsidiary, or source unreachable)
                   -> say which source failed and what was tried; do NOT guess either way
```
`UNSURE` is not a skip. Report it with the ambiguity named so the user can resolve it in one look.
**On an inconclusive E-Verify lookup with work visa filings confirmed, treat it as `t2-h1b` and apply** —
under this rule E-Verify cannot block, so an unknown E-Verify status never costs an application.

**Log the tier on every posting, passed or skipped.** The label is the recovery mechanism: it lets the
`t3-everify` pool be re-opened later without re-running any lookup. **Never drop it because the posting
was skipped.**

**Where it goes — `tracker.md` has no tier column.** It is a fixed 12-column table (`jobtrack.py`
`COLS`) and rows are only ever written by `jobkit track add|set`, so the tier travels as a **structured
token in Notes**, first thing, in this exact form so it stays greppable and `insights` can parse it:
```
jobkit track add … --status skipped --notes "tier=t4-neither; not in E-Verify list (e-verify.gov, 2026-09-25) and no work visa filings (USCIS Data Hub, all years)"
jobkit track add … --status applied --notes "tier=t2-h1b; work visa at SWE I (h1bdata.info); NO E-Verify — work-authorization extension not filable here"
```
Same convention for the outreach fields the plan in `<projects folder>\cold-outreach-sourcing.md` needs:
`outreach=yes|no`, `channel=li-connect|email|github`, `referral=real|portal|none`. Semicolon-separated,
`key=value`, always at the front of Notes. **Adding real columns is the better long-term fix** — it needs
a `COLS`/`HEADER` change in `jobtrack.py` plus a migration of existing rows, so it is deliberately not
done here.

**Reason discipline applies to every gate, not just G7.** Any `skipped` log and any line in the final
report states the specific trigger — the quoted posting phrase, the number, the employer name, or the
failed lookup — never a category alone. "Skipped: 5+ years required (posting: *'5+ years of
professional experience'*)" is a reason; "Skipped: YOE" is not. the user overrides with `--force`, and a
reason they cannot evaluate is a reason they cannot override.

**How to run the two lookups, in order. Stop at the first that answers.**
1. **WebFetch / WebSearch** against the E-Verify employer search and the USCIS work visa Employer Data Hub,
   or `h1bdata.info` with the year filter on All years.
2. **Firecrawl** (`firecrawl_scrape` / `firecrawl_search`) when a host blocks the plain fetch.
3. **Playwright MCP — the fallback when neither can reach the source.** Both the E-Verify
   participating-employer search and the USCIS Data Hub are interactive, JS-driven pages that routinely
   defeat automated fetching, so this is an expected path, not a last resort. These are public,
   unauthenticated lookups — no logged-in session is needed, so Playwright is the right tool here, not
   Claude in Chrome: navigate, search the company, read the result from the accessibility-tree snapshot
   (ref-based, not screenshots), then close the page. Load the Playwright tools with a single
   `ToolSearch` call before starting. Do **not** log in anywhere or submit any form — these are public
   read-only searches. Fall back to Claude in Chrome only if Playwright itself fails to reach the page
   (e.g. active bot-detection that specifically requires a real logged-in browser profile).
4. Still no answer → `UNSURE`, naming which sources were tried and how each failed. Never guess.

**Not yet automated.** A `jobkit visacheck "<company>"` subcommand — caching the E-Verify employer list
and the USCIS Data Hub extract locally, with fuzzy name matching and a subsidiary alias table — is the
obvious next build, and would remove almost all of the above.

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

### 9. Fill the form — one fresh `apply-job-fill` subagent per form
Each form is filled by its own subagent, **`subagent_type: "apply-job-fill"`** (Sonnet, defined in
`<agents folder>\apply-job-fill.md`; it reads `references\fill.md` itself). Its
context starts empty for every form, which is the point: screenshots and field lists from one
form are never re-read while filling the next. **Do not read `form-pack.md`, `fill.md` or any
playbook in this thread, and do not drive the browser here** — except to close a tab after the user
confirms, or to answer their question about a tab. If the agent type is missing, stop and tell the user.

**Launch prompt — only this block:**
```
Mode: foreground | ahead | resume
Folder: applications\<folder>
Company / Role: <C> / <R>
Apply URL: <resolved apply URL from the prep return>
Platform: <platform>
Posted: <YYYY-MM-DD (N days ago) | unknown>
Tab: new | <tabId> | unknown             (resume: the tab from the last return; unknown after a crash)
the user's answers: <label -> answer, one per line>    (resume after BLOCKED only)
Deferred: <the list from PARTIAL_AHEAD>             (resume after PARTIAL_AHEAD only)
```

**Scheduling — one fill agent active at a time, one Chrome.**
- Serial by default: launch in `foreground`, wait for the return, hand off, wait for the user.
- **One form ahead — Greenhouse, Ashby, Lever only.** When a return is `READY_FOR_SUBMIT` and the
  NEXT queued form is Greenhouse/Ashby/Lever, show the user the handoff and immediately launch that
  next form in `ahead` mode (its own tab, no clicks, no focus changes). An ahead run always
  returns `PARTIAL_AHEAD`: do not show that to the user. When they confirm the first form, relaunch
  the ahead form in `resume` mode, foreground, with its `Deferred` list (the finish run: the
  leftover real clicks plus the final screenshot), and hand off its `READY_FOR_SUBMIT`. If they
  confirms before the ahead agent has returned, wait for its return first — never two fill
  agents at once. Never run a Workday, Oracle CX, SmartRecruiters or other multi-step /
  idle-timeout form ahead, and never start one while an earlier form still waits on the user.
  (Whether creating the ahead tab pulls focus is unverified: if the user reports their screen
  switching, stop using ahead mode and log it.)
- **Amazon: one at a time.** Amazon keeps ONE résumé per account, so a second Amazon form's
  upload would replace the first's. Never launch a second Amazon fill until the user confirms the
  first is submitted; other companies' forms may run in between.

Every `--notes` below starts with the posting's `tier=<t>;` token (G7 "Where it goes"), then
`rv=v2;` — the résumé layout variant (v2 = 2026-10-26 layout: city in header, software/AI put
Experience first and drop the courses line). Rows without `rv=` are v1. `insights` compares
outcomes by `rv` once v2 has ~150 submitted rows; bump the label whenever the base layout changes.

**Returns.**
- `READY_FOR_SUBMIT` → show the user the handoff block verbatim (its `Flags:` line carries prep's
  t2-h1b warning), plus the tab. Then step 10 with `--status filled` (`track set` if a
  `blocked` row already exists for the folder).
- `BLOCKED` → **step 10 right away** with `--status blocked --notes "<the blocker>"`, then tell
  the user the blocker in one line (log in, enter the code, upload the résumé, answer this). When
  they are done, relaunch in `resume` mode on the same tab with their answers; the row moves on with
  `track set`. A login or OTP wall is not a skill failure; do not log it. **Phenom `hvhapply`
  blocker:** the user's upload IS the submission, so when they say they uploaded, `track set <folder>
  --status applied --notes "hvhapply: the user uploaded"`; never resume that form.
- `AUTO_SUBMITTED` → report it, step 10 with `--status applied --notes "auto-submitted at <page>"`.
- `CLOSED` → step 10 with `--status skipped --notes "posting closed"`, close the tab.
- An agent that errors or returns nothing usable: relaunch it once in `resume` mode with the tab
  from an earlier return if there was one, else `Tab: unknown` (the agent finds its tab by host
  and job id). If it
  fails again, log the failure (hard rule 8), step 10 with `--status blocked --notes "fill agent
  failed twice"`, and hand the user the tab.

**Multi-link runs: a form found submitted was submitted by the user.** They submits finished forms
while other fills continue. If a tab shows a confirmation page, ask one line (`<Company> shows
submitted — you clicked it?`) and on yes log `applied`; it is an auto-submit only when the fill
agent's own click caused it.

Filled tabs stay open until the user confirms they submitted; then close that tab.

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
