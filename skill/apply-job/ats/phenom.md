# Phenom People (CareerConnect) — playbook

**Detect:** company-branded domain (`careers.<company>.com`) + an apply route of
`/us/en/apply?jobSeqNo=...` or `/us/en/hvhapply?jobSeqNo=...`; assets served from
`pp-cdn.phenompeople.com` / `cdn.phenompeople.com`.
`jobkit schema` returns `ats=unknown / NO_SCHEMA_API` — **there is no schema. DOM path.**

## ⛔ `hvhapply` IS NOT A WIZARD — THE UPLOAD IS THE SUBMIT

**Check the URL path before touching anything.** Phenom has two apply routes and they behave
completely differently:

| Path | Behaviour |
|---|---|
| `/us/en/apply?jobSeqNo=...` | the six-step wizard below. Safe. Upload first as documented. |
| `/us/en/hvhapply?jobSeqNo=...` | **high-volume apply. Uploading the résumé submits the entire application immediately** — no Submit button, no wizard, no chance to fill anything. |

Confirmed at **Honda 2026-09-10** (OT Security Engineer, job 11971). The `hvhapply` page renders
what looks exactly like step 1 — "My Documents", "Profile Information", and a four-step progress
bar — so it is indistinguishable from the wizard by appearance. Uploading the résumé redirected
straight to `applythankyou?status=success` (application 707124), submitted with only the résumé
and the parser's name: no screeners, no work authorisation, no sponsorship answer, no EEO, none
of the prepared narrative answers.

**Rule:** on `hvhapply`, first try rewriting the URL to `/us/en/apply?jobSeqNo=<same value>`. If
that renders the real wizard, fill it there. If only `hvhapply` works, **do not upload** — stop
and hand the user the browser, because the upload sends a bare résumé on their behalf. The
"upload first" instruction below applies to `/apply` ONLY.

**Seen at:** Rocket Companies (2026-09-10).
**Auto-submit risk: low.** Six-step wizard with an explicit Review step; Submit is a distinct
button on step 6. No login wall on the Rocket instance — the whole flow is anonymous.

## THE TRAP: JS-set text values are silently discarded

This is the expensive one. On Phenom, a text input set via JS (native setter +
`input`/`change` events) **reads back correctly in the DOM and is never sent to the server.**

- Rocket 2026-09-10: the name silently reverted to the resume parser's all-caps
  version and the **entire address was dropped**. Every in-page read-back said the
  values were right. Only the step-6 review page exposed it.
- Same class of failure as Workday dropping JS-set descriptions on Save
  (the Workday playbook): a DOM read-back proves the DOM holds the value, not that
  the ATS stored it.

**What persists vs. what does not:**

| Widget | JS-set works? | How to fill |
|---|---|---|
| Text inputs (name, address, city, ZIP, skills textarea) | **NO — silently dropped** | real keystrokes: `computer` click → `ctrl+a` → type |
| `<select>` dropdowns | Yes, via native setter + input/change | JS is fine; re-read after ~1.5 s, React re-renders late |
| Radios / checkboxes | Yes, via `el.click()` | JS is fine |
| `<input type="date">` | **NO — fails validation** | real keystrokes (`ctrl+a` then `09/10/2026`); the field shows the value but the step refuses to advance until typed |
| Month/year and year pickers | No | real clicks (see below) |

**Rule: type every text field. Then walk to the review page and diff it against `form-pack.md`
before handing off. Treat the review page, not the DOM, as the source of truth.**

## Date pickers

- Education dates are **year-only** pickers; work-experience dates are **month + year**.
- A picker's selectable range is clamped by that entry's *other* bound. To move a start date
  later than the current end date, widen the end date first.
- Consequence (Rocket 2026-09-10): a newly added work entry could not be back-dated past the
  values it inherited, so an out-of-order 4th entry could not be fixed. **Do not add an
  experience entry that is not on the tailored PDF** — the three PDF entries in PDF order is
  both correct per fill.md 9b and the only order the widget will accept cleanly.

## Resume parse

- Step 1 offers `Upload Resume` before any field. **Upload first** — the parse populates work
  experience, education and skills. **`/apply` only** — on `hvhapply` the upload submits the
  application outright (see the box at the top).
- The parse is good on work experience: Rocket got all three entries right, in PDF order,
  with correct MM/YYYY dates and no invented entries. **Still diff it** (fill.md 9b).
- The parse is bad on two things:
  - **Name comes back ALL CAPS.** Always retype it in proper case.
  - **Skills becomes a noisy dump** (`Node`, `SES`, `Stripe Billing`, `AirCrack`, fragments of
    bullet text). Replace it with the curated list in `form-pack.md` — by typing, not JS.
- There is no description/responsibilities field per entry, so the résumé bullets are not
  needed on the form.

## Step map (Rocket instance)

1. **My information** — resume upload, prior-employment radio, country, name, address,
   email, phone + device type, Source (prefilled, leave it).
2. **My experience** — parsed work experience, education (degree select + year pickers),
   skills textarea, additional attachments.
3. **Application questions** — the job-specific questionnaire (`jsqData.QUESTIONNAIRE-*`).
4. **Additional application questions** — race/ethnicity + gender (`secondaryJsqData.*`).
5. **Voluntary Disclosures** — a single T&C consent checkbox.
6. **Review** — full read-only summary + **Submit. STOP HERE.**

## Field-key conventions

- Step 1: `cntryFields.firstName`, `cntryFields.lastName`, `cntryFields.addressLine1`,
  `cntryFields.city`, `cntryFields.region` (value form `USA-MD`), `cntryFields.postalCode`,
  `email`, `deviceType`, `phoneWidget.phoneNumber`, `candidateIdentifyAsPriorWorker.{true,false}`.
- Step 2: `experienceData[N].{title,companyName,location,fromTo.startDate,fromTo.endDate,
  fromTo.currentlyWorkHere}`, `educationData[N].{schoolName,degree,fromTo.startDate,fromTo.endDate}`.
- Steps 3–4: `jsqData.QUESTIONNAIRE-<id>.<letter>` and
  `secondaryJsqData.QUESTIONNAIRE-<id>.<letter>` — letters run `a`, `b`, `c`… in page order.
- Step 5: `disclosureVerification`.

## Known question → answer mappings (Rocket)

| Question | Answer |
|---|---|
| What is your pronoun? | They/Them/Their |
| Please select your time zone | the **role's** zone (Detroit → Eastern), not necessarily the user's |
| Overall work experience level | Early Career (Between 1 - 4 years) |
| Available to start full-time | today's date (immediately available) — **must be typed** |
| Willing to relocate? | Yes |
| NMLS account? | No |
| Subject to a non-compete? | No |
| Under 18 work permit? | N/A |
| Legally authorized to begin immediate employment in the US? | Yes |
| Need immigration support/sponsorship now **or in the future**? | Yes (combined question) |
| Military affiliation self-ID | No |
| Race/ethnicity · Gender | from `profile.md` |

## Degree select

61 options, many of them non-US degree names; exact matches usually exist (`M.S.`, `Bachelor of Technology (B.Tech)`).

## Other

- Attachment cap is **1 MB** — the <University B> marksheets (~3.5 MB) will be rejected; see
  `form-data.md` → Transcripts.
- A "Rocket Careers" chatbot opens over the page; dismiss it before clicking Apply.
- Sessions expire back to the job posting. If the wizard is gone, refill from step 1 —
  nothing is preserved.
- Clicking Next sometimes no-ops mid-render; re-`find` the button and click again rather than
  assuming a validation failure. Confirm the step actually changed via `location.search`.
