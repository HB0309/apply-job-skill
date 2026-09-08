# iCIMS — playbook

**Detect:** `*.icims.com`, `careers-*.icims.com` · **8 applications** · **No schema API.**
**Auto-submit risk:** medium — treat as unfamiliar, verify state after every click.

## Quirks
- **Renders inside `icims_content_iframe`, and the tooling cannot get refs into it.** `read_page`
  and `find` only see the wrapper page; `file_upload` therefore has no ref for the resume input.
  Navigating the tab to the iframe's own URL does NOT help — iCIMS re-wraps itself in the frame.
  What DOES work: the frame is same-origin, so
  `document.getElementById('icims_content_iframe').contentDocument` reads and fills text fields
  and selects via the native-setter pattern. **Resume upload and any file input stay manual.**
- **A PepsiCo-style portal opens on ACCOUNT CREATION, not a form** (`accountId=-1`, fields
  `PersonProfileFields.Login` / `.Password` / `.Password_Confirm`) and can carry an
  **hCaptcha** (`h-captcha-response` textarea). Account creation, passwords and CAPTCHAs are all
  prohibited — combined with the un-reachable file input that makes the entire first page a
  hand-off. Check for these three before starting: if present, hand over immediately rather than
  filling name/address, because that page's resume upload states it REPLACES existing form data,
  so anything filled before the upload is discarded. Correct order: the user uploads the resume and
  sets credentials first, then the agent fills and verifies the rest.
- Frequently asks **reason for leaving** and **supervisor contact** per job — both come from
  `form-data.md`: reasons are fixed lines; references/supervisor contacts are always left blank.
- Often asks salary history — leave blank, or "Negotiable" if it blocks.
- Multi-page with a progress bar; re-enumerate per page.

## Known question → answer mappings
| Question contains | Answer |
|---|---|
| "reason for leaving" | see form-data.md table |
| "may we contact this employer" | No |
| "desired salary" | Negotiable, targeting <salary range> |

## Work-experience ordering (2026-09-05; SKILL.md rule 9b governs the whole section)
iCIMS renders experience entries in the order they were created and offers no re-sort. The
resume parse frequently lands them out of order or merges two roles into one. After the upload,
read every entry back and make the list strictly reverse-chronological (most recent first),
matching the tailored PDF entry-for-entry. If an entry sits in the wrong slot and has no
move control, clear the entries and re-enter them in the correct sequence rather than leaving
a scrambled history in front of the recruiter.

## Jibe/iCIMS candidate-profile form — verified 2026-09-07 (Garmin req 19098)

**Entry path.** `careers.<co>.com/jobs/<id>/apply` renders the *posting*, not the form. The real
apply link points at `careers-<co>.icims.com/jobs/<id>/login`. That login page asks only for an
email, then lands on a **Candidate Profile** page with `accountId=-1`, `PersonProfileFields.Login`
/ `.Password` / `.Password_Confirm` and an **hCaptcha** — the account-creation hand-off case above.
the user must set the password, clear the captcha, and upload the resume (the file input lives inside
the iframe, so `file_upload` has no ref). Everything after that is fillable.

**Two-step flow:** Step 1 Candidate Profile → `Submit Profile` (`cp_form_submit_i`) → Step 2
Confirm Application. `Submit Profile` is a real submit guarded by the captcha; hand it over.

**Widget taxonomy — this is what makes or breaks the fill:**
- *Plain text inputs* (names, city, zip, employer, title, year, reason-for-leaving textarea) and
  *plain selects* (PhoneType, AddressType, IsGraduated, date Month/Day, "How did you hear about
  us?") accept the native-setter + `input`/`change`/`blur` pattern. Batch them in one JS call.
- *`icimsDropdown` lookups* (Country, State, School, Degree, Major, address Street1) do NOT. The
  native `<select>` carries class `dropdown-hide`, `offsetParent` is null, and its option list is
  empty until the widget loads it. Drive them with real clicks: click the widget → type into the
  `.dropdown-search` box that appears → click the result row.

**Read-back trap (cost a false "15 required fields empty" report).** After a lookup is set, the
widget collapses the native select to a **single option at index 0**. So `selectedIndex > 0` reads
a correctly-filled field as EMPTY. Verify with the option *text* at `selectedIndex >= 0` and treat
`— Make a Selection —` / `Please select a country` / `No states available` / `-Select-` as the
empty values.

**Scrolling.** The iframe is sized to its full content, so `scrollIntoView` inside it does nothing
visible. Scroll the OUTER window:
`window.scrollTo(0, iframe.getBoundingClientRect().top + window.scrollY + el.getBoundingClientRect().top + iframeWin.scrollY - 200)`.

**Repeating sections.** "Add More (X)" are real elements with ids like `rcf3211Button_-1`,
`CandProfileFields.EducationButton_-1`. JS `.click()` works and creates blocks with `-2`, `-3`
id prefixes; the newest block's own button is `..._-2`. Verify `cp_form_submit_i` still exists
after each click (auto-submit guard). Fill order does not matter — entries render in creation
order, so create them most-recent-first.

**Field-name decoder (Professional Experience):** `rcf3212` Employer · `rcf3213` Title ·
`rcf3216` City · `rcf3217` State · `rcf3218` Country · `rcf3214_*` Start date ·
`rcf3215_*` End date (leave blank if current) · `rcf3268` Reason for Leaving.

**Gotchas seen once:**
- The Address lookup offers an `— Enter Manually —` row that converts it to a free-text input.
- Education has no GPA field; Major often lacks the exact program — leave the lookup unset and put
  the real field of study in the adjacent free-text **Other Major** rather than mislabeling.
- Dates: the form's own instruction is "if the exact date is unknown, select the first day of the
  month" — follow it over the house day-15 default, and say so in the handoff.
- A required SMS-consent select can ship pre-selected with **only** a consent option (no decline).
  Do not set it; flag it to the user as a standing marketing consent they are agreeing to.
- Account linkage can prefill Legal First Name as the FULL name and Last Name as `Lnu`
  ("last name unknown"). Always check and fix both.
