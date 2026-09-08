# Form-only data — apply-job

Values that ATS forms demand but the read-only master files don't carry. Skill-owned; edit
this file freely (unlike `master\content-pool.tex` and `master\profile.md`). Rename it to
`form-data.md` once filled in.

**Source of truth for everything else:**
- Identity, contact, work auth, visa, salary, notice period, pronouns → `master\profile.md`
- Job titles, employers, employment dates, bullets → `master\content-pool.tex` (Experience section)
- Degrees, institutions, graduation dates, GPA → `master\content-pool.tex` (Education section)

Hard rule 1 still governs: nothing here is invented. If a form needs a value that is not in
this file or the masters, leave it blank — do not improvise one.

---

## Education (start dates live ONLY here)

| Institution | Degree | Field of study | Start | End | Location | GPA |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |

- **Field-of-study lookup widgets** (Workday, Oracle CX) rarely have your exact string. List the
  search terms to try, in order, and the closest acceptable option: `<term 1>`, `<term 2>`, ...
  These are lookup widgets: real clicks + Enter, JS-set values silently fail.
- **GPA on forms:** which GPA to enter and on what scale. Do not convert scales.
- Highest level of education completed:

## Employment — reason for leaving

Asked by iCIMS / Taleo / SuccessFactors. Answer only what the form asks for.

| Employer | Reason for leaving |
|---|---|
| <current employer> | Currently employed — N/A (tick "I currently work here") |
| | |

Employer locations (for forms that ask separately from the title line):

## Certifications

| Field | Value |
|---|---|
| Name | |
| Exam code | |
| Issuing organization | |
| Issued | |
| Expires | |
| Credential ID | |
| Verification URL | |

## Languages

| Language | Proficiency |
|---|---|
| | |

## References & supervisor contacts

**Always blank.** Never enter a name, email, or phone number for a third party on any form.
Where offered, tick "available upon request" or set "may we contact this employer: No".
If a reference block is hard-required to submit, that is a pause trigger (hard rule 4) —
stop and ask.

## Standard defaults

| Question | Answer |
|---|---|
| Legal name | |
| Preferred name | |
| Are you 18 years or older? | |
| Legally authorized to work in the US? | (see `profile.md`) |
| Have you previously worked for this company? | No |
| Do you have relatives employed here? | No |
| Have you been convicted of a felony? | |
| Willing to relocate? | |
| Willing to travel? | |
| Salary history / last drawn compensation | Blank; if required, "Negotiable" |
| Websites / social profiles | LinkedIn + GitHub only; no portfolio |
| How did you hear about us? | The job board the link came from (hard rule 7); "Company website" only as fallback |
| Numeric "years of experience" | |

## Not known — leave blank

- Date of birth
- Driver's license (do NOT infer it from the job requiring driving)
- Supervisor names and contact details
- Salary history figures

If a form hard-requires any of these to advance, stop and ask (hard rule 4, trigger 1).
