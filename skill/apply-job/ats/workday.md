# Workday — playbook

**Detect:** `*.myworkdayjobs.com` — also any company careers page whose Apply click redirects
there (careers.homedepot.com, corporate.target.com, jobs.boeing.com). · **37 applications** ·
**No schema API — DOM path.**
**Auto-submit risk:** low (explicit multi-step wizard), but it **requires an account**.

## Login wall — hand over first
Workday requires sign-in or account creation before the application. STOP at the wall and
hand the user the browser: "your turn to log in." Never create accounts or enter passwords/OTPs.
Resume filling once they say they're in.

## Page sequence
1. My Information (name, address, phone, "how did you hear")
2. My Experience (**work history, education, skills, resume upload** — the big one; step 9a applies in full)
3. Application Questions (visa, authorization)
4. Voluntary Disclosures (EEO)
5. Self Identify (disability form)
6. Review → Submit

Re-enumerate fields on every page. **Before every Next / Save and Continue: one full read-back
of every field on the page against form-pack (SKILL.md 9.2 step 6), fix, re-read, then click.**
After the click, confirm the new page is the expected step and not a validation bounce.

## Quirks — these bite every time
- **Date fields are spinbuttons.** A JS-set value silently fails — and worse, it **displays
  correctly while never registering internally**, so a read-back of `.value` shows the right date
  and Save still returns "The field From is required and must have a value" for every one
  (Salesforce wd12, 2026-09-05: all 18 segments looked filled, all 18 were rejected). The
  read-back cannot catch this; only Save can. Click the **month segment** (the left ~third of the
  box, e.g. x≈437 on a 1536px viewport — clicking the box's centre misses it) and type the digits
  straight through: `062026` for MM/YYYY, `12182025` for MM/DD/YYYY. The widget auto-advances
  between segments. Retyping over a stale JS value works; no need to clear first.
- **Lookup fields (Field of Study, Skills, Location, Degree)** reject JS values, and typing alone
  does not search — the widget shows only category rows ("Partial List", "All") until you press
  **Enter to run the search**. Order that works: real click on the field, type the term, press Enter,
  wait, then **click the option row** (a JS `.click()` on the option does nothing; it needs a real
  click). Never press Enter to *select* — the top row is often a near-miss ("Computer Science and
  Communication Engineering" over "Computer Science and Engineering", "C (Programming Language)"
  over "C++ Programming Language"). Multiselects add a chip per pick, pushing the search box down
  ~29px each time, so re-screenshot rather than reusing coordinates.
- **Lookup *search* can be JS-driven even though selection cannot.** Native-setter the query into
  the input, then dispatch `keydown`/`keypress`/`keyup` with `key:'Enter'` — the search runs. The
  option row still needs a real click; `option.click()` does nothing. This halves the round trips.
- **In a multiselect (skills, Field of Study), click the row's CHECKBOX**, not its text. Clicking
  the label area closes the dropdown without selecting and looks like a silent failure.
- **Enter sometimes *selects* the highlighted row instead of running the search**, and the top row
  is often a near-miss — "Information Security" typed → **Information Technology** selected
  (Salesforce wd12, 2026-09-05). Always read back what got chipped and remove a wrong pick via its
  chip `×`.
- **Answering a question can reveal a new required dropdown below it.** Answering "Yes" to
  sponsorship injected a "current visa type" dropdown; a blind click at the usual Yes/No offset
  picked **J-2** instead of **<visa type>**. Never fire a pre-computed option click after a change
  that may re-render the form — re-read the question list first.
- **Beware page zoom.** At 125% zoom, `getBoundingClientRect()` coordinates land short of where
  the element actually is on screen. If a real click "does nothing", screenshot and compare the
  element's DOM y against its screenshot y before retrying.
- Elements carry `data-automation-id` attributes — the most stable selector available here.
- "Add" buttons create repeating blocks; each new block re-indexes, so re-read refs after every Add.
- **`Page Error — VPS|<uuid>` on Save is a server fault, not a validation failure.** Seen on
  Applied Materials' Voluntary Disclosures page (2026-09-03): every field valid, Save returns two
  VPS errors with a *new* uuid each attempt. Retrying does not help. Verify the fields still hold,
  then hand the browser to the user to finish the remaining pages rather than hammering Save.
- **My Experience page: SKILL.md rule 9b in full — enter every Work Experience and Education
  block by hand from `form-pack.md`.** "Autofill with Resume" and "Use My Last Application"
  both pre-populate these blocks and both have shipped wrong: AT&T (4 blocks for 3 jobs),
  Baker Hughes (titles/companies swapped), HPE (fabricated GPA), a Workday employer
  (truncated description), Home Depot 2026-09-08 (description missing on a profile-carried
  entry). Treat whatever is pre-filled as absent: delete extra blocks, overwrite every field.
  **Exception — the legal-name fields.** Where the profile stores a legal surname that looks
  like a placeholder, it may be correct: it can match the name on the work-authorization
  document. Leave it and fill preferred-name fields normally — record the rule in your
  own `form-data.md`.
  **Descriptions must be typed with real keystrokes** — a JS-set description passes the DOM
  read-back and is dropped on Save (Aderant 2026-09-03). After `Save and Continue`, when the
  page re-renders, re-read every block's full description and dates and compare to the pack
  before clicking Next. Order = PDF, most recent end date first.

## Known question → answer mappings
| Question contains | Answer |
|---|---|
| "How did you hear about us" | the job board the link came from (hard rule 7: Handshake / Jobright / LinkedIn / Indeed / …), else Company website |
| "legally authorized to work" | Yes |
| "require sponsorship" | Yes |
| "previously worked for" | No |
| Country | United States of America |
