# `/apply-job inbox` — morning Gmail sweep

1. `python bin/jobkit.py track active --query` prints ready-made Gmail queries — the companies
   with a live application (`applied` / `viewed` / `oa` / `interview` / `offer`), 20 names per
   query so nothing gets truncated. **Never read `tracker.md`; never build the OR-list yourself.**
2. **Read Gmail via the API script** (default since 2026-07-31 — cheaper and more reliable than
   Chrome scraping): for each printed query
   `cd <WORKSPACE>\bin\gmail && python gmail_search.py search "<query>" --max 30`.
   For a hit whose snippet is ambiguous, `python gmail_search.py read <message_id>`.
   If the script reports an expired token, tell the user to run `python gmail_auth.py` once — the
   OAuth app is in "Testing" status, so Google expires refresh tokens after 7 days until they
   publishes it in the Google Cloud console. Fallback only if they decline: Chrome
   (`tabs_context_mcp`, new tab, `mail.google.com`, `get_page_text` on a search URL).
3. Classify each hit: rejection / online assessment / interview invite / recruiter reply / noise
   (marketing, confirmations). Snippets are usually enough to tell "thank you for applying" from a
   real rejection ("other candidates were closer", "won't be moving forward"); `read` anything
   ambiguous.
3a. **Any hit classified as online assessment or interview invite → create/update
   `interview-prep\<company-slug>\process-notes.md`** (same slug as the `applications\` folder):
   what the email said verbatim (stages, dates, links, proctoring/format), plus a short researched
   note on the format if identifiable ("50 questions in 15 minutes" = CCAT). A stub is enough;
   flesh it out later if asked. Silent — surface it via the brief's action items.
4. Update the tracker through the script only:
   `python bin/jobkit.py track set <folder-or-link> --status rejected|oa|interview|offer --notes "<sender, date, quote>"`.
5. `python bin/jobkit.py track audit --days 7` — its "prepped/filled but never submitted" list goes
   into the brief so nothing stays half-done silently.
6. Reply with a morning brief: 3–5 sentences, action items first ("OA from Gamma due Thursday"),
   then status changes, then the never-submitted list, then silence-count ("4 applications silent
   past 14 days").

Plain-language outcome reports at any time ("Acme rejected me", "got an interview at Beta") →
`track set` the matching row immediately.
