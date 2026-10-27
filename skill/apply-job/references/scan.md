# Scan mode — loaded only by `/apply-job scan`

Hard rules 1-8 are in SKILL.md. The eligibility rules are SKILL.md -> G6; the employer list is
`form-data.md` -> Auto-skip employers.

## Scan flow: `/apply-job scan`

Three sites (Handshake, Jobright, LinkedIn) offer their own "recommended for you" / "top
applicant" pages that <Project B>'s connectors can't reach — they need the user's real logged-in
session, not a public API. This mode uses claude-in-chrome with their already-logged-in browser
to read those pages and queue anything that's a plausible fit, same downstream queue as sweep.

**URLs:** `references\scan-sources.md` (config — edit there when the user gives new ones).

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
   - Drop seniority mismatches: Principal / Staff / Director, and Senior / Sr / Lead titles
     with no entry tier beside them (the user rejected 16 of 16 of these, 2026-09-20).
   - Drop what the card itself shows as a bar: "no sponsorship", "US citizens only", or a
     stated 3+ years of experience (their M.S. covers a requirement of up to 2). Anything the
     card does not show is left to `jobkit triage`, which applies the same rules to the text.
   - **Do NOT filter on the employer's sponsorship record here** (a card that itself says "no
     sponsorship" is dropped above). The record is gate **G7** (`SKILL.md` → "G7 Visa
     eligibility"), which needs an employer lookup no job card carries. work visa filing history at entry
     level is what decides it; E-Verify is recorded but never vetoes. Queue the posting and let G7 rule.
   - **Apply the user's standing defense/gov auto-skip** even at this stage — the employer list and
     the flag words live in ONE place, `form-data.md` → Auto-skip employers. For an applicant who is not a US Person, ITAR-restricted work is a legal bar, not a per-posting judgment call. Edit the list to your situation.
4. For each kept job, pipe a JSON array into `jobkit.py scan-add` (one call per site is fine):
   `{"title", "company", "url", "location", "track" (exactly `security-analyst`,
   `software-engineer` or `ai-engineer` — anything else is rejected), "connector": "<site>_live", "score" (0-1,
   the site's own match % if it shows one, else a reasonable estimate), "note" (why/site context)}`.
   `scan-add` is idempotent by URL hash — safe to re-run without duplicating.
5. Report: how many found per site, how many queued, how many dropped and why (auto-skip vs.
   seniority vs. off-track) — same terse style as sweep's summary.

**This mode never applies to anything itself** — it only queues. Processing still happens via
`/apply-job sweep`, with the same hard filter, tailoring, and factual audit as any other link.
