# Tailoring — steps 1–8 of `/apply-job`

Loaded by the **prep subagent**, which runs this whole file for one posting and never
touches the browser except to fetch a JS-rendered posting. It never clicks Submit.

Read `resume-style.md` before any tailoring. Get the content pool with
`python bin/jobkit.py pool tex` (comment-stripped) — never read `content-pool.tex` directly.

### 1. Fetch & extract the posting
Try WebFetch first. If blocked, empty, or JS-rendered (LinkedIn, Workday, Greenhouse embeds): invoke the claude-in-chrome skill, then use the Chrome tools (`tabs_context_mcp` first, create a new tab, `get_page_text`) — the user's logins carry over.
Create folder `applications\<YYYY-MM-DD>_<company-slug>_<role-slug>\` and save `job-posting.md`. Its **first line** is the posting date handed to you by the orchestrator's date gate — `**Posted:** <YYYY-MM-DD> (<N> days ago)`, or `**Posted:** unknown`. Do not run the date check yourself and do not substitute a date you scraped off the page; the gate's value is the one the tracker records. **Immediately after extracting company and role, re-run the duplicate check with them:**
`python bin/jobkit.py dup "<url>" --company "<C>" --role "<R>"`. `MATCH` or `FUZZY MATCH` → stop,
return `VERDICT: Duplicate` with the prior row, log nothing else (the orchestrator logs
`duplicate`). The URL-only check at step 0 cannot see the same job posted on another board.
Then the body: company, role title, location, posted/reposted date if visible on the page, hard requirements vs preferred, responsibilities, exact keyword list, any screener questions visible, red-flag observations (reposted >60 days, "fast-paced" = understaffed patterns, junior title with senior requirements, vague responsibilities).

### 2. Hard filter — allowed to say no

**Auto-skip (standing rule):** verdict Skip immediately when the stated salary band tops out below <salary floor> AND the employer is government/public-agency/defense (cannot sponsor a work visa). Both conditions required; either alone is not a skip.
Compare hard requirements against master + profile. Verdict **Skip** when: a hard requirement is genuinely unmet (e.g. "3+ years professional Java" vs coursework), visa/work-auth mismatch, or wrong seniority tier. Be blunt: "Skip — they want 3 years of Java, you have coursework."
**Do not skip on years-of-experience alone when the posting reads "Bachelor's + N years"** — an M.S. counts as equivalent experience toward that bar (standing rule); only skip if the *type* of experience is genuinely missing, not just the year count.
On Skip: report the reasons; the orchestrator logs the row with `track add --status skipped --notes "<reason>"`. STOP. The user can override by re-running with `--force` — respect the override without re-arguing.

### 3. Tailor the resume

**3-0. Variant cache — check before tailoring anything.**
`python bin/jobkit.py similar <folder>/job-posting.md --company "<C>" --role "<R>"`
prints `REUSE` or `REBUILD (<reasons>)`. On **REUSE**: copy the named prior folder's
`Resume.tex` and `.pdf` into this folder, skip steps 3–5 entirely, and state in
the match report which application was reused and its cosine score. On **REBUILD**, or if
`--fresh` was passed, tailor normally. Phase 1 thresholds: cosine >= 0.45 AND same company.

Read `resume-style.md` (this folder) and `master\profile.md`. Get the content pool with
`python bin/jobkit.py pool tex` — comment-stripped, 34% smaller, still valid LaTeX.
**Never read `master\content-pool.tex` directly.**
Copy `master\resume.cls` into the application folder unchanged (required to compile), then
**Write** `<application-folder>\Resume.tex` directly from the pool text you
already have in context — never `cp` the pool and Read it back to Edit it, which pays for the
same ~8k tokens twice.

**3a. Score and select Experience and Projects.** The content pool holds more than fits one page — everything in it competes fresh on every run, nothing gets an inertia advantage for already being in the pool's default position.
1. List every Experience entry and every Project in the pool, using the `% RELEVANCE:` comment above each as a starting signal.
2. Score each 0-3 against the posting's stated requirements/keywords (0 = irrelevant, 1 = tangential, 2 = related, 3 = directly matches a named requirement).
3. Rank within each section. Select top-scoring entries down to what the page needs, respecting floors: **Experience never drops below 3 entries; Projects never drops below 2; and the total selected across both sections is never below 6** (added 2026-08-06 — a bare 3+2 floor was observed leaving a visibly unfilled page twice on 2026-08-06). Concretely: default to **4 Experience + 2 Projects or 3 Experience + 3 Projects**, whichever combination scores higher in aggregate, before falling further to 3+2 only if a 6th entry would genuinely score 0 with nothing defensible to say.
4. For Experience entries kept, if a `% --- ... framing (swap in for ...) ---` alternate bullet block exists for that entry and better matches the posting's track, use it in place of the default bullet(s) it's paired with — same underlying facts, different emphasis.
5. Experience order is fixed reverse-chronological regardless of score (resume-style.md 2026-07-26.B) — scoring decides what's *included*, never the order. Projects MAY be reordered by score.
6. Record the kept/dropped decision and a 1-line reason for each pool item — this feeds the match report's Selection section (step 6).

**3b. Rewrite and lay out.**
- Reorder Technical Skills rows by relevance to the posting (rows only, never invent or drop a row's content beyond the do-not-list rule in resume-style.md).
- Rewrite bullets per the style guide (XYZ formula, agreed voice). Mirror the posting's terminology ONLY where truthful (pool "CI pipelines" → posting "CI/CD" is fine; claiming unused tech is not).
- **Keep every bullet to at most 2 wrapped lines.** If a bullet stitches two separate accomplishments together with "X, then Y" / "X, then added Y", split it into two bullets instead (respecting the entry's 2-3 bullet cap) rather than stretching one long sentence. See `resume-style.md` 2026-08-02.
- Preserve the content pool's LaTeX preamble, macros, and layout — content edits only.
- Top third of the page gets the strongest, most posting-relevant material (summary + first bullets of most relevant experience/project).
- Strip every `%`-comment (relevance tags, alternate-framing blocks not used, guardrail notes) from the compiled copy — those are pool-only annotations, not resume content.

**3c. Portrayal pass (added 2026-08-31). Run after 3b, before the factual audit.**
Five checks, each one a defect actually observed on shipped output. Do all five every run.

1. **Tense.** For every entry whose end date is not `Present`, every bullet leads with a past-
   tense verb. For the entry that IS `Present`, every bullet leads with present tense. If the pool
   stores the current role's bullets in past tense, fix the tense in the copy, never in the pool.

2. **One metric in the Professional Summary.** The pool's summary carries no numbers, and the
   summary is the top-third's most valuable block. Weave in the single strongest metric already
   selected onto this page for this posting's track (the accuracy figure for an ML read, the scale figure for a full-stack read). The number must come from a
   pool bullet that is on the page, and the summary is the *anchor* -- the bullet keeps the
   surrounding detail. Never add a metric the page does not already carry.

3. **Summary/bullet scope agreement.** Whenever a bullet carries an environment qualifier
   ("in a research lab environment", "built and unit-tested", "on test data"), re-read the
   summary for the same claim and make it agree. A summary saying `shipped production-grade
   models` above a bullet saying `in a research lab environment` is worse than either
   wording alone -- it reads as caught rather than careful. Scope only ever moves DOWN.

4. **Verb openers.** List the first word of every bullet on the page. No opener may repeat
   (rule 2026-07-23.A). Reword the weaker bullet on any collision. Never resolve a collision by
   swapping a strong verb for a duty phrase: `Optimized course administration ... as primary
   POC` must not become `Served as primary point of contact for ...`. `Served as`, `Responsible
   for`, `Worked on`, `Helped with` are banned openers regardless of what they fix.

5. **Bold metrics survive.** Every `\textbf{}` around a number in the pool stays bold in the
   tailored copy. Bolded figures are what the six-second F-scan lands on; a rewrite that
   flattens them is a regression even when the words improve.

**3d. Project links.** Where a selected project has a real public repo or demo that the
pool records, put it in that project's header next to the tech tag with `\href`. Only link
what the pool records as existing and public — never invent a URL, a personal site, or a
demo link. If the pool names no link for that project, the header stays bare. Never prompt
the user about links; if they want one, they will add it to the pool.

**3e. Routing rules live in the pool, not in your judgment.** When an entry carries
`% --- ALTERNATE ... (swap in for ...) ---` blocks, the comment states the trigger (e.g.
"only when the posting names DAST"). Follow the trigger literally; do not pick an alternate
by feel, and never use two alternates for the same bullet. When the pool marks a project as
"goes FIRST for postings naming X", honour it — do not bury the strongest entry out of
habit.

### 4. Factual audit (before compiling)
**First run `python bin/jobkit.py pool notes "<entry>"` for every entry you kept.** That block
holds the VERIFIED PROJECT METRICS and the deliberately-excluded-claims list, and `pool tex`
strips it — without pulling it back, the audit has nothing to check against. Mandatory, not optional.

Go claim-by-claim through the tailored copy. For each bullet/skill/date: identify the master or profile line it traces to. Anything untraceable → silently revert that claim to the master's wording. This is a verification pass, not a formality.

### 5. Compile & enforce ONE FULL page
`& "<WORKSPACE>\bin\tectonic.exe" -X compile "<application-folder>\Resume.tex" --outdir "<application-folder>"`
Page check: `python bin/jobkit.py pagefit <application-folder>/Resume.pdf`
prints `pages=N gap=Npt (N%) verdict=FULL|SHORT|OVERFLOW`. **Use this, never a rendered image
read** — cheaper and objective. Calibrated on real output: good runs land at 22–29pt; the two
runs that shipped visibly short (Max Tech, Twitch) were 65pt. Threshold: gap <= 40pt = FULL.

The target is **one page, filled to near the bottom margin** — not merely "under two pages":
- **>1 page** → trim the lowest-relevance bullets and recompile.
- **`verdict=SHORT`** → this is a LOOP, not a one-shot menu, and it is a MANDATORY GATE, not optional cleanup — do not proceed to step 6 while skipping it (added 2026-08-06 after two same-day runs, Max Tech and Twitch, both compiled with visible bottom white space and were reported as done without the loop actually firing). After every lever below, recompile and **read the produced PDF again** to actually look at how much white space remains — don't infer "page is full" from having applied a lever or from a match-report note; only the rendered page is evidence. Before moving to step 6, state in one line which levers were checked and what the final rendered page looked like (e.g. "levers 1-5 checked, <filler entry> added, page now full to bottom margin") — this line is the gate; if you cannot honestly write it, the loop isn't done. Keep applying the next lever and re-checking until the bottom margin is close to full or every lever is exhausted. Order of levers:
  1. restore trimmed bullets,
  2. pull in the next-highest-scoring dropped Experience/Project entry from step 3a's ranking (at its normal 2-3 bullet length),
  3. restore the Education "Relevant Courses" line,
  4. add real detail to the most relevant entry.
  5. **Final catch-all:** if, after re-checking the rendered PDF, space still remains and <filler entry> isn't already on the page, add it back with a single dense bullet — regardless of how large or small the remaining gap is (no minimum-gap gate; see the <filler entry> exception in `resume-style.md` 2026-08-02). This step always runs before accepting a short page.
  Never pad with filler or invented content.
- **Every experience and every project must have ≥2 bullets, EXCEPT <filler entry> which may run with exactly 1** as a fine-grained page-fill lever (see `resume-style.md` 2026-08-02). If trimming would leave any other entry with one bullet, restore a second or drop the entry entirely.

**5a. ATS text-layer gate (added 2026-08-30, MANDATORY, runs once the page-fit loop passes).**
The page can look perfect and still parse wrong: an ATS reads the PDF's extracted *text layer*,
not the rendering. XeTeX + Calibri reverse-maps every literal `-` to U+2010 HYPHEN, so
`scikit-learn`, `<exam code>`, `AES-256-GCM`, `full-stack` and even the phone number are invisible
to a parser searching the ASCII spelling. Measured on the 2026-08-30 D. E. Shaw resume:
**53 broken hyphens**, i.e. every hyphenated keyword on the page.

```
python bin/jobkit.py atscheck "<application-folder>/Resume.pdf"
```
prints `atscheck pages=N badhyphen=N other=<chars> verdict=OK|WARN` plus the at-risk keyword
tokens. On `WARN` with `badhyphen>0`, run the fix and re-check:
```
python bin/jobkit.py atsfix   "<application-folder>/Resume.pdf"
python bin/jobkit.py atscheck "<application-folder>/Resume.pdf"
```
`atsfix` rewrites only the ToUnicode CMaps (U+2010/2011/2012/2212 -> `-`); content streams are
untouched, so the rendered page is unchanged and en-dashes in date ranges survive. Run it
**after the final compile** -- any recompile undoes it. Do not proceed to step 6 until
`atscheck` prints `verdict=OK`. If `other=` names an unfamiliar character, report it in the
match report rather than silently rewriting it.

Ignore the `Overfull \hbox (30.0pt)` warning at `\begin{document}` — it comes from the class file's `\printname` and is present in the untouched master. Any *other* overfull warning is real and must be fixed.
If compile errors: fix only what your edits broke; if the master itself fails, stop and tell the user.

### 6. Match report → `match-report.md`
Headline block (readable in <30 seconds):
```
VERDICT: Strong | Worth it | Skip
<one sentence of reasoning>
Red flags: <n> | Rewordings to rehearse: <n>
```
Below the fold: requirements met (each with the exact resume line proving it), genuine gaps (never papered over), red flags, keywords woven in, top-third framing chosen (one line — logged to tracker), **pool gaps** (any place a bullet named what was built but the pool records no purpose/outcome for it, or a project with no link on record, so the user can decide whether to add the fact to the master), **rewordings to rehearse** (every bullet whose key terms drift notably from the pool's wording, so nothing surprises the user in an interview).

**Selection** (from step 3a): every Experience and Project entry in the content pool, marked kept or dropped, with the 1-line reason. Example:
```
Selection:
  Experience — <Employer A>: KEPT (leadership + secure tooling, score 2)
  Experience — <Employer B>: KEPT (ML framing swapped in, score 3, direct match)
  Experience — <filler entry>: DROPPED (score 0, no teaching/mentorship angle in posting)
  Experience — <Employer D>: KEPT (floor — 3rd of 3 required, score 1)
  Project — <Project A>: KEPT, ORDERED FIRST (score 3, posting names LLM agents)
  Project — <Project B>: KEPT (score 2)
  Project — <Project C>: DROPPED (score 1, posting is pure security)
  Project — <Project D>: DROPPED (score 0)
```
Score every project in the pool — a run whose selection list is shorter than the pool has
skipped a candidate.

### 7. Screener answers → `screener-answers.md`
For each question found in the posting plus the standard set (why this company, availability, salary, work auth): 50–120 words, first sentence answers the question outright, one concrete detail from real experience, zero filler ("I am writing to express..." is banned). Locked-field questions: one line straight from profile, marked `🔒 LOCKED — fill from profile, recap at handoff` (they are filled without confirmation; see hard rule 4).
For narrative/behavioral questions ("a challenge", "proud of", "how do you use AI"), pick with `python bin/jobkit.py qa list` (23 headings, each tagged with its angle), then pull
only the chosen one or two with `python bin/jobkit.py qa get "<substring>"`. **Never read
`qa-bank.md` whole** — it is 58KB and a run uses 4–8% of it. Use only ONE or TWO of the most fitting stories for that question and role — never dump multiple examples or list every project (qa-bank usage rule). Pick the single best-matching angle, or at most two that complement each other, and keep the rest in reserve.

### 7a. Cover letter (on-request only)
Not part of the default flow — skip unless the user explicitly asks for one on that run (e.g. "also do a cover letter for this one"). When asked: write `cover-letter.tex` in the application folder using the same factuality rules as the resume (every claim traces to master/profile, same voice/style rules from `resume-style.md`), then compile to `cover-letter.pdf` with tectonic — never leave it as markdown/tex-only, since some ATSes require a PDF upload.

### 8. Checkpoint (trust-aware)
- **`--review` flag: FULL REVIEW / teaching mode.** Show the tailored resume changes with explanations of why each bullet changed, the full match report, and every screener answer. Wait for approval. When the user corrects voice/phrasing: apply the fix AND append the lesson to `resume-style.md` under "## Learned corrections" so it persists.
- **Otherwise: spot-check mode.** Show only the match-report headline block, then proceed straight to the browser.


---

### 8b. Write `form-pack.md` — the handoff to the fill phase

The fill phase reads **only this file**. It must never need `content-pool.tex`, `qa-bank.md`,
`resume-style.md`, or the tailored `.tex`. Write `<application-folder>\form-pack.md` with:

- **Identity** — name, email, phone, address, LinkedIn, GitHub (`profile.md`)
- **Locked fields** — work auth, sponsorship, salary, notice period and the four EEO answers,
  resolved to final values (hard rule 4: these get filled, not confirmed)
- **Education** — both degrees with start AND end month/year, degree, major, GPA (`form-data.md`)
- **Work experience** — the entries that made it onto the PDF, in PDF order (most recent END
  date first, current role at the top — SKILL.md rule 9b), each with title,
  employer, location, dates, currently-work-here flag, reason for leaving, and **that entry's
  tailored bullets as plain text with LaTeX stripped** (`\%`→`%`, `--`→`–`, `\&`→`&`, `\$`→`$`)
- **Certification, languages, standard yes/no defaults** (`form-data.md`)
- **Screener answers**, verbatim
- **Resume PDF absolute path**
- **Fill plan** — run `python bin/jobkit.py schema <url>`. On Ashby/Greenhouse it returns the
  whole form; write an ordered `field key → value` list with every dropdown answer already
  matched against the schema's own option strings, and flag which fields need a real click
  rather than a synthetic one. If the call prints `NO_SCHEMA_API` or `SCHEMA_FAILED`, write
  `NO SCHEMA — DOM path` and let the fill phase explore. **Never invent a fill plan.**

### 8c. Return to the caller

Report only: `VERDICT` + one-line reason, the folder path, the `pagefit` verdict, whether the
résumé was reused (and from which application, with its score), and any question that could
not be answered from the sources. Nothing else — everything else is on disk.
