# ATS quirks & troubleshooting

Per-platform detail lives in `ats/<platform>.md`. This file holds the cross-platform failure modes.

- **Oracle CX auto-submit risk — see fill.md 9.4.** A click that looks like ordinary form navigation can be the actual submit action there, with no separate confirm step. Verify page state after every click on Oracle CX and unfamiliar ATSes.
- **JS-rendered forms (Ashby, Greenhouse embeds, Workday) — VERIFY, don't trust the clicks (learned 2026-07-29, Crusoe).** On these forms, coordinate-based `computer` click+type and radio/toggle clicks can silently fail: the page auto-scrolls between screenshot and click, so typing lands nowhere and radio picks hit the wrong option. Symptoms: fields look filled in one screenshot but are empty/wrong on submit; a required Name/Email came out blank; a radio landed on the wrong choice (e.g. Race = White instead of Decline). **Before handing off, verify the true field state with `__rbCheck`** (fill.md 9.0), never from a screenshot. To FIX React-controlled inputs, set them via the native setter and fire events, not by typing:
  `const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; s.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));`
  For custom radios/toggles use `el.click()` on the backing `input`, or read the active toggle by computed `backgroundColor`. Prefer `read_page`→`form_input`(ref) where refs are exposed; fall back to JS when they are not. Never report a form "filled" from screenshots alone on these sites.
- Tectonic "Fontconfig error" lines are non-fatal noise — ignore unless the PDF fails to produce.
- If the master uses `fontspec` with a system font Tectonic can't find, tell the user which font and stop — don't swap fonts silently.
- If a form field type defeats `form_input`, try the computer tool (click + type). If a site blocks automation entirely, return `BLOCKED` naming the site; `form-pack.md` already is the copy-paste pack for the user.
- **LinkedIn Easy Apply (`openSDUIApplyFlow=true` on the Apply link) cannot be filled.** It is
  LinkedIn's default Easy Apply flow. The modal renders inside a Shadow DOM host (`#interop-outlet`)
  that `read_page` and `find` do not traverse, so `file_upload` and `form_input` have no ref;
  `javascript_tool` can read `host.shadowRoot` but cannot upload a file, and a JS click on the wrong
  shadow-root button is an unverified submit. Return `BLOCKED` ("LinkedIn Easy Apply: the user submits
  the tailored PDF by hand"). Prep runs normally and notes the block in `form-pack.md`
  (tailoring.md 8b). If `read_page` / `find` gain shadow-DOM support, re-test before relying on this.
- **SmartRecruiters oneclick-ui** (Angular web components in shadow roots): workable, see
  `ats/smartrecruiters.md`.
