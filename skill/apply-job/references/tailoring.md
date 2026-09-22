# Tailoring — steps 1–8 of `/apply-job`

Loaded by the **prep subagent**, which runs this whole file for one posting. It never touches
the browser except to fetch a JS-rendered posting, and it never clicks Submit.

**Style guide: `<skill folder>\resume-style.md`** (the skill root; this
file is in `references\`). Never read anything under `skill-backups\`.

**Load order is where the tokens go.** Do NOT read the style guide or the pool up front. Step 3-0
decides: a REUSE needs neither, a track base needs the style guide and single pool entries, only
a from-scratch tailor needs `jobkit pool tex`.

### 1. The posting
**Normal case: the prompt says `job-posting.md: written by jobkit meta`.** The folder and
`job-posting.md` exist, body verbatim from the ATS API, the gate's date on line 1. Read it. Do
not fetch, rewrite, or re-run the duplicate check. Note the hard requirements, screener
questions and red flags (reposted >60 days, "fast-paced" understaffing patterns, junior title
with senior requirements) for the match report.

**`NO_META` case only.** Fetch order: WebFetch → `firecrawl_scrape` → your OWN Chrome tab
(`tabs_create_mcp`, `navigate`, `get_page_text`, `tabs_close_mcp`; never touch a tab you did not
create). LinkedIn cannot be fetched by Firecrawl. Create
`applications\<YYYY-MM-DD>_<company-slug>_<role-slug>\` (date FIRST, underscores; the older
`<company>-<role>-<date>` folders are legacy) and save `job-posting.md`: line 1
`**Posted:** <the date the prompt gave you>` (never a date scraped off the page), then
`- **Company:**`, `- **Role:**`, `- **Location:**`, `- **Pay range published:**` bullets, a
`---` line, then the body. Then run
`python bin/jobkit.py dup "<url>" --company "<C>" --role "<R>"` (`MATCH` / `FUZZY MATCH` → stop,
return `VERDICT: Duplicate` with the prior row) and `python bin/jobkit.py triage <folder>`
(`SKIP` → return `VERDICT: Skip` with its reason).

### 2. Hard filter — allowed to say no
`jobkit triage` has already removed the clear-cut cases. What is left for you is the judgement
that needs the pool. The prompt's `Triage:`
line carries any flagged lines: weigh them. `--force` means the user overrode a skip: tailor it, do
not re-argue.

Verdict **Skip** when a hard requirement is genuinely unmet ("3+ years professional Java" vs
coursework), on a visa / work-auth mismatch, or the wrong seniority tier. Be blunt.
- **Years of experience.** Their M.S. covers a requirement of **up to 2 years** ("2+ years",
  "1-3 years", "Bachelor's + 2" are never a skip on the count). **A first stated requirement of
  3+ years IS a skip.** A range counts by its lower bound ("2-6 years" is 2). A `YOE` flag
  reaching you means the line was softened, on a Master's path, or not the first requirement:
  read it and apply the same rule.
- Also a Skip: the employer saying it will not sponsor now or in the future, "OPT, CPT or EAD not
  accepted", a graduation-cohort program they are outside of, a non-US location, an ITAR /
  US-person requirement, a required stack with zero pool evidence. A residency requirement is a
  Skip only when the posting rules out relocating. "Must be authorized to work in the US" is NOT
  a skip.
- On Skip: report the reasons and STOP; the orchestrator logs the row. the user overrides with
  `/apply-job <link> --force`.

### 3. Tailor the resume

**3-0. Variant cache.** `python bin/jobkit.py similar <folder>/job-posting.md --company "<C>" --role "<R>"`
prints `REUSE` or `REBUILD (<reasons>)`. On **REUSE**: copy the named prior folder's
`Resume.tex` and `.pdf` here, skip steps 3–5, and state in the match report which
application was reused and its cosine score. Still run 5a (`atsfix`) and 8b (`formpack`).
Thresholds: cosine >= 0.45 AND same company.

**3-0b. Track base — the default path on REBUILD.**
Run `python bin/jobkit.py skills <application-folder>` first. Its `TRACK` line reads
`TRACK security=<n> software=<n> ai=<n> -> base: <track> [HYBRID: <a>+<b>]`. **Use the base it
names; never pick by feel.** (The title decides first, security > AI > software, a title word
is worth 6 hits; otherwise the highest count with 2+ hits wins and ties go to `software`;
boilerplate-only hits are ignored.) **On `HYBRID`, read `references\hybrid-swaps.md` and make the
swaps it lists: they are mandatory.** State the base, the HYBRID tag and each swap in the match
report's Selection section.

Then `python bin/jobkit.py base use <track> <application-folder>`:
- `BASE <track> -> …`: an already-audited one-page résumé for that track is now in the folder
  as `Resume.tex`, with `resume.cls`. **Read it once, then change it with `Edit`
  calls; never rewrite the file whole.** Read the style guide first. Expected edits: the
  Professional Summary (3c.2, 3c.3), the skills-table rebuild and keyword-coverage pass (3b,
  mandatory here too), the routed bullets (3e), project order (3f), truthful mirrored
  terminology, and an entry swap only when 3a's scoring says another entry clearly beats one on
  the page (or a HYBRID swap requires it). Pull one entry with
  `python bin/jobkit.py pool entry "<name>"` (it prints the entry plus its alternate framings).
  Do NOT load `jobkit pool tex` on this path. Steps 3a–3f apply only to what you change.
- `NO_BASE` / `BASE_STALE`, or `--fresh` in the prompt: tailor from scratch as below, and say so
  in your return so the user can re-set the base.

**From scratch (fallback only).** Read the style guide and `master\profile.md`. Get the pool with
`python bin/jobkit.py pool tex`. **Never read `master\content-pool.tex` directly.** Copy
`master\resume.cls` into the application folder unchanged, then **Write**
`<application-folder>\Resume.tex` from the pool text already in context.

**3a. Score and select Experience and Projects.** Everything in the pool competes fresh on
every run.
1. List every Experience entry and every Project, using the `% RELEVANCE:` comment above
   each as a starting signal. A run whose selection list is shorter than the pool skipped one.
2. Score each 0-3 against the posting (0 irrelevant, 1 tangential, 2 related, 3 directly matches
   a named requirement).
3. Rank within each section and select, respecting floors: **Experience never below 3 of 4;
   Projects never below 2; total never below 6.** Default to **4 Experience + 2 Projects or
   3 + 3**, whichever scores higher; fall to 3+2 only if a 6th entry would genuinely score 0.
4. For kept Experience entries, use a `% --- ... framing (swap in for ...) ---` alternate block
   when it better matches the posting's track: same facts, different emphasis.
5. Experience order is fixed reverse-chronological regardless of score. Projects MAY be reordered.
6. Record kept / dropped and a 1-line reason for every pool item (feeds step 6).

**3b. Rewrite and lay out.**
- **The `jobkit skills` output decides every skill question.** It matches the posting against
  `master\skills-inventory.md`:
  - `TRUE <posting spelling> -> <page wording> [row] (level) | never: ...` — put it on the page
    using **exactly that page wording**, in that row, never stretched into anything on its
    `never:` list. `level`: `shipped`; `reviewed` (they audited someone else's system, e.g. Azure);
    `coursework` (skills row only, last in its row, never in the summary or a bullet). A
    `[Project]` row (Next.js, React Native) stays in project tech-tags and bullets and **never**
    enters the skills table.
  - `BANNED <term>`, `GAP <keyword>`, `UNKNOWN <term>` — never on the page in any form. List
    them under genuine gaps; list `UNKNOWN`s under pool gaps too so the user can add a row.
  - Do not judge "is this keyword true?" yourself. If you believe a real skill is missing from
    the inventory, do not add it to the résumé: say so under pool gaps.
- **Rebuild the Technical Skills table for this posting** (style guide → Skills section): order
  rows by relevance, add every TRUE tool, add the Practices row when it qualifies, drop or merge
  rows with zero overlap. Nothing enters the table that is on neither the pool's skills table
  nor a non-banned inventory row.
- **Keyword-coverage pass.** ATS matching is literal: every TRUE keyword appears on the page
  **verbatim in the posting's own spelling** (`full stack` vs `full-stack`, `back-end` vs
  `backend`, `CI/CD`, `ETL`, `REST APIs`). Tools go in the skills table; practices in the
  Practices row or a bullet; domain phrases in the summary or a bullet. This changes the
  spelling and placement of true facts; it never creates one.
  The gate counts a keyword as covered when EITHER its posting spelling or its row's page
  wording is on the page. A `COVERED-BY-WORDING` line means only the wording is there: the
  sanctioned way to add the posting's spelling too is a parenthetical beside the wording,
  `Machine Learning (ML)`, `monitoring and alerting (observability)`, never a new claim. A
  spelling on the row's own `never:` list (RAG) is left off on purpose.
- Rewrite bullets per the style guide (XYZ formula, agreed voice). Mirror the posting's
  terminology ONLY where truthful (pool "CI pipelines" → posting "CI/CD" is fine).
- **Every bullet at most 2 wrapped lines.** A bullet stitching two accomplishments with "X, then
  Y" is split in two (respecting the entry's 2-3 bullet cap).
- Preserve the pool's LaTeX preamble, macros and layout: content edits only.
- Top third of the page carries the strongest, most posting-relevant material.
- Strip every `%`-comment from the compiled copy.

**3c. Portrayal pass. Run after 3b, before the factual audit. All five, every run.**
1. **Tense.** An entry whose end date is not `Present` leads every bullet with a past-tense
   verb; the `Present` entry leads with present tense (if the pool stores the current role in past tense, fix it in the copy). Fix it in the copy, never in the pool.
2. **One metric in the Professional Summary.** Weave in the single strongest metric already on
   this page for this posting's track. It must come from a bullet that is on the page; the
   bullet keeps the detail. Never add a metric the page does not already carry.
3. **Summary/bullet scope agreement.** When a bullet carries an environment qualifier ("in a research lab environment", "on test data"), the summary
   must agree with it. Scope only ever moves DOWN.
4. **Verb openers.** No first word of a bullet may repeat on the page. Reword the weaker bullet.
   Never fix a collision with a duty phrase: `Served as`, `Responsible for`, `Worked on`,
   `Helped with` are banned openers.
5. **Bold metrics survive.** Every `\textbf{}` around a number in the pool stays bold. Design
   counts that the pool does not bold (`7-rung`, `4 tools`) stay unbold.

**3d. Project links.** Where the pool records a real public repo or demo, put it in that
project's header next to the tech tag: `\item \textbf{<Project>} \textit{(<techs>)} \hfill
\href{<url>}{<shown>}`. Never invent a URL. Which projects are linked is settled in the pool; never prompt the user about links.

**3e. Routing rules live in the pool, not in your judgment.** When an entry carries
`% --- ALTERNATE ... (swap in for ...) ---` blocks, the comment states the trigger (e.g.
"only when the posting names DAST"). Follow the trigger literally; never pick an alternate
by feel, and never use two alternates for the same bullet.

**3f. Project ordering.** When the pool marks a project as "goes FIRST for postings naming
X", honour it; do not bury the strongest entry out of habit.

### 4. Factual audit (before compiling)
**First run `python bin/jobkit.py pool notes "<entry>"` for every entry you kept** (the VERIFIED
PROJECT METRICS and the excluded-claims list; `pool tex` strips them). Mandatory.

Go claim by claim through the tailored copy (on the track-base path: every line you changed).
Each bullet, skill and date must trace to a master or profile line. Anything untraceable →
revert to the master's wording.

**Then `python bin/jobkit.py audit <application-folder>\Resume.tex`:**
- `audit FAIL` — a number on the page exists nowhere in the pool or profile. Fix and re-run.
  Never ship a FAIL.
- `audit NUMBER-CONTEXT` — the number is in the pool beside different words ("12-person" vs "12
  boards"). Same measurement → fine; otherwise revert.
- `audit WARN` — a tech-looking term not in the pool. A truthful mirror of the posting's wording
  for something the pool records → keep it and list it under rewordings to rehearse; a new
  claim → revert it.
- `audit OK` — nothing to do. The script catches invented tokens, not drifted meaning; your
  claim-by-claim pass is what catches scale inflation.

### 5. Compile & enforce ONE FULL page
`& "<WORKSPACE>\bin\tectonic.exe" -X compile "<application-folder>\Resume.tex" --outdir "<application-folder>"`
then `python bin/jobkit.py pagefit <application-folder>/Resume.pdf` →
`pages=N gap=Npt (N%) verdict=FULL|SHORT|OVERFLOW`. **Use this number, never a rendered image.**
Good runs land at 22–29pt; gap <= 40pt = FULL.

The target is **one page, filled to near the bottom margin**:
- **>1 page** → trim the lowest-relevance bullets and recompile.
- **`verdict=SHORT`** → a LOOP and a MANDATORY GATE. After every lever, recompile and **re-run
  `pagefit`**: its `gap=` is the only evidence. Before step 6, state in one line which levers
  were applied and the final `pagefit` line; if you cannot honestly write it, the loop is not
  done. Levers, in order:
  1. restore trimmed bullets,
  2. pull in the next-highest-scoring dropped entry from 3a (at its normal 2-3 bullets),
  3. restore the Education "Relevant Courses" line,
  4. add real detail to the most relevant entry,
  5. **final catch-all:** if still `SHORT` and <filler entry> is not on the page, add it with
     a single dense bullet, whatever the remaining gap. This always runs before accepting a
     short page.
  Never pad with filler or invented content.
- **Every experience and project has ≥2 bullets, EXCEPT <filler entry>, which may run with
  exactly 1.** If trimming would leave another entry with one bullet, restore a second or drop
  the entry.

**5a. ATS text-layer gate (MANDATORY, after the page-fit loop passes).** XeTeX + Calibri maps
every literal `-` to U+2010, so hyphenated keywords are invisible to a parser.
```
python bin/jobkit.py atsfix "<application-folder>/Resume.pdf"
```
It rewrites the text layer and prints `atscheck pages=N badhyphen=N other=<chars> verdict=OK|WARN`.
Run it **after the final compile**: any recompile undoes it. Do not proceed until `verdict=OK`.
If `other=` names an unfamiliar character, report it in the match report.

**5b. No auto-hyphenation.** Every resume carries, directly after `\begin{document}`:
`\hyphenpenalty=10000 \emergencystretch=2em` (the three bases already do; add it on the
from-scratch path, never in `master\resume.cls`). Breaks at a real hyphen are fine. This can
push a bullet onto an extra line: rerun `pagefit` after any edit, and on OVERFLOW tighten the
bullet whose last line is a one- or two-word orphan (same facts, fewer words) before trimming
content.

Ignore the `Overfull \hbox (30.0pt)` warning at `\begin{document}` (it is in the untouched
master). Any *other* overfull warning is real. On compile errors fix only what your edits
broke; if the master itself fails, stop and tell the user.

### 6. Match report → `match-report.md`
Headline block (readable in <30 seconds):
```
VERDICT: Strong | Worth it | Skip
<one sentence of reasoning>
Red flags: <n> | Rewordings to rehearse: <n>
Keyword coverage: <on page>/<posting keywords> (<X>%) | true-but-missing: <n>
```
**Keyword coverage gate.** Copy the line from
`python bin/jobkit.py skills <application-folder> --pdf <application-folder>\Resume.pdf`
(after the final compile + `atsfix`). `true-but-missing` must be **0** before you leave step 5;
if one truly cannot fit, list it with the reason. Never compute the line by hand and never edit
`job-posting.md` to change it. `NO_KEYWORDS posting too thin to score` means the gate gave NO
evidence: say exactly that, it is not a pass. A `THIN` marker means few keywords were found: read
the requirements by hand and put what the scan missed under genuine gaps.

Below the fold: requirements met (each with the exact resume line proving it), genuine gaps
(never papered over; include every `GAP`, `BANNED` and `UNKNOWN`), red flags, keywords woven in,
top-third framing chosen (one line, logged to the tracker), **pool gaps** (a bullet that names
what was built with no purpose or outcome in the pool, a project with no link on record, every
`UNKNOWN`, any skill you believe is missing from the inventory), **rewordings to rehearse**
(every bullet whose key terms drift from the pool, every `coursework` or `stated` item used).

**Selection** (from 3a): every Experience and Project entry, kept or dropped, with a 1-line
reason; the base used; HYBRID and swaps if any. Example:
```
Selection:  base = security (TRACK security=5 software=4 ai=2, HYBRID security+ai)
  Experience — <Employer A>: KEPT (leadership + secure tooling, score 2)
  Experience — <Employer B>: KEPT (ML framing swapped in per HYBRID rule, score 3)
  Experience — <filler entry>: DROPPED (score 0, no teaching angle in posting)
  Project — <Project A>: KEPT, ORDERED FIRST (score 3; policy-gate bullet per hybrid-swaps.md)
  Project — <Project E>: DROPPED (displaced by the mandatory HYBRID swap)
```

### 7. Screener answers → `screener-answers.md`
For each question in the posting plus the standard set (why this company, availability, salary,
work auth): the first sentence answers the question outright, one concrete detail from real
experience, zero filler ("I am writing to express..." is banned). Locked-field questions: one
line straight from profile, marked `🔒 LOCKED — fill from profile, recap at handoff`.

**Punctuation.** Inside an answer use only commas and periods (plus a question mark or
apostrophe where grammar needs one). **No colons, no semicolons, no dashes of any kind** as
sentence punctuation: restructure instead ("I made three choices: A, B and C" → "I chose A, B
and C"). This covers text pulled from `qa-bank.md`: rewrite it as you pull it, never paste it
raw. Colons inside a URL, a time or a code identifier are fine. Before finishing, search the
answers for `: ` and `;` and fix every hit.

**Length is set by the kind of question, not by the box.** Count characters.

| Question kind | Words | **Characters** | Examples |
|---|---|---|---|
| Factual / locked screener | 1 line | ≤ 150 | availability, salary, work auth, notice period |
| Why this company / why this role | 100–150 | **600–900** | "Why Cursor?", "What interests you about this team?" |
| Narrative / behavioral | 150–250 | **900–1,500**, aim ~1,200 | "a project you're proud of", "a challenge", "how do you use AI" |
| Cover letter (7a, on request only) | 250–400 | **1,500–2,400** | |

- **Hard ceiling for any single answer: 2,700 characters (~450 words).**
- **A stated limit is a ceiling, never a target.** Never lengthen an answer to approach a limit.
- **Box capacity is not a recommendation** (Workday allows 4,000 characters, Ashby `LongText` is
  unbounded). Use the table.
- Record the character count next to each answer (`(1,180 chars)`) so the fill phase can verify
  the paste landed whole.

For narrative / behavioral questions, pick with `python bin/jobkit.py qa list`, then pull only
the chosen one or two with `python bin/jobkit.py qa get "<substring>"`. **Never read
`qa-bank.md` whole.** Use only ONE or TWO of the most fitting stories per question; never list
every project.

### 7a. Cover letter (on request only)
Skip unless the user asks for one on that run. When asked: write `cover-letter.tex` in the
application folder at **250–400 words (1,500–2,400 characters)**, same factuality and voice
rules as the résumé, then compile to `cover-letter.pdf` with tectonic. Never leave it as
tex-only: some ATSes require a PDF.

### 8. (The checkpoint belongs to the orchestrator. Go straight to 8b.)

---

### 8b. `form-pack.md` — generated, then completed
The fill phase reads **only this file**. Do not write it by hand.
```
python bin/jobkit.py formpack "<application-folder>" --company "<C>" --role "<R>" \
  --url "<resolved apply URL>" --platform <platform> --source "<referral source>" \
  --pay "<published band or none>" --posted "<posting date line>"
```
Run it **after** the final compile + `atsfix`. It writes the header, the platform playbook,
identity, locked fields, defaults, education, certification, languages, transcripts, the
work-experience entries exactly as they stand on the PDF, and the raw form schema.
`FORMPACK_FAILED …` means the résumé layout no longer parses or the PDF is stale: fix the cause
(usually recompile) and re-run; only if it still fails, write the pack by hand in the same layout.

Then open `form-pack.md` and replace its two `<!-- PREP AGENT … -->` markers, nothing else:
- **FILL PLAN** (only when the pack contains a schema): an ordered `field key → value` list,
  every dropdown answer matched to the schema's own option strings, fields needing a real click
  flagged, name fields per the legal-name rule. No schema → the script already wrote
  `NO SCHEMA — DOM path`. **Never invent a fill plan.**
- **Screener answers**: `screener-answers.md` verbatim, character counts included.
Add a short `## Notes for this posting` section only for what the script cannot know: a pay band
outside <salary range>, a posting-specific yes/no ("previously worked at <Company>?" is already
No), an unusual required upload.

### 8c. Return to the caller
The return format is fixed in your agent definition. Nothing else: everything else is on disk.
