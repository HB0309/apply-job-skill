# PageUp People — playbook

**Detection:** the apply flow redirects to `*.pageuppeople.com` (often `<org>-identity.login.pageuppeople.com`)
after a short intake widget on the employer's careers site (universities, public bodies; seen at
a university employer, 2026-09-21). `jobkit meta` has no API for it: expect `NO_META` and
`platform=unknown / no schema` in the form-pack.

**Auto-submit risk:** low. **Account wall:** ALWAYS, and it comes first. Right after the email
entry the site opens an identity-verification page (Google / LinkedIn / passkey / password /
emailed OTP) before any application field. Hand the tab to the user at that page (SKILL.md step 9,
login-wall rule); take back over once they are inside.

**Page sequence after login:** Personal details → Work Experience (entered by hand, PDF order) →
Additional Questions → Mandatory Information (EEO-style) → **Professional References** (2 named
references with phone and email, hard-required) → Review. The references page is a stop: fill
everything before it, hand off there, log `blocked` per `form-data.md` → References.

**Quirks:** fields are plain inputs and selects; a DOM-path fill with one JS read-back per page
works. Session survives a handoff pause.
