#!/usr/bin/env python3
"""mailjobs -- pull job postings out of alert email, for `/apply-job sweep`.

Same idea as jobkit: the mechanical work (Gmail reads, HTML parsing, redirect
resolution, dedupe) happens here so the digest bodies never reach the model's
context. One compact line per surviving candidate is the whole output.

  harvest [--since auto|<N>d] [--max-msgs N] [--json]
      Read alert mail since the last harvest (capped at 3 days), extract job
      links, drop everything already known, print the survivors.

  enrich <url> ... | -        [--body N] [--gap SECONDS]
      Triage data for LinkedIn postings from the public guest endpoint -- company,
      title, location, posted age, applicants, and flags for clearance, US-person,
      sponsorship, years of experience and pay. No login, no browser. Anything else
      prints NEEDS-OPEN.

  sources
      Print the sender allow-list and the blocked senders.

  seen <url> [<url> ...]
      Mark URLs as processed so a later harvest never re-surfaces them.
      Run this on whatever was triaged, queued or dropped.

Read-only against Gmail (scope gmail.readonly, shared with gmail_search.py).
State lives in mail-state.json next to this file.
"""
import argparse
import base64
import datetime
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(HERE)
ROOT = os.path.dirname(BIN)
STATE = os.path.join(HERE, "mail-state.json")
ENRICH_CACHE = os.path.join(HERE, "mail-enrich-cache.json")
SWEEP_FEED = os.path.join(ROOT, "job-matcher-feed")
TRACKER = os.path.join(ROOT, "tracker.md")

sys.path.insert(0, BIN)
from jobkit import norm_url  # noqa: E402  -- one canonical URL normaliser, not two

# --------------------------------------------------------------------- config
# quality: 1 = board alert, 2 = employer talent community, 3 = newsletter digest.
# Used only to order candidates when the triage cap bites.
SOURCES = [
    {"key": "linkedin", "quality": 1, "from": [
        "jobalerts-noreply@linkedin.com", "jobs-listings@linkedin.com",
        "jobs-noreply@linkedin.com"]},
    {"key": "jobright", "quality": 1, "from": ["jobright.ai"]},
    {"key": "handshake", "quality": 1, "from": ["joinhandshake.com", "handshake.com"]},
    {"key": "dice", "quality": 1, "from": ["dice.com"]},
    {"key": "talent", "quality": 2, "from": [
        "jobs2web.com", "icims.com", "myworkday.com", "successfactors.com",
        "taleo.net", "smartrecruiters.com", "greenhouse.io", "ashbyhq.com"]},
    {"key": "newsletter", "quality": 3, "from": [
        "careerbrew@substack.com", "apexearlycareers.com"]},
]

# Deliberately not harvested -- measured low signal (staffing reposts, sub-$100k
# bands, degree ads). standing rule, 2026-09-19.
BLOCKED = ("ziprecruiter.com", "lensa.com", "ihire.com", "notify.ihire.com")

# A message whose subject looks like application correspondence is not an alert.
# `/apply-job inbox` owns those; harvesting them would queue the employer's own
# careers page as if it were a new posting.
NOT_AN_ALERT = re.compile(
    r"application (update|status|received|confirm)|thank you for (applying|your interest)"
    r"|no longer under consideration|not (be )?mov(e|ing) forward|unfortunately"
    r"|interview (invit|request|schedul|with|for|confirm)|schedule (your|an) interview"
    r"|(online|coding|technical|skills?) assessment|complete (your|the|an) assessment"
    r"|offer letter|job offer|offer of employment|your application", re.I)
# The bare words "interview", "assessment" and "offer" are deliberately NOT here:
# they discarded real alerts ("Acme is hiring: Security Assessment Engineer").

# A URL only counts as a posting if it has a job-DETAIL path. Host alone is not
# enough: alert mail is full of career-site landing pages, "manage your job
# alerts" links and company profiles that would otherwise be queued as jobs.
JOB_URL = re.compile(r"""(?ix)
      linkedin\.com/(?:comm/)?jobs/view/\d+
    | jobright\.ai/jobs/info/[a-f0-9]{8,}
    | joinhandshake\.com/(?:stu/)?jobs/\d+
    | dice\.com/job-detail/[a-f0-9-]{8,}
    | (?:job-)?boards\.greenhouse\.io/[^/]+/jobs/\d+
    | greenhouse\.io/embed/job_app\?
    | jobs\.lever\.co/[^/]+/[a-f0-9-]{8,}
    | jobs\.ashbyhq\.com/[^/]+/[a-f0-9-]{8,}
    | myworkdayjobs\.com/.+/job/
    | icims\.com/jobs/\d+
    | smartrecruiters\.com/[^/]+/\d{6,}
    | taleo\.net/careersection/.*\bjobid=
    | successfactors\.[a-z.]+/.*\bjobid=
    | oraclecloud\.com/.*/job/\d+
    | jobs\.workable\.com/(?:view|j)/
    | jobvite\.com/.*/job/[a-zA-Z0-9]+
    | bamboohr\.com/(?:careers|jobs)/\d+
    | breezy\.hr/p/[a-f0-9]{8,}
    | phenompeople\.com/.*/job/
    | eightfold\.ai/careers.*\bpid=
    | avature\.net/careers/JobDetail
    | recruitee\.com/o/
    | applytojob\.com/apply/[a-zA-Z0-9]+
    | jobs\.apple\.com/.*/details/\d+
    | google\.com/about/careers/.*/jobs/results/\d+
    | amazon\.jobs/.*/jobs/\d+
    | metacareers\.com/jobs/\d+
""")

# Wrappers that hide the real destination behind a click-tracker.
REDIRECT_HOSTS = (
    "click.", "clicks.", "email.", "e.", "link.", "links.", "track.", "trk.",
    "substack.com/redirect", "jobs2web.com", "sendgrid.net", "mandrillapp.com",
    "list-manage.com", "awstrack.me", "hubspotlinks.com", "ct.sendgrid.net",
    "mailtrack", "go.dice.com", "email.jobright.ai",
)

GENERIC_ANCHOR = re.compile(
    r"^(apply|apply now|view job|view( the)? job|see job|learn more|read more"
    r"|details|view details|click here|here|more|see all|view all|unsubscribe"
    r"|open|save|view)$", re.I)

ANCHOR = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                    re.I | re.S)
TAG = re.compile(r"<[^>]+>")
BARE_URL = re.compile(r"https?://[^\s<>\"')\]]+")
MAX_LINKS_PER_MSG = 60
MAX_RESOLVE = 80
PENDING_DAYS = 5   # an undecided row stops resurfacing after this long
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) mailjobs/1.0"


# ---------------------------------------------------------------------- state
def load_state():
    try:
        with io.open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"last_run": None, "seen_msgs": [], "seen_urls": [], "pending": {}}


def save_state(state):
    state["seen_msgs"] = state["seen_msgs"][-2000:]
    state["seen_urls"] = state["seen_urls"][-4000:]
    with io.open(STATE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)


def uhash(url):
    return hashlib.sha1(norm_url(url).encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ gmail I/O
def get_service():
    sys.path.insert(0, HERE)
    from gmail_auth import get_credentials
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=get_credentials())


def build_query(since_epoch):
    froms = []
    for src in SOURCES:
        froms.extend(src["from"])
    q = "(" + " OR ".join("from:" + f for f in froms) + ")"
    q += " after:{}".format(since_epoch)
    q += "".join(" -from:" + b for b in BLOCKED)
    return q


def source_of(sender):
    s = (sender or "").lower()
    for src in SOURCES:
        if any(f in s for f in src["from"]):
            return src
    return {"key": "other", "quality": 3, "from": []}


def walk_parts(payload, out):
    mime = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")
    if data and mime in ("text/plain", "text/html"):
        try:
            out.append((mime, base64.urlsafe_b64decode(data).decode("utf-8", "replace")))
        except Exception:
            pass
    for part in payload.get("parts", []) or []:
        walk_parts(part, out)
    return out


# --------------------------------------------------------------- link parsing
def is_job_url(url):
    return bool(JOB_URL.search(url or ""))


def is_redirect(url):
    u = url.lower().split("://", 1)[-1]
    return any(u.startswith(h) or h in u for h in REDIRECT_HOSTS)


def resolve(url):
    """Follow a click-tracker to its destination. HEAD first; some trackers only
    redirect on GET, so fall back to a GET whose body we never read."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method,
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=8) as resp:
                final = resp.geturl()
            if final and final != url:
                return final
        except Exception as e:
            final = getattr(getattr(e, "url", None), "__str__", lambda: "")()
            if final and final != url:
                return final
    return url


def clean_text(html):
    txt = TAG.sub(" ", html or "")
    txt = (txt.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#39;", "'")
              .replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", txt).strip()


def links_from_body(bodies):
    """[(url, anchor_text)] in document order, NOT deduped by url.

    Alert mail links the same posting several times -- an image anchor with no
    text, then the company name, then the title. Deduping here would keep the
    empty one and throw the title away, which is exactly the bug this signature
    exists to avoid. Grouping happens in harvest, after the best text is known.
    """
    found = []
    for mime, body in bodies:
        if mime == "text/html":
            for href, inner in ANCHOR.findall(body):
                href = href.replace("&amp;", "&").strip()
                if href.startswith("http"):
                    found.append((href, clean_text(inner)[:120]))
        else:
            for url in BARE_URL.findall(body):
                found.append((url.rstrip(".,)"), ""))
    return found[:MAX_LINKS_PER_MSG * 8]


TITLEISH = re.compile(
    r"engineer|developer|analyst|intern|scientist|architect|administrator"
    r"|specialist|consultant|manager|researcher|security|software|data|cloud"
    r"|devops|sre|associate|graduate|co-?op", re.I)
COMPANYISH = re.compile(r"^[A-Z][\w&.,'()\- ]{1,40}$")


def same_job(a, b):
    a, b = re.sub(r"[^a-z0-9]", "", (a or "").lower()), re.sub(r"[^a-z0-9]", "", (b or "").lower())
    return bool(a) and bool(b) and (a in b or b in a)


def pick_title_company(texts, subject_company, subject_title):
    """Choose a title and a company out of the several anchor texts that point
    at the same posting. Best effort only -- triage opens the real posting.

    The shortest title-ish text wins, not the longest: Jobright's card mashes
    company, industry, funding stage and match % into one string ahead of the
    title, and a plain title anchor for the same job sits right next to it."""
    cands = [t for t in texts if t and not GENERIC_ANCHOR.match(t)]
    titles = [t for t in cands if TITLEISH.search(t)]
    title = min(titles, key=len) if titles else (max(cands, key=len) if cands else "")
    company = ""
    for t in sorted(cands, key=len):
        if t == title or TITLEISH.search(t) or "%" in t or "$" in t:
            continue
        if COMPANYISH.match(t) and not re.search(r"\d{3}", t):
            company = t
            break
    # Subject company belongs to the headline job only. LinkedIn alerts carry a
    # "similar jobs" block from entirely different employers; tagging those with
    # the headline company was wrong in a way that survives into the tracker.
    if not company and subject_company and same_job(title, subject_title):
        company = subject_company
    # Jobright card with no plain title anchor beside it:
    # "Everpure Computer Software - Late Stage 90% Associate Security Engineer"
    card = re.match(r"^(?P<co>.{2,60}?)\s*[·|]\s*[^%]{0,40}?(\d{2,3})%\s*(?P<t>.+)$",
                    title or "")
    if card:
        title = card.group("t").strip()
        company = company or card.group("co").strip()

    # "Machine Learning Engineer $91K/yr - $146K/yr" -> title + kept pay note
    pay = re.search(r"\$\s?\d+[KkMm].{0,25}", title or "")
    if pay:
        title = title[:pay.start()].strip()
    return title.strip(" -|,"), (company or "").strip(" -|,"), (pay.group(0).strip() if pay else "")


def parse_subject(subject, source_key):
    """(company, title) from the subject line, best effort -- blanks are fine,
    the triage step reads the real posting anyway."""
    s = (subject or "").strip()
    m = re.match(r"^(.+?) is hiring:?\s*(.+)$", s, re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^(.+?)\s+job at\s+(.+?)\s*$", s, re.I)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    m = re.match(r"^(.+?)\s+opening at\s+(.+?)\s*$", s, re.I)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    if source_key == "jobright":
        m = re.search(r"[“\"]([^”\"]+)[”\"]", s)
        if m:
            return "", m.group(1).strip()
    return "", ""


def match_pct(subject, texts):
    """The card's own match %, not the subject's -- a Jobright digest headlines
    one job's score and then lists others with different ones."""
    for t in texts or []:
        m = re.search(r"\b(\d{2,3})\s*%", t)
        if m:
            return min(100, int(m.group(1)))
    m = re.search(r"(\d{2,3})\s*%\s*match", subject or "", re.I)
    return min(100, int(m.group(1))) if m else None


def canonical(url):
    m = re.search(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)", url, re.I)
    if m:
        return "https://www.linkedin.com/jobs/view/" + m.group(1)
    return url.split("?utm_")[0]


# -------------------------------------------------------------------- dedupe
def known_urls():
    """Everything already queued, already processed, or already applied to."""
    known = set()
    for base, _dirs, files in os.walk(SWEEP_FEED):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            try:
                with io.open(os.path.join(base, fn), encoding="utf-8") as fh:
                    rec = json.load(fh)
                if rec.get("url"):
                    known.add(norm_url(rec["url"]))
            except Exception:
                continue
    try:
        with io.open(TRACKER, encoding="utf-8") as fh:
            for url in BARE_URL.findall(fh.read()):
                known.add(norm_url(url.rstrip(".,)|")))
    except Exception:
        pass
    return known


# ------------------------------------------------------------------- harvest
def since_epoch(spec, state):
    now = datetime.datetime.now(datetime.timezone.utc)
    floor = now - datetime.timedelta(days=3)
    if spec and spec != "auto":
        days = int(re.sub(r"[^0-9]", "", spec) or 1)
        start = now - datetime.timedelta(days=min(days, 3))
    elif state.get("last_run"):
        try:
            start = datetime.datetime.fromisoformat(state["last_run"])
        except Exception:
            start = floor
    else:
        start = floor
    start = max(start, floor)
    return int(start.timestamp()), start


def cmd_harvest(args):
    state = load_state()
    epoch, start = since_epoch(args.since, state)
    try:
        service = get_service()
    except Exception as e:
        print("TOKEN_ERROR {}".format(e))
        print("run: python gmail_auth.py   (token expires every 7 days while the "
              "OAuth app is in Testing)")
        return 2

    query = build_query(epoch)
    # Stamped BEFORE the list call: mail that lands while this run is reading
    # belongs to the next window, not to nobody.
    run_started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    msgs, token, truncated = [], None, False
    try:
        while True:
            resp = service.users().messages().list(
                userId="me", q=query, pageToken=token,
                maxResults=min(100, args.max_msgs)).execute()
            msgs.extend(resp.get("messages", []))
            token = resp.get("nextPageToken")
            if not token:
                break
            if len(msgs) >= args.max_msgs:
                truncated = True
                break
    except Exception as e:
        print("TOKEN_ERROR {}".format(e))
        return 2

    seen_msgs = set(state.get("seen_msgs", []))
    seen_urls = set(state.get("seen_urls", []))
    already = known_urls()

    candidates = {}
    stats = {"messages": 0, "skipped_correspondence": 0, "links": 0,
             "dup_queue": 0, "dup_seen": 0}

    for m in msgs:
        if m["id"] in seen_msgs:
            continue
        try:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full").execute()
        except Exception:
            continue
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        sender, subject = headers.get("from", ""), headers.get("subject", "")
        if any(b in sender.lower() for b in BLOCKED):
            continue
        if NOT_AN_ALERT.search(subject):
            stats["skipped_correspondence"] += 1
            seen_msgs.add(m["id"])
            continue

        src = source_of(sender)
        co_subj, title_subj = parse_subject(subject, src["key"])
        stats["messages"] += 1
        seen_msgs.add(m["id"])

        bodies = walk_parts(msg["payload"], [])
        raw, wrapped = {}, {}
        for url, anchor in links_from_body(bodies):
            if is_job_url(url):
                raw.setdefault(canonical(url), []).append(anchor)
            elif is_redirect(url) and len(wrapped) < MAX_RESOLVE:
                wrapped.setdefault(url, []).append(anchor)

        # Click-trackers hide the posting URL; Dice in particular puts the title
        # on the wrapped link and the bare link elsewhere with no text at all.
        if wrapped:
            with ThreadPoolExecutor(max_workers=8) as pool:
                finals = list(pool.map(resolve, list(wrapped)))
            for src_url, final in zip(list(wrapped), finals):
                if is_job_url(final):
                    raw.setdefault(canonical(final), []).extend(wrapped[src_url])

        for url, texts in raw.items():
            title, company, pay = pick_title_company(texts, co_subj, title_subj)
            # The subject names a job only when the mail is about ONE job.
            if not title and len(raw) == 1:
                title = title_subj or clean_text(subject)[:110]
            if not company and len(raw) == 1:
                company = co_subj
            candidates[url] = {
                "source": src["key"], "quality": src["quality"],
                "company": company[:60], "title": title[:110], "pay": pay,
                "subject": subject, "url": url,
                "match": match_pct(subject, texts),
                "date": headers.get("date", ""),
            }

    # Rows surfaced by an earlier harvest and never decided on (`seen`) or queued.
    # The message ids are already in seen_msgs, so without this list a deferred
    # row -- over the opening cap, stale-but-interesting, a crashed triage --
    # could never come back.
    pending = state.get("pending") or {}
    now = datetime.datetime.now(datetime.timezone.utc)
    carried = 0
    out = []
    for h, row in list(pending.items()):
        try:
            age = now - datetime.datetime.fromisoformat(row.get("first_seen"))
        except Exception:
            age = datetime.timedelta(0)
        if (h in seen_urls or norm_url(row["url"]) in already
                or age > datetime.timedelta(days=PENDING_DAYS)):
            del pending[h]
        elif row["url"] not in candidates:
            out.append(row)
            carried += 1

    for url, row in candidates.items():
        stats["links"] += 1
        if norm_url(url) in already:
            stats["dup_queue"] += 1
            continue
        if uhash(url) in seen_urls:
            stats["dup_seen"] += 1
            continue
        row["first_seen"] = pending.get(uhash(url), {}).get("first_seen") or run_started
        pending[uhash(url)] = row
        out.append(row)

    out.sort(key=lambda r: (r["quality"], -(r["match"] or 0)))

    # A truncated list dropped the OLDEST mail. Leaving last_run where it was
    # keeps that mail inside the next window; seen_msgs stops re-reading the rest.
    if not truncated:
        state["last_run"] = run_started
    state["seen_msgs"] = sorted(seen_msgs)
    state["pending"] = pending
    save_state(state)

    if args.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    elif not out:
        print("NONE")
    else:
        for r in out:
            print("{} | {} | {} | {} | {}".format(
                r["source"], r["company"] or "?",
                (r["title"] or "?") + (" " + r["pay"] if r.get("pay") else ""),
                "{}%".format(r["match"]) if r["match"] else "-", r["url"]))
    print("-- {} alert messages since {} ({} correspondence skipped); {} job links, "
          "{} already queued/applied, {} seen before, {} new, {} carried over undecided".format(
              stats["messages"], start.strftime("%Y-%m-%d %H:%M UTC"),
              stats["skipped_correspondence"], stats["links"],
              stats["dup_queue"], stats["dup_seen"], len(out) - carried, carried))
    if truncated:
        print("-- WARNING: more than {} messages in the window; oldest not read yet. "
              "Run harvest again to continue.".format(args.max_msgs))
    return 0


# ------------------------------------------------------------------- enrich
CRITERIA = re.compile(
    r"(Seniority level|Employment type|Job function|Industries)\s*(.{0,60}?)\s*(?="
    r"Seniority level|Employment type|Job function|Industries|Referrals|$)", re.I)
FLAGS = (
    ("CLEARANCE", r"security clearance|ts/sci|top secret|public trust|polygraph"),
    ("US-PERSON", r"u\.?s\.? citizen|us person|citizenship (is )?required|green card holder"),
    ("NO-SPONSOR", r"(not|unable to|cannot|will not)[^.]{0,40}sponsor|no sponsorship|"
                   r"without (the need for )?sponsorship|sponsorship is not"),
    ("SPONSORS", r"(will|can|do) sponsor|visa sponsorship (is )?available"),
)
YOE = re.compile(r"(\d{1,2})\+?\s*(?:-\s*\d{1,2}\s*)?years?[^.]{0,30}experience", re.I)
PAY = re.compile(r"\$\s?\d{2,3}(?:,\d{3})?(?:K)?\s*(?:-|to|–)\s*\$?\s?\d{2,3}(?:,\d{3})?(?:K)?", re.I)


_throttle = threading.Lock()
_last_call = [0.0]


def _paced_get(url, min_gap):
    """LinkedIn's guest endpoint 429s hard past ~30 quick requests, so calls are
    spaced globally and retried with backoff rather than fanned out wide."""
    for attempt in range(4):
        with _throttle:
            wait = min_gap - (time.time() - _last_call[0])
            if wait > 0:
                time.sleep(wait)
            _last_call[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise
            time.sleep(4 * (attempt + 1) ** 2)
    raise RuntimeError("unreachable")


def fetch_linkedin(url, min_gap=1.0):
    m = re.search(r"jobs/view/(\d+)", url)
    if not m:
        return None
    api = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + m.group(1)
    raw = _paced_get(api, min_gap)
    text = clean_text(raw)
    # Everything after the sign-in furniture is the actual posting body.
    body = text.split("Show more", 1)[0]
    head = body[:400]
    out = {"url": url}
    # The header reads "<title> <company> <location> <N> ago". Company is the
    # only anchor LinkedIn repeats verbatim, so find it first and cut around it.
    m = (re.search(r"See who (.+?) has hired for this role", head)
         or re.search(r"role at (.+?) (?:Email|Sign|Join)", head))
    if m:
        company = m.group(1).strip()
        out["company"] = company
        m2 = re.match(r"^\s*(?P<title>.+?)\s+" + re.escape(company) +
                      r"\s+(?P<loc>.+?)\s+(?:Over\s+)?\d+\s+"
                      r"(?:second|minute|hour|day|week|month)s?\s+ago", head)
        if m2:
            out["title"] = m2.group("title").strip()
            out["location"] = m2.group("loc").strip()
    age = re.search(r"(\d+)\s+(day|week|month|hour|minute)s?\s+ago", head, re.I)
    out["posted"] = age.group(0) if age else "?"
    appl = re.search(r"(\d+)\s+applicants?", head, re.I)
    out["applicants"] = appl.group(1) if appl else "?"
    flags = [name for name, pat in FLAGS if re.search(pat, body, re.I)]
    yoe = YOE.search(body)
    if yoe:
        flags.append("YOE:" + yoe.group(1))
    pay = PAY.search(body)
    if pay:
        flags.append("PAY:" + pay.group(0).replace(" ", ""))
    out["flags"] = flags
    out["body"] = body
    return out


def cmd_enrich(args):
    """Cheap triage data for LinkedIn postings, straight from the public guest
    endpoint -- no login, no browser, no scraper that LinkedIn blocks. Anything
    else prints NEEDS-OPEN for a subagent to fetch."""
    urls = args.urls
    if urls == ["-"]:
        # harvest's trailer ("-- N alert messages ...") and "NONE" are not rows
        urls = [ln.strip().split(" | ")[-1] for ln in sys.stdin if ln.strip()]
        urls = [u for u in urls if u.startswith("http")]
        if not urls:
            print("NONE")
            return 0
    jobs, others = [u for u in urls if "linkedin.com" in u], [u for u in urls if "linkedin.com" not in u]

    try:
        with io.open(ENRICH_CACHE, encoding="utf-8") as fh:
            cache = json.load(fh)
    except Exception:
        cache = {}

    def one(u):
        if u in cache and not args.body:
            return cache[u]
        try:
            r = fetch_linkedin(u, args.gap)
            cache[u] = {k: v for k, v in r.items() if k != "body"}
            return r
        except Exception as e:
            return {"url": u, "error": str(e)[:60]}

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, jobs))
    with io.open(ENRICH_CACHE, "w", encoding="utf-8") as fh:
        json.dump(dict(list(cache.items())[-800:]), fh)
    for r in results:
        if not r or r.get("error"):
            print("ERROR | {} | {}".format((r or {}).get("url", "?"), (r or {}).get("error", "?")))
            continue
        if args.body:
            print("=== {}\n{}\n".format(r["url"], r["body"][:args.body]))
            continue
        print("{} | {} | {} | posted {} | {} applicants | {} | {}".format(
            r.get("company", "?"), r.get("title", "?"), r.get("location", "?"),
            r["posted"], r["applicants"], ",".join(r["flags"]) or "-", r["url"]))
    for u in others:
        print("NEEDS-OPEN | {}".format(u))
    return 0


def cmd_seen(args):
    state = load_state()
    urls = set(state.get("seen_urls", []))
    added = 0
    for url in args.urls:
        h = uhash(url)
        if h not in urls:
            urls.add(h)
            added += 1
    state["seen_urls"] = sorted(urls)
    pending = state.get("pending") or {}
    for url in args.urls:
        pending.pop(uhash(url), None)
    state["pending"] = pending
    save_state(state)
    print("seen: {} added, {} total".format(added, len(urls)))
    return 0


def cmd_sources(args):
    for src in SOURCES:
        print("{:<11} quality={}  {}".format(src["key"], src["quality"],
                                             ", ".join(src["from"])))
    print("blocked: " + ", ".join(BLOCKED))
    state = load_state()
    last = state.get("last_run")
    try:
        hours = (datetime.datetime.now(datetime.timezone.utc)
                 - datetime.datetime.fromisoformat(last)).total_seconds() / 3600.0
        print("last harvest: age={:.1f}h ({} UTC) | {} undecided rows pending".format(
            hours, last[:16], len(state.get("pending") or {})))
    except Exception:
        print("last harvest: never")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harvest")
    h.add_argument("--since", default="auto", help="auto (default) or <N>d, capped at 3d")
    h.add_argument("--max-msgs", type=int, default=120)
    h.add_argument("--json", action="store_true")
    h.set_defaults(fn=cmd_harvest)
    e = sub.add_parser("enrich")
    e.add_argument("urls", nargs="+", help="posting URLs, or - to read harvest lines on stdin")
    e.add_argument("--body", type=int, default=0, help="print N chars of the posting body instead")
    e.add_argument("--gap", type=float, default=1.0, help="min seconds between LinkedIn calls")
    e.set_defaults(fn=cmd_enrich)
    s = sub.add_parser("seen")
    s.add_argument("urls", nargs="+")
    s.set_defaults(fn=cmd_seen)
    sub.add_parser("sources").set_defaults(fn=cmd_sources)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
