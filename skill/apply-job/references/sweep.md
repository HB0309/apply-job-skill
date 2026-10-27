# Sweep mode — loaded only by `/apply-job sweep`

Hard rules 1-8 and the whole main flow (gates G1-G7, prep, fill, tracker) are in SKILL.md and
apply unchanged. This file is only the queue handling around them.

## Sweep flow: `/apply-job sweep [N]`

Two sources feed one queue: <Project B>'s scheduled exports, and job alerts sitting in Gmail.
A sweep harvests the mail first, then processes the merged queue.

**0. Mail harvest — `references\mail-harvest.md`.** Runs first on every sweep. Skip it,
silently, if the `last harvest:` line of `mailjobs.py sources` shows `age=` under `4.0h` (the
script prints the age; never work it out from the UTC timestamp), so a looped sweep doesn't
re-read the same mail. `N undecided rows pending` on that line means an earlier triage was cut
short — those rows come back on the next harvest, so do not skip the harvest when N > 0. Flags: `--no-mail` skips the harvest, `--mail-only`
harvests, triages, queues and reports, then **stops without applying to anything**. The
harvest only queues — nothing it finds bypasses the hard filter below.

A separate personal project (`<Project B>`, a job aggregator with its own LLM-based
matching) runs unattended every 3 hours across 3 resume tracks (Security, Software, AI
Engineer) and drops its pre-scored candidates into `job-matcher-feed\<track>\<date>\<job_id>.json`
via `bin\jobkit.py sweep-list` / `sweep-done`. This mode is a thin wrapper — <Project B> only
*finds and scores* candidates; every candidate still goes through the **exact same** tailoring,
factual-audit, and fill pipeline as a pasted link.

1. `python bin/jobkit.py sweep-prune` first — moves every candidate older than 3 days by the
   feed's own date (`posted_at`, else first-seen, else the feed folder date) into `processed/`
   so stale evergreen listings never occupy the top slots. Then
   `python bin/jobkit.py sweep-list --limit N` — one line per pending candidate, newest first,
   score as tie-break: `<job_id> | <track> | <company> | <title> | score=<0-1> | feed_age=<N>d | <url>`.
   `NONE` means nothing is queued — say so and stop.
2. Take those `N` (default 5) URLs and feed them into the **main flow in SKILL.md, unchanged** —
   gates G1–G7, parallel prep, one fill subagent per form, tracker row. **A `STALE` verdict stops and
   asks in a sweep exactly as it does for a pasted link** (standing rule): run G1 on
   all N links first, ask about every stale one in a single message with its link and age, and
   meanwhile carry on with the fresh ones. A stale link stays queued until they answer — yes →
   process it; no → log `skipped --notes "stale, declined"` and `sweep-done` it. <Project B>'s score is extra context for the prep
   subagent (pass it along, it's a useful signal), never a substitute for the hard filter or the
   factual audit — <Project B>'s matcher scores structurally, it does not read the posting.
3. After each link reaches a terminal state in the main flow (skipped, duplicate, held,
   blocked, stale-and-declined, or filled), run `python bin/jobkit.py sweep-done <job_id>` so it isn't picked up again next
   sweep. Do this **regardless of outcome** — a skip or duplicate is still a terminal state, not
   a reason to leave it queued. The one exception is a stale link the user has not answered yet.
4. Report same as the main flow's step-9 handoff, plus a one-line sweep summary: how many
   processed, how many filled/skipped/duplicate/stale, how many remain queued.
