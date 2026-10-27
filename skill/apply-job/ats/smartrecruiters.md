# SmartRecruiters — playbook

**Detect:** `jobs.smartrecruiters.com/<org>/<id>`, `careers.smartrecruiters.com` · **10 applications**
**Auto-submit risk:** low. **No schema API confirmed — DOM path.**

**Two different templates exist — check the URL before picking a method:**
- Classic template (the 6 prior successful applications) — standard DOM path below works.
- **`.../oneclick-ui/company/<org>/publication/<id>` — workable via a shadow-DOM walk.**
  A newer Angular template built entirely from SmartRecruiters' "SPL" web components
  (`SPL-INPUT`, `SPL-FORM-FIELD`, `SPL-DROPZONE`, …), each with its own Shadow DOM — the Zoro
  posting measured **1,814 shadow hosts** and exposed only **1** light-DOM input, so
  `read_page`/`find` see almost nothing.

  **`javascript_tool` reaches everything with a recursive walk** — use it to find and read back
  the real controls:
  ```js
  const all=[];function walk(r){r.querySelectorAll('*').forEach(e=>{
    if(e.shadowRoot)walk(e.shadowRoot);
    if(/^(INPUT|TEXTAREA)$/.test(e.tagName))all.push(e)})}
  walk(document);
  // label comes off the SPL host element, not the input:
  const key=e=>{const h=e.getRootNode().host;
    return (h&&h.getAttribute('label'))||e.getAttribute('aria-label')||e.placeholder||''};
  ```
  **Type every field with real keystrokes** (`computer` click + type). A native-setter value
  renders in the input but never reaches the Angular form model, so Save/Next reports "Title is
  required" on fields that visibly hold text (ServiceNow). For the `SPL-INPUT` combobox fields
  (Title, Company, Office location, City, Institution) click the suggestion row that appears
  ~45px below the field — typing alone does not commit them. Other traps:
  - **`SPL-DATE-PICKER` (month-year):** type `YYYY-MM-DD`, then click the month cell in the popup
    that opens. The popup's year header does NOT follow what you typed — step it with the
    prev/next-year arrows first. Re-open the field to confirm the right month is highlighted.
  - **Experience/Education lists stack newest-added ON TOP.** There is no reorder control, so add
    entries in REVERSE PDF order (oldest first) to end up with PDF order on screen (rule 9b).
  - Screenshots go flaky mid-run (`Page.captureScreenshot` timeouts, changing scale). Get click
    coordinates from `getBoundingClientRect()` after `scrollIntoView` instead of from a screenshot.

  Zoro's page-1 keys were: `First name`, `Last name`, `Email`,
  `Confirm your email`, `City`, `Phone number`, `LinkedIn`, `Facebook`, `X (fka Twitter)`,
  `Website`, `Let the company know about your interest working there`.

- **The one thing that stays blocked: the résumé upload.** The file input lives inside
  `SPL-DROPZONE`'s shadow root, and `file_upload` needs a `read_page` ref, which cannot address
  a shadow node. JS cannot set a file input, and clicking the dropzone opens a native picker.
  **Return `BLOCKED` for the résumé upload BEFORE filling anything** (the session expires if
  it waits mid-form), then take back over in resume mode — and since the upload
  parses into Experience/Education, verify those per rule 9b afterward.

## Method (classic template only)
Standard DOM path: one `read_page(filter:"interactive")`, one `browser_batch` of `form_input`
calls, `__rbCheck`. Single-page form in most tenants.

## Quirks
- Offers "Apply with LinkedIn / Indeed" — **ignore those**, use the manual form.
- Resume upload may auto-parse into the experience fields. fill.md 9b: enter every entry
  from `form-pack.md` regardless, in PDF order, and re-read every full description after the
  page commits.
- Consent/GDPR checkbox is common at the bottom — tick it and list it in the handoff
  (fill.md, Consent checkboxes); leave marketing opt-ins unticked.
- Location is usually a plain text input, not an autocomplete.

## Known question → answer mappings
| Question contains | Answer |
|---|---|
| "authorized to work" | Yes |
| "require sponsorship" | Yes |
| "How did you hear" | the job board the link came from (hard rule 7: Handshake / Jobright / LinkedIn / Indeed / …), else Company website |
