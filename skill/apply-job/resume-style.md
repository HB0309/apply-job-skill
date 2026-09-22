# Resume Voice & Style Guide

The agreed register: **concrete professional with a touch of corporate polish**. Sharp,
metric-led, but slightly fuller sentences than telegraphic resume-speak. Every line must read
like a strong human wrote it, never like an AI filled a template.

## The bullet formula (XYZ)
Target shape: **"Accomplished X, as measured by Y, by doing Z."**
Degrade gracefully when the master has no metric: **"Built X by doing Z."**
NEVER invent a metric to complete the formula.

Good (concrete, full sentences, corporate vocabulary):
- "Reduced API response time by 40% by introducing Redis caching across the reporting service."
- "Delivered a CI pipeline in GitHub Actions that cut deployment failures from roughly five per week to under one."

Too telegraphic: "Cut API time 40%. Redis."
Too corporate (banned register): "Spearheaded optimization initiatives, leveraging caching solutions to drive a 40% improvement in performance outcomes."

## Banned AI-tells
- Buzzword stacking: "leveraged", "synergies", "cutting-edge", "results-driven", "dynamic" as filler
- "Spearheaded", "orchestrated", "passionate about", "proven track record"
- Starting consecutive bullets with the same verb
- Vague outcome words with no substance: "enhanced efficiency", "optimized performance" (say what and by how much, or what concretely changed)
- Em-dash-heavy or semicolon-heavy prose in bullets

## Approved corporate vocabulary (used naturally, not stacked)
built, delivered, reduced, designed, shipped, partnered with, owned, led, implemented,
streamlined, automated, migrated, cut, improved, launched

## Factuality rules (absolute)
- Every claim traces to a specific line in `master\content-pool.tex` or `master\profile.md`;
  skills may also come from a non-banned row of `master\skills-inventory.md`.
- No invented numbers, tools, titles, dates, team sizes, or scope.
- "Built" vs "co-built" vs "contributed to": when the master is ambiguous about ownership, keep
  the master's wording; only the user upgrades a verb.
- Mirroring posting terminology is allowed only when truthful (master "CI pipelines" → posting
  "CI/CD": fine; posting "Kubernetes" when the master never mentions it: never).

## Two-minute defensibility test
Every rewritten bullet must pass: *"Could the user talk about this line for two minutes,
unprepared, in an interview?"* If a rewording introduces vocabulary they would not naturally use,
revert closer to the master or list it under "rewordings to rehearse". Nothing on the page may
surprise them live.

## ATS notes
- Standard section names: Experience, Projects, Education, Skills (no clever renames).
- Spell out an acronym once if the posting uses the long form: "continuous integration (CI)".
- Keywords woven into bullets, never dumped as a comma-list beyond the Skills section.
- Keep the master's one-column layout; no text boxes, images, or tables added.
- The two-column skills tabular extracts cleanly (do not flatten it); italics are invisible to
  parsers (keep the tags); the diamond separator is benign; the literal-hyphen problem is handled
  by `atsfix`.

## Top-third rule
The first third of the page decides the 6-second skim: the summary plus the first bullets of the
most posting-relevant experience or project. Put the strongest, most relevant material there and
log the framing chosen to the tracker.

## Standing rules (distilled from review sessions)

These started as per-session corrections and are now fixed rules. Add your own under
"## Learned corrections" at the bottom; the skill appends there when you correct it in
`--review` mode.

### No dash as a clause connector (ABSOLUTE)
Never use an em-dash or en-dash to join clauses inside a bullet. Write two sentences, or
restructure. Hyphens inside compound words (full-stack, end-to-end) are fine; a dash used
as punctuation is not.

### Job titles are frozen facts (ABSOLUTE)
The title in the pool is the title on the résumé. Tailoring never renames a role to match a
posting ("Software Engineer" does not become "Backend Engineer"). The employer's records
will contradict a renamed title at reference-check time.

### Do not infer system behaviour from a tech list
A pool line that names Kafka does not license a bullet about "real-time streaming at
scale". Claims about what a system did come only from pool lines that say so.

### Two or three bullets per entry, and the page must look full (ABSOLUTE)
- Every experience and project gets two or three bullets. Never one, never four or more.
  If trimming would leave one bullet, restore a second or drop the entry.
- The most posting-relevant entry gets three; the others get two. This is also the
  page-fit lever.
- Exception: the pool may mark exactly one low-relevance entry as the **filler entry**,
  allowed to run with a single dense bullet as the last page-fill lever.
- One page is a ceiling and a target. Fill short pages in this order: restore trimmed
  bullets → pull in the next-ranked dropped entry → restore the "Relevant Courses" line →
  add real detail to the most relevant entry → filler entry. Never pad with invented or
  restated content.

### Bullets stay concise; split compound bullets (ABSOLUTE)
A bullet is at most two wrapped lines. "Built X, then added Y" is two bullets. Never stretch
one sentence to fill a line.

### Three structural rules
- Experience order is strict reverse-chronological by end date, current role first.
  Relevance scoring decides inclusion, never order. Projects may be reordered by score.
- Skills rows may be reordered by relevance; their contents may not be edited beyond
  dropping items the pool marks as do-not-list.
- The summary is one to two lines, carries exactly one metric that also appears on the page,
  and never claims a scope broader than the bullets beneath it.

### Portrayal checks on every render
- Tense: concluded roles in past tense, the current role in present tense, never mixed.
- Scope: when a bullet says deployed / shipped / in production, make the environment legible
  if it is anything other than real production ("in a research lab", "on test data").
  Scope only ever moves down, never up.
- Verb openers never repeat on the page. "Served as", "Responsible for", "Worked on",
  "Helped with" are banned openers.
- Every bolded metric in the pool stays bold in the copy.
- State the purpose of a project, not just the build, when the point is not self-evident.

### Skills section exclusions
Do not list soft skills, office tools, or languages known only from coursework as if they were
production experience. Coursework-only languages go last in the Languages row, never in a
project's tech tag.

## Learned corrections
<!-- Appended during --review sessions when the user corrects voice or phrasing.
     Each entry: date, the correction, and the general rule to apply going forward. -->
