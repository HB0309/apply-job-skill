# SmartRecruiters — playbook

**Detect:** `jobs.smartrecruiters.com/<org>/<id>`, `careers.smartrecruiters.com` · **10 applications**
**Auto-submit risk:** low. **No schema API confirmed — DOM path.**

**Two different templates exist — check the URL before picking a method:**
- Classic template (the 6 prior successful applications) — standard DOM path below works.
- **`.../oneclick-ui/company/<org>/publication/<id>` — WORKABLE via shadow-DOM walk
  (revised 2026-09-07, Zoro; supersedes the 2026-09-05 Versant "BLOCKED" verdict).**
  A newer Angular template built entirely from SmartRecruiters' "SPL" web components
  (`SPL-INPUT`, `SPL-FORM-FIELD`, `SPL-DROPZONE`, …), each with its own Shadow DOM — the Zoro
  posting measured **1,814 shadow hosts** and exposed only **1** light-DOM input.
  `read_page`/`find` see almost nothing, which is what produced the original verdict.

  **But `javascript_tool` reaches everything with a recursive walk.** Collect the real controls:
  ```js
  const all=[];function walk(r){r.querySelectorAll('*').forEach(e=>{
    if(e.shadowRoot)walk(e.shadowRoot);
    if(/^(INPUT|TEXTAREA)$/.test(e.tagName))all.push(e)})}
  walk(document);
  // label comes off the SPL host element, not the input:
  const key=e=>{const h=e.getRootNode().host;
    return (h&&h.getAttribute('label'))||e.getAttribute('aria-label')||e.placeholder||''};
  ```
  Set values with the native setter, and dispatch events with **`composed:true`** so they cross
  the shadow boundary (plain `bubbles:true` alone does not reach the Angular handler):
  ```js
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v);
  ['input','change','blur'].forEach(t=>
    el.dispatchEvent(new Event(t,{bubbles:true,composed:true})));
  ```
  Read back through the same walk. Zoro's page-1 keys were: `First name`, `Last name`, `Email`,
  `Confirm your email`, `City`, `Phone number`, `LinkedIn`, `Facebook`, `X (fka Twitter)`,
  `Website`, `Let the company know about your interest working there`.

- **The one thing that stays blocked: the résumé upload.** The file input lives inside
  `SPL-DROPZONE`'s shadow root, and `file_upload` needs a `read_page` ref, which cannot address
  a shadow node. JS cannot set a file input, and clicking the dropzone opens a native picker.
  **Hand the user the browser for the résumé only**, then take back over — and since the upload
  parses into Experience/Education, verify those per rule 9b afterward.

## Method (classic template only)
Standard DOM path: one `read_page(filter:"interactive")`, one `browser_batch` of `form_input`
calls, one JS read-back. Single-page form in most tenants.

## Quirks
- Offers "Apply with LinkedIn / Indeed" — **ignore those**, use the manual form.
- Resume upload may auto-parse into the experience fields. SKILL.md rule 9b: enter every entry
  from `form-pack.md` regardless, in PDF order, and re-read every full description after the
  page commits.
- Consent/GDPR checkbox is common at the bottom — this is an "accept terms" action, so
  surface it to the user rather than ticking it silently.
- Location is usually a plain text input, not an autocomplete.

## Known question → answer mappings
| Question contains | Answer |
|---|---|
| "authorized to work" | Yes |
| "require sponsorship" | Yes |
| "How did you hear" | the job board the link came from (hard rule 7: Handshake / Jobright / LinkedIn / Indeed / …), else Company website |
