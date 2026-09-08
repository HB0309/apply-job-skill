# SAP SuccessFactors (career2.successfactors.eu / careers.<company>.com wrappers)

Detect: apply click on a hosted careers wrapper redirects to `career*.successfactors.eu/portalcareer?...`.
Seen at: Metso (2026-08-28).

## Page shape
One long single-page form, sections collapsed by default. Click **"Expand all sections"** first.
Sections: My Documents · Profile Information · LinkedIn Profile · Previous Work Experience ·
Formal Education · Certifications/licenses · Language Skills · Countries of Interest ·
Jobs of Interest · Job-Specific Information. Buttons at the bottom: **View Profile · Save · Apply**.
`Apply` is the submit — never click it.

## Walls
- Account/login wall before the form. Hand off to the user.
- The extension needs site permission for `career2.successfactors.eu` separately from the
  `careers.<company>.com` wrapper. If JS/screenshots return "Permission denied for this domain",
  ask the user to grant it.

## Traps (all observed, all cost a full refill when ignored)
1. **Résumé upload re-parses and WIPES address/city/zip/state.** Upload the résumé FIRST, then
   fill the address block. The parse populates work experience and education, but per SKILL.md rule 9b every
   entry is still entered/overwritten by hand from `form-pack.md` in PDF order, and every
   description re-read in full after the last Save.
2. **`Save` silently blanks every free-text description field** — "Most important duties and
   responsibilities" on each work entry and "Description" on each education entry. Everything
   else persists. Refill those AFTER the last Save, and do not Save again afterwards.
3. **Free-text description fields reject JS-set values** on the server round-trip. They accept a
   JS set in the DOM, but the value does not survive Save. Type them with real keystrokes
   (`computer` click + type) as the final step.
4. **Element ids renumber on every re-render** (upload, Save, section expand). Re-enumerate ids
   before each batch; never reuse ids across a re-render.
5. Dropdowns (State, Degree, Field of Study, Language, Proficiency, Country/Location of Interest,
   gender) are custom comboboxes: real click to open, type to filter, real click on the option.
   JS `value` sets do not stick.
6. Date fields (`MM/DD/YYYY`) take a real click + typed string + Tab. No JS.
7. Clicking "Add" on a section that the parse already populated appends an EMPTY row — delete it
   with that row's "Delete Row"/Remove control.
8. Losing the tab loses everything unsaved; only the résumé attachment lives on the profile.

## Field-of-study vocabulary is employer-specific
Metso's list is industrial (Engineering - mechanical, extractive metallurgy, ...). There is no
Computer Science option; **Information technology** is the closest for both degrees.

## Questions actually asked (Metso)
Only **"What is your gender?"** under Job-Specific Information (from `profile.md`). No work-authorization,
sponsorship, salary, or notice-period question appeared anywhere — so those locked answers have
nowhere to go on this form. Say so in the handoff rather than implying they were entered.

## Warning banner
"Applying will change your preferences" — submitting flips the candidate profile to be visible to
recruiters outside the applicant's own country. Surface it to the user before they click Apply.
