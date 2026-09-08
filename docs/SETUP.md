# First-run walkthrough

This is the order that works. Budget about two hours for the first session; most of it is the
setup interview, which is where the value lives.

## 1. Install (10 minutes)
Follow the README's Install section: copy `skill/apply-job` into `~/.claude/skills`, copy
`workspace/` somewhere, drop `tectonic` into `workspace/bin`, `pip install -r
workspace/bin/requirements.txt`, replace `<WORKSPACE>` in `SKILL.md` and `references/inbox.md`.
Install the Claude in Chrome extension and sign in to the job boards you use in that Chrome
profile.

## 2. Run the setup interview (60–90 minutes)
In Claude Code, from the workspace folder:
```
/apply-job setup
```
Have your current résumé handy (any format) and be ready to answer "where does that number
come from?" for every metric. The interview writes:

| File | What it holds | Who edits it later |
|---|---|---|
| `master/profile.md` | identity, work authorization, visa answer, salary, EEO answers | you only |
| `master/content-pool.tex` | every job, project, verified metric, alternate framing | you only |
| `~/.claude/skills/apply-job/form-data.md` | education dates, cert IDs, reason-for-leaving, yes/no defaults | you or the skill |
| `qa-bank.md` | behavioural stories, one per entry, tagged by angle | you or the skill |

The pool does not need to fit one page. The skill selects per posting.

## 3. First three applications: use `--review`
```
/apply-job https://jobs.ashbyhq.com/<org>/<id> --review
```
`--review` shows every résumé change with its reason, the full match report and every
screener answer before anything touches the browser. Correct the voice where it is wrong;
each correction is appended to `resume-style.md` under "Learned corrections" and applies to
every later run. After three runs the voice is usually settled and you can drop the flag.

Pick low-stakes postings for these three. The first fill on a new ATS is also where you learn
which widgets need real clicks.

## 4. What a run prints
```
FRESH posted 2026-09-07, 1 day ago · no duplicate
Prep: VERDICT Worth it — Python/FastAPI backend, they want Kafka (you have coursework only)
      folder applications/2026-09-08_acme_backend-engineer · pagefit FULL · atscheck OK
Form filled through the last page — review and click Submit.
Posted: 2026-09-07 (1 day ago)
Locked fields entered: work auth Yes | sponsorship Yes | salary <your range> | start Immediately | EEO as profile
Work experience: 3 of 3 entered, order = PDF, descriptions verified after save
Education: 2 of 2 entered, verified after save
Optional sections filled: languages, websites
Unanswered: none
```
Read the locked-fields line every time. Then click Submit yourself and tell Claude
"submitted" so the tracker row flips from `filled` to `applied`.

Verdicts are `Strong`, `Worth it`, or `Skip`. A `Skip` is a real recommendation with a reason;
override it with `--force` if you disagree.

## 5. The files a run leaves behind
```
applications/2026-09-08_acme_backend-engineer/
  job-posting.md        the posting as extracted, posting date on line 1
  Resume.tex / .pdf     the tailored one-pager
  match-report.md       verdict, requirements met with proof lines, genuine gaps, selection log
  screener-answers.md   every screener answer that was entered
  form-pack.md          every field value the fill phase used (the audit trail)
```
`match-report.md` is worth reading before an interview: "rewordings to rehearse" lists every
bullet whose wording drifted from your pool.

## 6. Daily loop
- Morning: `/apply-job inbox` — reads Gmail, updates the tracker, prints action items (OAs
  with deadlines first), then status changes, then applications that were prepped but never
  submitted.
- Paste links as you find them, several at once is fine.
- Weekly: `/apply-job insights` — reply rates by role type and by source. It says
  `SAMPLE TOO THIN` until you have 15 known outcomes; believe it.
- `python bin/jobkit.py track audit` any time — lists tracker rows with problems and folders
  without rows.

## 7. When something goes wrong
- A form the skill cannot fill (Shadow DOM, iframe uploads, CAPTCHAs, login walls): it stops
  and says "your turn". Do that step, say "done", it continues.
- A field it is unsure about: it leaves the field blank and lists it under `Unanswered` rather
  than guessing. Fill it yourself before Submit.
- A wrong voice or a claim you would not defend: fix it in `--review`, or edit the pool. Never
  edit a tailored `.tex` by hand and expect the fix to persist; the pool is the source.
