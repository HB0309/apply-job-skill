# Unknown / unlisted ATS — generic playbook

Used when the URL matches no playbook. **Treat every unfamiliar form as auto-submit risky.**

## Method (DOM-first, screenshots last)
1. One `read_page(filter:"interactive")` → accessibility tree with `ref_` ids and labels.
2. Map every field to a `form-pack.md` value.
3. One `browser_batch` of `form_input(ref, value)` calls — fill within a page in a single round trip.
4. One JS read-back verifying every field. **Never report "filled" from a screenshot.**
5. `find` (natural-language lookup) for stubborn widgets before falling back to a real
   `computer` click.

## Rules that always apply
- **Never batch across a click** that navigates, advances, or might submit. Every such click
  is its own call, followed by a page-state read.
- React-controlled inputs need the native setter plus `input`/`change` events, not typing.
- Custom radios/toggles: `el.click()` on the backing `input`.
- File inputs need a `read_page` ref for `file_upload`.

## Promote it
**The second time a platform appears, create `ats/<name>.md`** with what was learned:
detection pattern, page sequence, quirks, and the question → answer mappings encountered.
That is how this directory gets cheaper over time.
