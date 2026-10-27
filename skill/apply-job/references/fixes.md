# Fixes — `/apply-job fixes`

Turns the failure log into edits of the skill. Loaded only by this mode. It never applies to a
job and never opens the browser.

The log is `<WORKSPACE>\failures.md`, written during runs by
`jobkit fail add` (SKILL.md hard rule 8). Each entry is one thing the skill should have
prevented: `## F-0007 · <date> · <phase> · <where> · open|fixed|wontfix`, then what happened,
what was expected, the workaround, a suggested fix, and `Seen: Nx` when it recurred.

## Procedure

1. `python bin/jobkit.py fail list` — open entries only. `0 open entries` → say so and stop.
2. **Group before fixing.** Entries that share a `where` (one platform, one jobkit command, one
   skill file) usually share a cause; fix the cause once. Order the groups by `Seen` count, then
   by severity: an unexpected auto-submit or a shipped wrong value outranks a slow widget.
3. **Find the root cause in the file the entry names** — read only that file (`ats\<platform>.md`,
   `references\fill.md`, `references\tailoring.md`, `form-data.md`, `bin\jobprep.py`, …). The
   entry's "Suggested skill fix" was written mid-run by a model under time pressure: treat it as
   a lead, not a spec. If the workaround worked, the fix is usually to make the workaround the
   documented method.
4. **Show the user the plan before editing anything**: one line per group — entries covered, the
   file, the change. Wait for their go-ahead. They may mark entries wontfix.
5. Apply the edits. Rules:
   - A platform quirk goes in that platform's `ats\<platform>.md`; a new platform seen twice gets
     its own playbook (per `ats\_unknown.md`). Cross-platform mechanics go in `fill.md`.
   - A missing stored answer goes in `form-data.md`, in the table `jobkit formpack` copies —
     ask the user for the value, never invent it (hard rule 1).
   - A script bug gets fixed in `bin\` and re-tested against the folder the entry names.
   - Fix the instruction that misled, do not add a second one that contradicts it. Keep edits
     short: every added line is read on every run.
   - Never edit `master\` files or `bases\`.
6. Close each entry: `python bin/jobkit.py fail close F-0007 --note "<file changed + one line>"`,
   or `--wontfix --note "<why>"`. An entry is closed only when the fix is actually in the file.
7. Add one dated paragraph to `references\changelog.md` (what failed, what changed, entry ids).
8. Tell the user which files changed, remind them that edits to `agents\apply-job-prep.md` or
   `agents\apply-job-fill.md` need a new session, and offer to commit the changed skill files if the skill folder is under version control.

`python bin/jobkit.py fail list --all` shows closed entries too — use it when a failure looks
familiar, to check whether an earlier fix did not hold.
