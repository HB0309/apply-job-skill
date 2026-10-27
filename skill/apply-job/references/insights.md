# `/apply-job insights` — what's converting

**Run `python bin/jobkit.py insights`.** It aggregates every tracker row into two fixed-size
tables (~600 bytes) regardless of corpus size. Reading `tracker.md` and the match-reports directly
costs more than one context window.

The script counts only rows in the closed vocabulary: sent = `applied viewed oa interview offer
rejected withdrawn`; reply = `viewed oa interview offer`; reject = `rejected withdrawn`. It prints
sent / reply / reject / pending and the reply rate **by role type** (security, SWE, ML/AI,
data/analyst) and **by source** (Handshake, Jobright, LinkedIn, Indeed, <Project B>, direct).
A third table splits by **résumé variant** (`rv=` token in Notes; rows without one are v1).
Compare variants only once the newer one has ~150 sent rows; below that, say it is too early.

From those tables, report the findings they support, strongest first, each with its evidence and one concrete change
("<Project B> candidates got 3/17 replies vs 1/62 from Jobright — prioritise the sweep queue over
Jobright scans").

**Be honest about sample size.** The script prints `SAMPLE TOO THIN` below 15 known outcomes;
then report only tentative observations. Never invent a pattern from 5 data points.

Only open an individual `match-report.md` if a specific finding needs the detail — never sweep
them all.
