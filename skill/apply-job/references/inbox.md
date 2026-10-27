# `/apply-job inbox` — morning Gmail sweep

1. `python bin/jobkit.py track active --query` prints ready-made Gmail queries — the companies
   with a live application (`applied` / `viewed` / `oa` / `interview` / `offer`), 20 names per
   query so nothing gets truncated. **Never read `tracker.md`; never build the OR-list yourself.**
2. **Read Gmail via the API script** (cheaper and more reliable than Chrome scraping): for each printed query
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
3b. **Recruiter cold outreach.** One extra search — **run it with the Bash tool**, single-quoted
   as written (PowerShell 5.1 mangles the inner double quotes):
   `python gmail_search.py search 'newer_than:7d ("came across your profile" OR "your background" OR "reaching out" OR "opportunity for you") -from:jobalerts-noreply@linkedin.com -from:jobs-listings@linkedin.com -from:jobs-noreply@linkedin.com -from:jobright.ai -from:ziprecruiter.com -from:lensa.com' --max 20`.
   Only LinkedIn's job-*alert* senders are excluded: recruiter InMail notifications also come
   from `linkedin.com` and are the main outreach channel, so they must stay in.
   Keep only mail from a named human at a real employer or agency about a specific role —
   drop template blasts with no role, course/bootcamp ads, and anything from a job board.
   Surface each keeper as an action item (who, company, role, what they asked for). Job
   *alerts* are not this: those belong to the sweep harvest (`references\mail-harvest.md`).
4. Update the tracker through the script only:
   `python bin/jobkit.py track set <folder-or-link> --status rejected|oa|interview|offer --notes "<sender, date, quote>"`.
5. `python bin/jobkit.py track audit --days 7` — its "prepped/filled but never submitted" list goes
   into the brief so nothing stays half-done silently.
6. Reply with a short morning brief, action items first ("OA from Gamma due Thursday"),
   then status changes, then the never-submitted list, then silence-count ("4 applications silent
   past 14 days").

Plain-language outcome reports at any time ("Acme rejected me", "got an interview at Beta") →
`track set` the matching row immediately.
