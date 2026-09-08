# Oracle CX (Oracle Recruiting Cloud) — playbook

**Detect:** `*.oraclecloud.com/hcmUI/CandidateExperience/...` · **9 applications**
**Auto-submit risk: CRITICAL. Session-expiry risk: CRITICAL.**

## ⚠ Two hard-won rules
1. **The flow can submit with no final Submit button.** A TI/edbz application submitted itself
   with no Submit ever shown. **Hand the browser to the user BEFORE filling the last remaining
   required field** — let them complete and submit themselves.
2. **Idle expiry destroys the whole in-progress application.** Gather every answer BEFORE
   clicking Apply Now, then fill in one uninterrupted block. Do not stop mid-form to ask a
   question, harvest dropdown options, or confirm a value — this is a large part of why
   locked fields are now filled without confirmation (hard rule 4).

## Fetching the posting — no browser needed (found 2026-08-21, Akamai)
Oracle CX exposes the requisition over REST. Beats rendering the page in Chrome:

```
GET https://<host>/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails
    ?expand=all&finder=ById;Id=%22<jobId>%22,siteNumber=%22<site>%22
```
`<jobId>` and `<site>` come from the URL (`/sites/CX_1/job/3783` -> site `CX_1`, id `3783`).
Returns `items[0]` with `Title`, `PrimaryLocation`, `ExternalPostedStartDate`, and the full
`ExternalDescriptionStr` (HTML — strip tags and unescape entities). ~14KB.
Some tenants also populate `ExternalQualificationsStr` / `ExternalResponsibilitiesStr`.

This covers step 1 only. The **application form** still has no schema API — DOM path.

## Method
- Read `form-pack.md` completely before clicking Apply Now.
- No schema API for the form itself. Use the DOM path, but plan every value in advance.
- Verify page state after every click — confirmation text, URL change, fields vanishing.
- If a click advances further than a normal Next should, STOP and tell the user immediately.

## Quirks
- Often requires an account → login wall, hand over.
- Multi-page with a progress rail; pages can silently merge.
- Some tenants re-render the whole form after each field blur; re-read refs rather than reusing them.
