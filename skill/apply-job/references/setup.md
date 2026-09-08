# `/apply-job setup` — first-run interview

Run once, before the first application. Also re-run a single section later ("setup pool" /
"setup qa") when the user has new work to add. Everything below is a conversation with the
user; nothing is written from a résumé file alone.

**Ground rule for the whole session:** the pipeline's hard rule 1 (never invent a fact) starts
here. A metric, tool, title, date, team size or scope is written into the pool only after the
user confirms it and says where it comes from (a dashboard, a commit, a report, memory of the
number). "I think it was about 40%" is a pause, not a value. Anything the user retracts or
cannot source goes into the pool's `NOT ON THE RESUME, DELIBERATELY` block so a later tailoring
pass can never bring it back.

## 0. Inputs
Ask for whatever exists: current résumé (PDF, docx, LaTeX, plain text), LinkedIn profile URL or
PDF export, GitHub URL, portfolio. Read them all once. Then ask the three framing questions:
1. What roles are you targeting? (2–3 tracks, e.g. "backend SWE", "security engineer",
   "ML engineer" — these become the `% RELEVANCE` vocabulary.)
2. Seniority you are applying at, and years of experience as you want it phrased.
3. Anything you do NOT want on a résumé (an employer, a project, a number, a technology you
   never want to be interviewed on).

## 1. `master\profile.md`
Walk the template top to bottom and fill it from the user's answers. Locked fields need a
decided answer, not a description:
- Work authorization and the visa question in **both** forms: the combined "now or in the
  future" question and the two-part version. Get the exact words the user wants entered.
- Salary: a range, and the sentence to use when a form forces one number.
- Notice period / earliest start.
- EEO self-identification: a direct answer for gender, race/ethnicity (plus the fallback when
  the exact option is missing), veteran status, disability status — or "decline" per field.
  These are the user's choices; record them and move on.
- "How did you hear about us" default: the job board the link came from (hard rule 7); confirm
  the fallback.
Write the file, show it, get an explicit OK.

## 2. `master\content-pool.tex`
This is the long part. Go **entry by entry**, most recent first. For each employer and each
project:
1. Confirm title (exact, as the employer would state it — titles are frozen facts), employer
   legal name, location, start and end month/year, whether it is current.
2. Ask what the user actually did there. Get 3–6 raw facts, not bullets.
3. For every fact that carries a number, ask: "where does this number come from?" Sourced →
   goes in `VERIFIED PROJECT METRICS` with the source. Unsourced → offer to keep the fact
   without the number, or drop it. Never round up, never estimate for them.
4. For every tool or technology named, ask: "did you use it yourself, or was it in the
   system?" Only self-used tools go in that entry's tech tag or bullets.
5. Draft 2–3 bullets in the XYZ shape (`resume-style.md`), read them back, and ask the
   two-minute test: "could you talk about this line for two minutes, unprepared?" Reword until
   yes.
6. Ask which tracks the entry serves and write the `% RELEVANCE:` line. If the same facts read
   differently for another track, draft a `% --- ALTERNATE` block with its trigger.
7. Ask whether there is a public repo or demo; only a confirmed public URL goes in `\href`.
Pick exactly one low-relevance entry as the **filler entry** (allowed to run with one bullet as
the last page-fill lever) and mark it in its `% RELEVANCE` line.
Education: both degrees, dates, GPA only if the user wants it shown (the form-side GPA rule is
separate and lives in `form-data.md`). Skills rows: only things that appear somewhere in the
entries above, plus coursework languages last and clearly marked.
Write the file from `content-pool.template.tex`, keeping every convention comment. Compile it
once with tectonic to catch LaTeX errors — it may run to two or three pages; that is expected
for a pool. Run `python bin/jobkit.py pool tex` and `pool notes` and confirm both print.

## 3. `form-data.md`
From `form-data.template.md`: education start dates (forms ask, résumés rarely say), the GPA
to enter and its scale, field-of-study search terms for lookup widgets, reason-for-leaving
lines per employer, employer locations, certification IDs and verification URL, languages,
the yes/no defaults, and the "not known, leave blank" list. Every value confirmed, none
inferred.

## 4. `qa-bank.md`
Use `workspace\qa-bank.template.md` for the format — `## <Project or employer>` then
`### Story <letter> — <angle>: <title>`; `jobkit qa list` parses exactly those two heading
levels. For each pool entry ask for at least one story: the situation, what the user decided,
what happened, what they would say if asked "why". Tag each with the angle it serves
(software / security / AI / leadership / conflict / failure). 120–250 words each, first
person, no metric that is not also in the pool. Stories may carry detail that is too long
for a résumé; that is what this file is for. The separation rule applies from day one: this
file is never a source for résumé bullets.

## 5. Finish
Run and show: `python bin/jobkit.py pool tex | head`, `pool notes`, `qa list`,
`track audit` (expect `0 problems`). Then tell the user:
- run the first three applications with `--review` — corrections they make there are appended
  to `resume-style.md` and shape every later run;
- re-run `setup pool` whenever a new project or job is worth adding, and `setup qa` after any
  interview that produced a story worth keeping;
- the Gmail step in the README if they want `inbox`.
