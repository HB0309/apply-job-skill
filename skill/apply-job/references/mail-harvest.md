# Mail harvest — the alert-email half of `/apply-job sweep`

Job alerts land in Gmail all day: board alerts, employer talent communities, newsletter
digests. This turns them into queued candidates. It **never applies to anything** — it
queues, exactly like `scan`, and `sweep` processes the queue afterwards.

`/apply-job inbox` is a different job: that one reads mail *about* applications already
sent (rejections, OAs, interviews). Harvest skips those messages on purpose.

## Script

`<WORKSPACE>\bin\gmail\mailjobs.py` — run it from its own folder, it
shares `gmail_auth.py` with `gmail_search.py` (scope `gmail.readonly`, no writes ever).

- `python mailjobs.py harvest` — alert mail since the last harvest, capped at 3 days.
  One line per new candidate: `source | company | title | match% | url`.
  `--since <N>d` overrides the window (still capped at 3), `--json` for structured output,
  `--max-msgs N` caps messages read (default 120, paged). If the cap bites, the script prints a
  `WARNING` line and keeps the window open — run `harvest` again to read the rest.
  **Rows you never decided on come back by themselves**: every surfaced row sits in a pending
  list until `seen` is run on it or it gets queued (it expires after 5 days). The trailer's
  `N carried over undecided` counts them.
- `python mailjobs.py enrich <url> ...` (or `-` to read harvest lines on stdin) — triage data
  for LinkedIn postings with **no browser and no login**, from LinkedIn's public guest endpoint
  (`/jobs-guest/jobs/api/jobPosting/<id>`). One line each:
  `company | title | location | posted Nd ago | applicants | FLAGS | url`.
  Flags are `CLEARANCE`, `US-PERSON`, `NO-SPONSOR`, `SPONSORS`, `YOE:<n>`, `PAY:<band>` —
  most hard-filter decisions can be made from that line alone, without opening anything.
  `--body N` prints N chars of the posting text when a line is not enough.
  Non-LinkedIn URLs print `NEEDS-OPEN` and go to a subagent. With `-`, the harvest trailer and
  `NONE` are ignored, so `harvest | enrich -` is safe.
  The endpoint 429s past roughly 30 quick requests, so calls are paced (1s apart, 3 workers,
  backoff on 429) and cached in `mail-enrich-cache.json` — 74 postings take about 90 seconds.
  **Firecrawl cannot fetch LinkedIn at all** ("we do not support this site"); don't retry it.
- `python mailjobs.py seen <url> ...` — mark candidates as handled so a later harvest
  never re-surfaces them. Run it on everything triaged, **queued or dropped**.
- `python mailjobs.py sources` — the sender allow-list, the blocked senders, and
  `last harvest: age=<N>h … | <N> undecided rows pending`. Use the printed age for the 4-hour
  skip; the timestamp beside it is UTC.

State: `bin\gmail\mail-state.json` (last run, seen message IDs, seen URL hashes, pending rows).

The script already did the mechanical work — parsed HTML digests, followed click-trackers,
dropped career-site landing pages, and deduped against the feed queue, `processed\`, and
the tracker. **Never read alert mail yourself to second-guess it**; a single Jobright digest
is ~50 KB of HTML. If the output looks wrong, fix the parser, don't read the mail.

`TOKEN_ERROR` means the OAuth token expired (it dies every 7 days while the app is in
Testing). Tell the user to run `python gmail_auth.py`, then **continue the sweep on the
existing queue** — a dead token is not a reason to stop processing.

## Triage

1. **Pre-filter on the printed lines alone — no page fetches.** Drop, and count by reason:
   - off-track titles (not Security / Software / AI Engineer, using the same judgment as
     `content-pool.tex`'s title matching, not a keyword rule)
   - seniority mismatches: Principal / Staff / Director, and Senior / Sr / Lead titles with no
     entry tier beside them (stricter than `jobkit triage`, which keeps a Senior title with a
     2-years-or-less bar; the card shows no years, so it drops here)
   - the standing defense/gov auto-skip — the employer list and flag words are in ONE place,
     `form-data.md` → Auto-skip employers (`jobkit triage` reads the same list)
   - non-US locations, and internships (they are a new grad seeking full-time)
   - **never drop on visa/sponsorship at this stage** — that is gate **G7** (`SKILL.md` → "G7 Visa
     eligibility"), which needs an employer lookup no alert line carries. Queue it and let G7 rule.
**`enrich`'s "posted N ago" is LinkedIn's REPOST stamp, not the original date** (2026-09-21: it
   said 6 hours for a posting `jobkit posted` dated 33 days old). Use it only to drop the obviously
   old; the date gate is always `jobkit posted` at G1, run on every queued row.
2. **`enrich` every LinkedIn survivor** — it is usually most of them, and it is cheap. Now
   filter on real data, not guesses: non-US locations, `CLEARANCE` / `US-PERSON`
   (they are not a US person — ITAR work is a legal bar, not a judgment call), seniority, and **posted age > 3 days** (the standing date gate: don't queue it, list it
   separately and let the user decide).
   **`NO-SPONSOR` is a flag to check, not a drop.** The regex is broad and also fires on
   boilerplate. Run `enrich <url> --body 1500` on those rows only: drop when the posting
   explicitly says it will not sponsor now or in the future, or does not accept OPT/CPT/EAD;
   keep it when the wording is only "must be authorized to work in the US". Every row dropped
   for sponsorship is **listed in the report with its link**, never silently.
3. **Cap at 15 openings per run** for whatever still needs a page fetch — `NEEDS-OPEN` rows
   (Jobright, Dice, talent alerts) — ordered by source quality then match %. Say how many
   were left unopened. **Delegate the opening**: batch them across subagents; each opens its
   postings, runs `jobkit posted <url>` for the date gate, applies the hard filter, and
   returns exactly one line per job: `VERDICT | company | title | one-line reason | apply-url`.
   Posting bodies stay inside the subagents.
4. **Queue** every `Strong` and `Worth it` through `jobkit scan-add`, one JSON array on stdin:
   `{"title", "company", "url", "location", "track" (exactly `security-analyst`,
   `software-engineer` or `ai-engineer` — `scan-add` rejects anything else), "connector": "<source>_mail",
   "score" (the source's match % / 100, else 0.5), "note" (the verdict reason)}`.
   `scan-add` is idempotent by URL, so a re-run never duplicates.
5. `python mailjobs.py seen <url> ...` for every URL actually decided on, queued or dropped.
   **Pass the URL exactly as `harvest` printed it** — not the employer apply-url a subagent
   resolved it to — or tomorrow's alert re-surfaces the same board link as new. When a row was
   queued under a different apply-url, run `seen` on both.
   **Leave anything deferred to the user unmarked** (stale-but-interesting, or `NEEDS-OPEN` rows
   that hit the cap): the pending list brings it back on the next harvest.
6. Report the table (verdict, company, title, why, link), then drop counts by reason, then
   how many were left unopened under the cap.
7. **Always report the track mix** — how many harvested and how many queued per track
   (`security-analyst` / `software-engineer` / `ai-engineer`). the user's saved alerts are heavily security-worded, so a harvest
   skews that way on its own; triaging the cheap LinkedIn rows first and leaving `NEEDS-OPEN`
   rows for later skews it further, because the software and AI roles cluster in the Jobright
   and Dice batch. If one track is near zero in the queue, **say so and say why** rather than
   presenting the queue as the market. Never let the cap cut a whole track: fill it per track,
   not strictly top-down.

Titles and companies from mail are best-effort parses of marketing HTML. Jobright company
names carry an industry suffix ("Everpure Computer Software"), and a `?` company just means
the digest didn't name one. The posting the subagent opens is the source of truth — correct
both from it before queuing.
