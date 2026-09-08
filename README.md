# apply-job — a Claude Code skill that applies to jobs for you (but never clicks Submit)

Paste a job link into Claude Code. The skill dates the posting, checks you haven't applied
already, tailors a one-page résumé from your own verified content, compiles it to PDF, fills
the application form in your Chrome browser, and stops on the final review screen for you to
click Submit. It also reads your Gmail for outcomes, keeps a tracker, and tells you which kinds
of applications actually get replies.

It was built and refined over ~400 real applications across Ashby, Greenhouse, Workday,
Oracle CX, iCIMS, SmartRecruiters, Taleo, SuccessFactors and Talemetry. Every rule in it
exists because something went wrong without it.

## What it will never do

- **Invent a fact.** Every claim on a tailored résumé traces to a line in your content pool.
  Untraceable claims are reverted, not "improved".
- **Click Submit.** You always click the final button.
- **Create accounts, enter passwords or OTPs, or solve CAPTCHAs.** It stops at login walls
  and hands you the browser.
- **Edit your master files.** `content-pool.tex` and `profile.md` are read-only for the skill.
- **Enter a third party's contact details** (references, supervisors).

## Requirements

| Thing | Why |
|---|---|
| [Claude Code](https://claude.com/claude-code) | runs the skill |
| [Claude in Chrome](https://claude.ai/chrome) extension | fills forms in your logged-in browser |
| Python 3.10+ with `pip install -r workspace/bin/requirements.txt` | `jobkit.py` (page-fit, ATS text check, tracker, dedupe) |
| [Tectonic](https://tectonic-typesetting.github.io/) | compiles the LaTeX résumé to PDF |
| A Gmail API OAuth client (optional) | the `inbox` mode; see below |
| The `whenthisjobwasposted` MCP server (optional) | fallback for the posting-date gate |

Paths in the skill are written Windows-style (`bin\jobkit.py`). It works on macOS/Linux too;
Claude adapts the slashes.

## Install

1. **Copy the skill** into your Claude Code skills folder:
   ```
   cp -r skill/apply-job ~/.claude/skills/apply-job
   ```
2. **Create a workspace** anywhere (e.g. `~/job-applications`) from `workspace/`:
   ```
   cp -r workspace ~/job-applications
   ```
   Put `tectonic` (or `tectonic.exe`) in `~/job-applications/bin/`.
3. **Point the skill at the workspace.** In `~/.claude/skills/apply-job/SKILL.md` and
   `references/inbox.md`, replace every `<WORKSPACE>` with your workspace path.
4. **Run the setup interview** — in Claude Code, from the workspace folder:
   ```
   /apply-job setup
   ```
   It takes your existing résumé (PDF, Word, LaTeX or plain text) and a conversation, asks
   "where does that number come from?" for every metric, and writes the four data files below.
   Numbers you cannot source are left out and recorded so they never creep back in.
   Full walkthrough: [`docs/SETUP.md`](docs/SETUP.md). Or fill the templates by hand:
   - `master/profile.template.md` → `master/profile.md`: identity, work authorization, visa
     answer, salary range, notice period, EEO answers.
   - `master/content-pool.template.tex` → `master/content-pool.tex`: every job, project and
     verified metric you would defend in an interview. It does **not** need to fit one page; it
     is a superset. Keep the `% RELEVANCE:` tags, the `% --- ALTERNATE` blocks and the two
     fenced note blocks at the bottom — the skill depends on them.
   - `skill/apply-job/form-data.template.md` → `~/.claude/skills/apply-job/form-data.md`:
     education start dates, certification IDs, reason-for-leaving lines, the yes/no defaults.
   - Optional: `qa-bank.md` in the workspace — behavioural stories under `## Project` /
     `### Story` headings, used for screener text boxes only.
5. **Sanity check:** `python bin/jobkit.py pool tex | head` should print your LaTeX with the
   note blocks stripped; `python bin/jobkit.py track audit` should print `0 problems`.

### Gmail (optional, for `/apply-job inbox`)
Create an OAuth "Desktop app" client in Google Cloud with the `gmail.readonly` scope, save it
as `bin/gmail/credentials.json`, run `python bin/gmail/gmail_auth.py` once. **Publish the OAuth
app** (OAuth consent screen → Publishing status → In production); while it is in "Testing",
Google expires the refresh token every 7 days.

## Usage

| Command | What happens |
|---|---|
| `/apply-job <link>` | date gate → duplicate check → tailored résumé → form filled → you click Submit |
| `/apply-job <link> <link> ...` | same, prep runs in parallel, forms are filled one at a time |
| `/apply-job <link> --review` | shows every résumé change and screener answer for approval first; corrections you make are appended to `resume-style.md` as standing rules |
| `/apply-job <link> --fresh` | ignore the variant cache, tailor from scratch |
| `/apply-job <link> --force` | apply even though the hard filter said Skip |
| `/apply-job inbox` | reads Gmail for rejections / OAs / interviews, updates the tracker, writes interview-prep notes, prints a morning brief |
| `/apply-job insights` | reply rates by role type and by source (Handshake / Jobright / LinkedIn / …) |
| `/apply-job sweep [N]` | pulls the N freshest candidates from `job-matcher-feed/` and runs them through the normal flow |
| `/apply-job setup` | first-run interview: builds `profile.md`, `content-pool.tex`, `form-data.md`, `qa-bank.md` from your existing résumé + answers |
| `/apply-job scan` | reads your logged-in Handshake / Jobright / LinkedIn "recommended" pages and queues fits for `sweep` |

Plain-language updates work too: "Acme rejected me", "got an OA from Beta" update the tracker.

### What a run looks like
```
> /apply-job https://jobs.ashbyhq.com/acme/1234-...
FRESH posted 2026-09-07, 1 day ago · no duplicate
Prep: VERDICT Worth it — Python/FastAPI backend, they want Kafka (you have coursework only)
      folder applications/2026-09-08_acme_backend-engineer · pagefit FULL · atscheck OK
Form filled through the last page — review and click Submit.
Posted: 2026-09-07 (1 day ago)
Locked fields entered: work auth Yes | sponsorship Yes | salary Negotiable, $X–Y | start Immediately | EEO as profile
Work experience: 3 of 3 entered, order = PDF, descriptions verified after save
Education: 2 of 2 entered, verified after save
Unanswered: none
```
You review the form, click Submit, and say "submitted". The tracker row flips to `applied`.

## Docs
- [`docs/SETUP.md`](docs/SETUP.md) — first-run walkthrough: setup interview, first three runs with `--review`, what a run prints, the daily loop.
- [`docs/INTERVIEW-PREP.md`](docs/INTERVIEW-PREP.md) — what the inbox mode writes when an OA or interview arrives, and how to ask for prep.
- `workspace/qa-bank.template.md` — the story-bank format the screener answers draw from.

## How it is built (and why it is cheap to run)

A naive version of this cost ~150k tokens per application. This one runs at ~25k:

- **`bin/jobkit.py` is the read layer.** The skill never reads the tracker, the content pool
  or the Q&A bank in full. Every read is a subcommand that returns a few lines: `dup`, `posted`,
  `similar`, `pool tex|notes`, `qa list|get`, `pagefit`, `atscheck`, `schema`, `insights`,
  `track …`, `sweep-…`.
- **Prep is delegated.** One subagent per link tailors the résumé, runs the factual audit,
  compiles, checks page fit and the PDF text layer, drafts screener answers, and writes a
  single `form-pack.md`. Subagents run in parallel.
- **`form-pack.md` is the contract.** The fill phase reads only that file. If a value is
  missing, that is a prep bug, not a reason to open the pool.
- **ATS playbooks** (`ats/<platform>.md`) load one at a time. Ashby and Greenhouse expose a
  form schema, so the fill plan is written offline and executed in one browser batch.
- **The tracker is script-owned.** `jobkit track add|set` writes rows with a closed status
  vocabulary and escaped pipes; `insights` and `inbox` can therefore trust it.

### Safety mechanics worth knowing
- Every filled field is verified by reading it back from the DOM, never from a screenshot.
- On Workday, a JS-set value can pass the read-back and still be dropped on Save, so work
  experience is re-read after every Save and typed with real keystrokes.
- Every multi-page form gets a full page check before each Next.
- The compiled PDF's *text layer* is checked: XeTeX + Calibri emit a Unicode hyphen that makes
  `scikit-learn` invisible to ATS keyword search. `jobkit atsfix` rewrites the font maps.
- The résumé page must be *full*, not merely one page. Short pages are a mandatory loop.

## Customising

- **Your standing rules** go in `resume-style.md` (voice) and `SKILL.md` hard rules. The
  `--review` mode appends corrections to `resume-style.md` automatically.
- **Auto-skip rules** (salary floor + employer type, seniority, citizenship) are in
  `SKILL.md` "Pre-filter" and `references/tailoring.md` step 2. Edit them to your situation.
- **Employer caps** live in `bin/jobtrack.py` `EMPLOYER_CAPS`.
- **Thresholds**: posting staleness (`STALE_DAYS`), page-fit gap (`FULL_THRESHOLD_PT`), résumé
  reuse similarity (`PHASE1_THRESHOLD`) are constants at the top of `jobkit.py`.
- **New ATS**: the second time a platform appears, create `ats/<name>.md` with its detection
  pattern, page sequence and traps (`ats/_unknown.md` explains the format).
- **`sweep` mode** expects a `job-matcher-feed/<track>/<date>/<id>.json` drop from an external
  aggregator. `jobkit scan-add` writes the same format, so you can use it without one.

## Limitations

- Sites that render the whole form in Shadow DOM (LinkedIn Easy Apply, SmartRecruiters
  `oneclick-ui`) are partly or fully blocked for automated filling; the skill still tailors the
  résumé and hands you the browser. `references/ats-quirks.md` has the details.
- File uploads inside cross-origin iframes (iCIMS) must be done by you.
- Terms-and-conditions, arbitration agreements and e-signatures are filled but always recapped
  in the handoff so you know what you are agreeing to.

## Layout

```
skill/apply-job/          → copy to ~/.claude/skills/apply-job
  SKILL.md                 the always-loaded orchestrator (modes, hard rules, fill phase)
  references/tailoring.md  steps 1–8, run by the prep subagent
  references/inbox.md      Gmail sweep
  references/insights.md   conversion analysis
  references/ats-quirks.md cross-platform failure modes
  references/setup.md      the first-run interview
  ats/*.md                 one playbook per ATS
  resume-style.md          voice and structural rules
  form-data.template.md    → form-data.md (your form-only facts)
workspace/                → copy anywhere, point SKILL.md at it
  bin/jobkit.py            read layer + tools
  bin/jobtrack.py          tracker layer (imported by jobkit)
  bin/gmail/               Gmail API reader
  master/                  profile.template.md, content-pool.template.tex, resume.cls
  tracker.md               empty tracker with the header
  qa-bank.template.md      story-bank format
docs/                     SETUP.md, INTERVIEW-PREP.md
  applications/            one folder per application (created by the skill)
```

## License

MIT. `resume.cls` is the "Medium Length Professional CV" class from LaTeXTemplates.com
(CC BY-NC-SA 3.0); replace it with your own class if that licence does not suit you.
