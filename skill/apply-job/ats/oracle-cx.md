# Oracle CX (Oracle Recruiting Cloud) — playbook

**Detect:** `*.oraclecloud.com/hcmUI/CandidateExperience/...` · **9 applications**
**Auto-submit risk: CRITICAL. Session-expiry risk: CRITICAL.**

## ⚠ Two hard-won rules
1. **The flow can submit with no final Submit button.** A TI/edbz application submitted itself
   with no Submit ever shown. **Leave the last remaining required field empty and hand off**
   (fill.md 9.4): the user completes it and submits themselves.
2. **Idle expiry destroys the whole in-progress application.** Gather every answer BEFORE
   clicking Apply Now, then fill in one uninterrupted block. Do not stop mid-form to ask a
   question, harvest dropdown options, or confirm a value.

## Method
- Read `form-pack.md` completely before clicking Apply Now.
- No schema API for the form itself. Use the DOM path, but plan every value in advance.
- Verify page state after every click — confirmation text, URL change, fields vanishing.
- If a click advances further than a normal Next should, STOP: return `AUTO_SUBMITTED` if a
  confirmation shows, else `BLOCKED` with what happened.

## Quirks
- Often requires an account → login wall: return `BLOCKED` ("login wall").
- Multi-page with a progress rail; pages can silently merge.
- Some tenants re-render the whole form after each field blur; re-read refs rather than reusing them.
