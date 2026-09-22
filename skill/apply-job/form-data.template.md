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

**Machine-read:** `jobkit formpack` copies the tables under Identity, Locked fields, Standard
defaults, Not known, Education, Certifications, Languages and Transcripts straight into every
`form-pack.md`, and `jobkit triage` reads the Auto-skip employers list. Keep those headings and
keep the values in tables — a value changed here changes every future application.

---

## Identity

Mirror of `master\profile.md` → Identity & contact, in the shape forms ask for it. If the
profile changes, change this table too.

| Field | Value |
|---|---|
| Legal first name (any plain "First Name") | `<legal first name>` |
| Legal last name (any plain "Last Name") | `<legal last name>` |
| Single unsplit "Full Name" box | `<legal full name>` |
| Preferred first / last — ONLY in a dedicated preferred-name field | `<preferred first>` / `<preferred last>` |
| Email | <email> |
| Phone | <phone> |
| Street address | <street> |
| City / State / ZIP | <city> / <state> / <zip> |
| Country | <country> |
| LinkedIn | <linkedin-url> |
| GitHub | <github-url> |
| Portfolio / website | none — leave blank |
| Pronouns (if asked) | <pronouns> |

## Locked fields (canonical answers — filled, never asked; SKILL.md hard rule 4)

| Field | Value |
|---|---|
| Legally authorized to work in the US? | **<Yes/No>** (<basis>) |
| Visa sponsorship, ONE combined "now or in the future" question | **<Yes/No>** |
| Sponsorship asked as TWO separate questions | now → **<Yes/No>**; future → **<Yes/No>** |
| Work authorization type, if asked | <visa type>; extension eligible: **<Yes/No>** |
| Salary expectation | **<salary range>** base, negotiable |
| Forced single number / "desired salary" | `Negotiable, targeting <salary range>` |
| Notice period / earliest start | **<availability>** |
| Gender | **<as you self-identify>** |
| Race / ethnicity | the closest option to **<as you self-identify>**; "Decline to self-identify" only if nothing maps |
| Veteran status | **<direct answer>** |
| Disability status | **<direct answer>** |

## Auto-skip employers (defense / gov — for applicants who are not US Persons, ITAR work is a legal bar)

The ONE copy of this list. `jobkit triage`, the scan flow and the mail harvest all use it;
add a name here and nowhere else. Matched as whole words against the company name. Edit it to
your own situation; delete it entirely if none of this applies to you.

- Anduril, L3Harris, RTX, Raytheon, Lockheed Martin, Lockheed, Northrop Grumman, General Dynamics
- Cubic, Huntington Ingalls, Textron, Booz Allen Hamilton, Booz Allen, Cherokee Federal, Leidos
- Relativity Space, SpaceX, Rocket Lab, Blue Origin, Firefly Aerospace, United Launch Alliance, ULA
- Stoke Space, Astranis, Sierra Space, Varda, Impulse Space, ABL Space

The space / launch names are export-controlled hardware employers whose forms ask a U.S. Person
question. `--force` still overrides.

Also dropped wherever it appears: any posting flagged `DoD` / `GovCloud` / "Public Sector" /
"Locals ONLY", and cleared roles generally.

## Form-pack notes — education

Copied under the Education table of every `form-pack.md`. One line each, bullets only.

- <specialization line, if a form asks>. Highest level of education completed: <level>.
- Field-of-study lookups (Workday, Oracle CX): search `<term 1>`, then `<term 2>`, then `<term 3>`; pick the closest existing option with real clicks + Enter.
- <degree> conferral date <MM/DD/YYYY>. Any other day-of-month a form forces: use 15.
- GPA on forms: <which GPA, on what scale>. Do not convert scales.

## Form-pack notes — transcripts

- "Undergraduate transcript" = <file>. Unqualified "transcript" on a role listing a master's = <file>. Both requested = attach both.
- Note any file over 1 MB: some ATSs cap uploads there; say so at handoff rather than substituting another document.

## Education (start dates live ONLY here)

| Institution | Degree | Field of study | Start | End | Location | GPA |
|---|---|---|---|---|---|---|
| <University A> | Master's / M.S. | <field> | **<Mon YYYY>** | <Mon YYYY> | <City, State, Country> | <GPA / scale> |
| <University B> | Bachelor's | <field> | **<Mon YYYY>** | <Mon YYYY> | <City, Country> | <GPA / scale> |

- **Field-of-study lookup widgets** (Workday, Oracle CX) rarely have your exact string. List the
  search terms to try, in order, and the closest acceptable option. These are lookup widgets:
  real clicks + Enter, JS-set values silently fail.
- **GPA on forms:** fill the GPA whenever a GPA field exists. The `resume-style.md` GPA rule is a
  *page-fit* lever for the PDF only; a form field has no page budget, so it never applies here.
  Never convert a GPA to another scale.
- Highest level of education completed: **<level>**.
- Optional: academic detail a screener may ask about (semester progression, credits, medium of
  instruction, entrance exams, language tests) — only facts you can show a document for.

## Employment — reason for leaving

Asked by iCIMS / Taleo / SuccessFactors. Answer only what the form asks for; these are the
approved wordings.

| Employer | Reason for leaving |
|---|---|
| <current employer> | Currently employed — N/A (tick "I currently work here") |
| <Employer B> | <e.g. Research role concluded> |
| <Employer C> | <e.g. Semester appointment ended> |
| <Employer D> | <e.g. Internship ended> |

Employer locations (for forms that ask separately from the title line): <Employer A> —
<City, State>; <Employer B> — <City, State>; ...

## Transcripts & academic documents

Real, official documents in `master\` — attach them when a form asks; never substitute one for
the other, and never claim a transcript that is not one of these.

| Document | Path | Size |
|---|---|---|
| <University A> official transcript | `master\<file>.pdf` | <size> |
| <University B> official transcript | `master\<file>.pdf` | <size> |

- "Undergraduate transcript" means the bachelor's document. A required transcript upload is not
  a reason to skip a posting.
- Any file over ~1 MB will be rejected by some forms (Phenom caps at 1 MB; Greenhouse and Ashby
  are more generous). If a size cap blocks it, say so in the handoff; never attach the other
  transcript in its place.

## Certifications

| Field | Value |
|---|---|
| Name | <certification> |
| Exam code | <exam code> |
| Issuing organization | <issuer> |
| Issued / certified | <YYYY-MM-DD> |
| Expires | <YYYY-MM-DD> |
| Candidate ID | <id> |
| Verification code | <code> |
| Verification URL | <url> |

## Languages

| Language | Proficiency |
|---|---|
| <language> | <proficiency> |

## References & supervisor contacts

**Always blank.** Never enter a name, email, or phone number for a third party on any form.
Where offered, tick "available upon request" or set "may we contact this employer: No".
If a reference block is hard-required to submit: fill every other page, stop at the references
page, hand off, and log the row `blocked --notes "requires N named references"`. No stored
contacts; the user supplies them by hand for a posting they care about.

## Standard defaults

| Question | Answer |
|---|---|
| Any first / last name pair — labelled "legal" OR plain "First Name / Last Name" | `<legal first>` / `<legal last>` — see **Name convention** below |
| Preferred first / last name — ONLY when the form offers a separate preferred-name field | `<preferred first>` / `<preferred last>` |
| Single unsplit "Full Name" field | `<legal full name>` |
| Are you 18 years or older? | Yes |
| Legally authorized to work in the US? | <Yes/No> (see `profile.md`) |
| Have you previously worked for this company? | No |
| Do you have relatives employed here? | No |
| Have you been convicted of a felony? | <answer> |
| Willing to relocate? | <answer> |
| Willing to travel? | <answer> |
| Salary history / last drawn compensation | Blank; if required, "Negotiable" |
| Websites / social profiles | LinkedIn + GitHub only (`profile.md`); no portfolio |
| How did you hear about us? | The job board the link came from (SKILL.md hard rule 7). Company website only when the board is not offered or the link came from the careers site directly. |
| Numeric "years of experience" | <n> (`profile.md`) |
| Work-authorization extension eligible? | **<Yes/No>** |
| Bound by a non-compete / restrictive covenant? | **<Yes/No>** (standing answer) |
| Consent to SMS / text-message contact from the employer or its recruiting partners? | **<Yes/No>** (standing default) |

## Name convention — read before filling any name field

State here how your legal name appears on your work-authorization documents, and whether it
differs from the name on your résumé. Forms, I-9 and E-Verify check the name against those
documents, so the legal-name fields must match them character for character, even when the
stored value looks odd (a placeholder surname, a given name that contains a space).

| Field type | First | Last |
|---|---|---|
| **Every name field by default** — plain "First Name / Last Name", "legal first/last name", background check, I-9, offer letter, e-signature | `<legal first>` | `<legal last>` |
| **Preferred** name — ONLY in a separate "preferred first/last name" / "what should we call you" field the form actually offers | `<preferred first>` | `<preferred last>` |
| **Single unsplit "Full Name"** box | `<legal full name>` | — |
| **Résumé, cover letter, LinkedIn, email signature** | `<name as printed on the résumé>` | — |

**Rule: legal name first, always.** Every name field gets the legal name unless it is explicitly
a preferred-name field. A returning-candidate profile or a résumé parse that already shows the
legal form is CORRECT: leave it, do not overwrite it, do not report it as a parser artifact.
This is the one exception to the standing rule that parsed identity data is never trusted.

## Not known — leave blank

- Date of birth
- Driver's license (do NOT infer it from the job requiring driving)
- Supervisor names and contact details
- Salary history figures

If a form hard-requires any of these to advance, stop and ask (hard rule 4, trigger 1).
