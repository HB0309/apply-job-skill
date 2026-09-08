# Interview prep with the skill

The skill is an application pipeline first, but it leaves behind exactly the material an
interview needs, and the inbox mode starts a prep folder the moment a process moves forward.

## What gets created automatically
When `/apply-job inbox` classifies an email as an **online assessment** or an **interview
invite**, it creates `interview-prep/<company-slug>/process-notes.md` (same slug as the
application folder) with:
- what the email said, verbatim: stages, dates, links, proctoring or format details;
- a short researched note on the format when it is identifiable ("50 questions in 15 minutes"
  is a CCAT; "Behavioral DNA" is a personality inventory; "Coderbyte", "HackerRank", "CodeSignal
  GCA" each have known shapes);
- the tracker row moves to `oa` or `interview`, and the morning brief lists the deadline first.

## What to ask for
Plain language works. Examples:
- "Prep me for the Acme phone screen" → Claude reads `applications/<acme folder>/match-report.md`
  (the genuine gaps and rewordings-to-rehearse sections), the posting, and `jobkit qa list`, then
  drafts likely questions with the story to use for each. It writes the result into the same
  `interview-prep/<company>/` folder.
- "Which story for 'tell me about a conflict'?" → `jobkit qa get conflict` and a suggested
  framing for that company.
- "The Acme OA is a 90-minute coding test, two problems" → a study plan and, if you want,
  practice problems in the style; solutions go in `interview-prep/<company>/`.
- "I had the interview, they asked X and Y, I answered Z" → the answers worth keeping are added
  to `qa-bank.md` as new stories (with your OK), and the tracker row gets the note.

## What the skill will not do
- Sit the assessment or the interview for you, or answer live questions in a proctored test.
- Put anything in a story that is not also true in the content pool. The separation rule runs
  the other way too: a story can carry more detail than a bullet, but never a different fact.

## Keeping the bank honest
After every interview, spend five minutes: which question surprised you? That is a missing
story. Tell Claude the real answer you gave, and it will file it under the right project with
the right angle tag. The bank gets better one interview at a time.
