# Prep brief — the variable block sent to each prep subagent

Everything static (hard rules, canonical facts, tool rules, the return format) lives in the agent
definition, `<agents folder>\apply-job-prep.md`. **Never paste rules into the
prompt** — the prompt is only the block below, filled in. Launch one per surviving link, all in
one message, as `subagent_type: "apply-job-prep"`; never `general-purpose`, never a `model`
override.

If the `apply-job-prep` agent type is not available in the session, STOP and tell the user — do not
fall back to another agent type, because the rules would not travel with it.

```
POSTING: <link exactly as given>
Company: <C> | Role: <R> | Location: <L> | Platform: <P>
Apply URL: <from jobkit meta, else same as the link>
Folder: <WORKSPACE>\applications\<folder from jobkit meta, else "create per tailoring.md step 1">
job-posting.md: <"written by jobkit meta" | "NO_META — fetch it yourself">
Posted: <YYYY-MM-DD (N days ago), confidence X | unknown> — <gate note, e.g. "STALE, the user said apply anyway">
Referral source: <Handshake | Jobright | LinkedIn | Indeed | <Project B> | direct>
Published pay: <band | none>
Triage: <PASS | the UNSURE lines and what the orchestrator decided | "--force: the user overrode a skip, do not re-argue">
Visa: <t1-both | t2-h1b — NO E-VERIFY, work-authorization extension cannot be filed here, flag it in the step-9 handoff | unsure | "--force: the user overrode a G7 skip">
Extra: <<Project B> score, --fresh, cover letter requested, anything else>
```
