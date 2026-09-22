# Amazon (account.amazon.jobs) — playbook

Amazon's own ATS. Promoted from `_unknown.md` on 2026-09-12 after reqs 10530257 (Audible,
SDE Early Career) and 10535483 (SysDE I, REALM) were filled back to back. Earlier appearance:
req 10414316 (2026-08-10).

## Detection
- `account.amazon.jobs/en-US/applicant/jobs/<reqId>/apply` — the apply flow.
- `www.amazon.jobs/en/jobs/<reqId>` — the public posting (use this to fetch the JD; the apply
  URL is login-walled).
- Amazon subsidiaries may post here under their own name (Audible). Twitch uses Greenhouse
  instead — different playbook.

## Login
Login-walled. the user's session is normally live; if not, hand them the browser. Never create an
account.

## Page sequence (tabs in "My progress")
Contact information · General questions · Education · Job-specific questions · Work Eligibility ·
Resume · Acknowledgement · Voluntary EEO · Voluntary Disability (CC-305) · Voluntary Veteran ·
Review & submit.

The flow opens on the **first incomplete** section, usually Job-specific questions, because
everything else is already complete from a prior application.

## ⚠ THE BIG ONE: the profile is ACCOUNT-LEVEL, not per application

Contact info, the **résumé**, EEO / disability / veteran answers, and "How did you hear about
this role?" are stored **once per account** and shared by every open application. Confirmed
2026-09-12: fixing the address and name on req 10530257 changed them on 10535483 too, and both
reqs showed one résumé with one upload timestamp.

**Consequence — the résumé trap.** Two applications open at once **cannot carry different
résumés**. Uploading job B's résumé silently replaces job A's before A is submitted.

**Therefore: fill and submit one Amazon req completely before uploading the next one's résumé.**
Per-application tailored résumés require serial submission, not parallel filling. If the user is
submitting a batch themselves, tell them this explicitly *before* they submit.

## Widgets

| Widget | Behaviour |
|---|---|
| Yes/No questions | native `<select>`, option values **`1`=Yes, `2`=No**, blank default. Native setter + `input`+`change` works. |
| Radios | `el.click()` on the backing input works. |
| Country / state | native `<select>` (245–250 options). Native setter works. |
| **Date fields** | **JS-set values, real keystrokes, and the calendar icon ALL fail.** See below. |
| File upload | hidden `input#document-replace-input`; `file_upload` with a `read_page`/`find` ref works. |

### Continue buttons — only trusted coordinate clicks advance
Each section renders several `<a>Continue</a>` elements that are **zero-size and invisible**, plus
one real `<button>`. Clicking the button **by ref** saves progress ("Progress auto-saved ✓") but
does **not** navigate. Only `computer left_click` at the button's real
`getBoundingClientRect()` centre advances the wizard.
Measure coordinates **in the same call that scrolls**, then click in the next call — and re-measure
after any re-render, because a stale y-coordinate silently clicks nothing.

### Date fields are unfixable — do not burn turns on them
The CC-305 "Today's date" field and the EAD-expiry field accept a value into the DOM and then fail
validation with **"Please enter a valid date or month"**, which blocks the whole section from
committing. Tried and failed on 2026-09-12: native setter + events, `triple_click` + real typing
(twice, at verified coordinates), and clicking the calendar icon.
- **Leave whatever date is already stored.** the user's account currently carries a stale CC-305
  signature date of **2024-11-15**; it is account-level, so it appears on every application.
- If a date edit has already corrupted the widget, **reload the page** — the reload discards the
  bad value and restores the committed one (see below).
- Only a human typing into the picker seems to work; hand it to the user if the date genuinely matters.

## ⚠ Reload semantics and the "review incomplete" trap

- A reload **discards every uncommitted answer** and restores the last server-saved state. Answers
  that survive a reload were genuinely saved; answers that come back `null` never were.
- After a reload, answering a question that **reveals conditional children** (see the Work
  Eligibility cascade) leaves those children *rendered as pre-filled from the profile but not
  saved*. The section then stays **"review incomplete"** with **no error text, no red field, and
  nothing unanswered** — and Continue will not advance.
- **Fix:** force a real change event on every auto-populated conditional — click the *wrong*
  option, then click the correct one. After that the section commits normally.
- Section state is readable from each tab's `aria-label`: `review completed` / `review incomplete`.
  The Review & submit tab carries `aria-disabled="true"` until every section is complete. Use these
  labels as the source of truth, not the visual checkmarks.

## Validation errors are plain text, not ARIA
Errors render as leaf text nodes; there is **no `role="alert"` and no `aria-invalid`**. Scanning
ARIA finds nothing. Scan for leaf elements whose text matches `/please enter|valid|is required/i`.

## Work Eligibility — the sponsorship cascade
`REQUIRE_SPONSORSHIP = YES` reveals, in order: `HOLDING_work visa`, `HOLDING_J-1`, a
"current nonimmigrant status" select, `REQUIRE_CPT`, `IS_YOUR_DEGREE_STEM`, an EAD-expiry date,
and `IS_CURRENT_EAD_YOUR_STEM_EXTENSION`. Each new answer can reveal the next, so re-read after
every one.

### Question → answer map (standing rule)

| Field | Answer |
|---|---|
| `HAVE_YOU_PREVIOUSLY_APPLIED_TO_AMAZON` | **Yes** (many prior applications) |
| `PREVIOUS_AMAZON_EMPLOYMENT` | No |
| `NON_COMPETITION_AGREEMENT_STATUS` | No |
| `ELIGIBLE_TO_BEGIN_EMPLOYMENT` | Yes |
| `REQUIRE_SPONSORSHIP` (combined now-or-future) | **Yes** |
| Immigration block (`HOLDING_*`, current nonimmigrant status, `REQUIRE_CPT`, EAD expiry,
  `IS_CURRENT_EAD_YOUR_STEM_EXTENSION`, `BACKGROUND_CHECK_LAST_SEVEN_YEARS`, citizenship, deemed-export
  questions) | every answer from `profile.md` / `form-data.md`; a pre-filled value from an old
  session may be stale (CPT eligibility ends at graduation) — correct it. EAD expiry: blank unless on file. |

## General questions — referral
"How did you hear about this role?" options: Advertisement · Amazon Career Site · At School/On
Campus · Events · **From a Person** · Job Posting · Other · Social Media.

For an employee referral pick **From a Person**, which swaps the follow-up select to
**A current employee** / A former employee / A recruiter / Other → choose **A current employee**.

**There is no free-text field for the referrer's name anywhere in the flow.** The referral is
carried by the `account.amazon.jobs` link itself — there is no code or token. Do not hunt for one.
Amazon's referral email (`noreply@mail.amazon.jobs`) names the referrer and req ID and nothing else.

Also on this page: "Are you willing to relocate?" → **Yes**.

## Stale account-profile defects seen 2026-09-12 — check every time
The carried-over profile had been wrong for a while. Verify these on the review page, never trust them:
- Address stored with a typo → correct it from `form-data.md`.
- Name stored as the preferred name → correct to the legal name (legal-name rule).
- Source stored as `Amazon Career Site` / `Amazon.jobs` → correct when a referral applies.
- CC-305 signature date `2024-11-15` → **cannot be fixed** (see Date fields).
- `REQUIRE_CPT` pre-filled `Yes` → correct to No.

## Review & submit
- The review page renders values as **text, not inputs** (`mounted inputs = 0`) — read it by text
  anchors. Sections collapse behind **"Show all answers"**; click every toggle (8 of them) before
  verifying.
- Anchor on a unique string like the email address: the sidebar nav also begins with
  "Contact information" and will match a naive search first.
- The résumé block shows filename + upload time — **check the timestamp**, not the filename, since
  every tailored résumé is called `Resume.pdf`.
- One `Submit application` button. **Never click it.**

## Post-submit
Amazon may issue an OA / work-simulation invitation by email afterwards (req 10414316 did).
