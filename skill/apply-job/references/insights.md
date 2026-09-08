# `/apply-job insights` — what's converting

**Run `python bin/jobkit.py insights`.** It aggregates every tracker row into two fixed-size
tables (~600 bytes) regardless of corpus size. Reading `tracker.md` and the match-reports directly
costs more than one context window, which is why this mode did not work before 2026-08-21.

The script counts only rows in the closed vocabulary: sent = `applied viewed oa interview offer
rejected withdrawn`; reply = `viewed oa interview offer`; reject = `rejected withdrawn`. It prints
sent / reply / reject / pending and the reply rate **by role type** (security, SWE, ML/AI,
data/analyst) and **by source** (Handshake, Jobright, LinkedIn, Indeed, job-matcher, direct).
The old "top-third framing" table was dropped 2026-09-08: framings are free text that never
repeat, so the table had 4 sends per row at best and could not support a finding.

From those tables, report **at most 3 findings**, each with its evidence and one concrete change
("job-matcher candidates got 3/17 replies vs 1/62 from Jobright — prioritise the sweep queue over
Jobright scans").

**Be honest about sample size.** The script prints `SAMPLE TOO THIN` below 15 known outcomes;
then report only tentative observations. Never invent a pattern from 5 data points.

Only open an individual `match-report.md` if a specific finding needs the detail — never sweep
them all.
