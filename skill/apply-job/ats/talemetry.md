# Talemetry ATS

Detection: URL is `apply.talemetry.com/application/<uuid>`, reached by clicking "Apply Now" on
a company's own careers page (e.g. `careers.creditonebank.com`). Modal-style 7-step wizard,
progress bar reads "STEP N OF 7".

## Page sequence (Credit One Bank instance; step count/labels may vary by employer)
1. Résumé source picker — Upload a Resume/CV / Build My Resume / LinkedIn / Dropbox / OneDrive.
   Use the file upload option; `find` the file input (it's a hidden `type="file"` button).
2. Applicant Information — auto-advances through THREE sub-stages after résumé upload/parse,
   all still labeled "Step 2 of 7" with their own inner progress bar: Contact Details -> Work
   History -> Education History. Uploading a résumé auto-parses name/email/phone AND full work
   history (title, company, dates, description bullets) AND education (school/degree/major) —
   often correctly, but SKILL.md rule 9b applies: **open every parsed entry via EDIT, overwrite
   every field from `form-pack.md` including the full description, and verify field-by-field**,
   not just the summary card. A card showing "Requires Attention" in red under an entry means
   a required field failed to parse — always fix these before Next will let you proceed.
3. Race & Ethnicity (EEO) — Gender / Hispanic-or-Latino / Race (race field only appears after
   answering Hispanic=No) / Your Name / Today's Date (name+date usually pre-filled correctly).
   Page text says "This is the final page of the application" — this is generic boilerplate,
   NOT actually the last step. Ignore it and click Next as normal.
4. Voluntary Self-Identification of Disability (CC-305 boilerplate) + Your Name + Today's Date.
5. Protected Veteran Classification (VEVRAA boilerplate) + Your Name + Today's Date.
6. Job-Related Questions — work authorization, age 18+, prior employment, background-check
   consent, visa sponsorship (combined now-or-future, standard Yes/No), desired salary (free
   text), referral, relatives, and a SECOND separate "Veteran Status" dropdown (more granular
   options: Not a Veteran / Disabled veteran / etc — pick "Not a Veteran" for consistency with
   step 5's answer). This step is long; scroll and re-read the page after every batch of edits.
7. Final Review and Submission — literally just Back / Submit / Cancel buttons and a thank-you
   paragraph. This is the real last page. **Never click Submit.**

## Quirks
- **Custom `<select>` dropdowns whose `form_input` succeeds but the value visually reverts to
  blank on next render** (seen on Education's Start/End Year+Month selects). `form_input`
  reports success but the underlying React state doesn't actually update from the tool's
  synthetic set. Fix: use a `javascript_tool` call with the native property setter + dispatch
  both `input` and `change` events:
  ```js
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;
  setter.call(selectEl, optionValue); selectEl.dispatchEvent(new Event('input',{bubbles:true}));
  selectEl.dispatchEvent(new Event('change',{bubbles:true}));
  ```
  This worked reliably for the Year/Month selects. It did NOT reliably work for plain text
  `<input>` fields on this platform (Degree/Major reverted after clicking Done) — for those,
  use a real `computer` click + `type` instead (triple-click to select-all before retyping).
- **Typing into one text field on Step 6 can silently reset an unrelated dropdown on the same
  page** (observed: filling the sponsorship "if yes, please explain" textarea reset the
  separate "Are you able to perform all requirements..." dropdown back to blank/required).
  Always re-screenshot and re-verify every dropdown on a step after typing into any free-text
  field on that same step, before clicking Next.
- Hidden auto-resize helper `<textarea>` elements with no `id`/`name` and literal value `"x"`
  sit alongside every real textarea on Step 6 — a naive `querySelectorAll('textarea')` read-back
  will pick these up. Filter to elements with a non-empty `id` when reading textarea values back.
- The Country dropdown lists Canada/UK/US first (out of alphabetical order) then the rest
  alphabetically — same pattern likely appears on other Talemetry-instance forms.
- Free-text School/Major/Degree fields (no closed list) — a non-US university
  entered cleanly here, unlike Greenhouse's closed school-picker.
