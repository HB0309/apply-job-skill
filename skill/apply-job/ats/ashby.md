# Ashby — playbook

**Detect:** `jobs.ashbyhq.com/<org>/<uuid>`  ·  **61 applications, the most common ATS**
**Auto-submit risk:** low. A distinct Submit button exists. Still verify page state after clicks.

## Schema-first (preferred)
`python bin/jobkit.py schema <url>` returns every field before the browser opens.
Keys are either `_systemfield_*` or a UUID. Types: `String` `Email` `Phone` `Location`
`File` `Boolean` `ValueSelect` `MultiValueSelect` `LongText`.

Stable system keys seen on every posting:
| Key | Value from form-pack |
|---|---|
| `_systemfield_name` | <Full Name> (single "Full Name" field, not split) |
| `_systemfield_email` | email |
| `_systemfield_location` | <City, State> — autocomplete widget, needs a real click + pick |
| `_systemfield_resume` | resume PDF path via `file_upload` |

Everything else is a per-posting UUID: map it by its `title` from the schema.

## Quirks
- **Location is an autocomplete**, not a text input. Type, wait for the dropdown, click the option. A JS-set value does not register.
- `ValueSelect` / `MultiValueSelect` are react-select. Match the answer against `selectableValues` from the schema *offline*, then click — never harvest options from the DOM.
- `Boolean` fields render as Yes/No radios.
- File inputs need a `read_page` ref for `file_upload`.
- Closed postings return `posting not found` from the schema call — fall back to the DOM path.

## Known question → answer mappings
| Question contains | Answer |
|---|---|
| "require sponsorship now or in the future" | Yes |
| "legally authorized to work" | Yes |
| "preferred programming language" | Python |
| "employment eligible countries" | United States |
| "How did you find out about this" | the job board the link came from (hard rule 7: Handshake / Jobright / LinkedIn / Indeed / …), else Company website |
| gender identity | from `profile.md` |
| race / ethnic identities | from `profile.md` |
| veteran | I am not a protected veteran |
| disability | No |
