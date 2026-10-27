#!/usr/bin/env python3
"""jobkit — cheap reads for the /apply-job skill.

Every subcommand exists to replace a large file read with a small stdout payload.
Run with no arguments for usage.

  dup <url> [--company C] [--role R]   MATCH <row> (same URL) | FUZZY SAME_REQ <id> <row> (duplicate) |
                                        FUZZY DIFFERENT_REQ <new> vs <old> <row> (not a duplicate) |
                                        FUZZY UNKNOWN_REQ <new|?> vs <old|?> <row> (judge on location/team) |
                                        NONE. FUZZY compares requisition ids parsed from both URLs
                                        (Greenhouse, Lever, Ashby, Workday, SmartRecruiters, iCIMS, Oracle,
                                        Taleo, UKG, Paylocity, Phenom, Eightfold, Dayforce, generic).
  gate <url> --source S [--force] [--stale-ok]
                                        G1 posted, G2 dup, G3 meta, G4 dup+company/role, G5 employer cap,
                                        G6 triage in one call. First line: GATE PASS | folder= company= role=
                                        location= platform= pay= apply= posted=<date> (<N> days,
                                        <confidence>) employer= (then '  note:' / '  unsure:' /
                                        '  dup:' lines), or GATE STOP G# STALE|DUPLICATE|CLOSED|AT_CAP|SKIP |
                                        reason | details, or GATE NO_META | posted= | dup=NONE. The folder is
                                        written only after G4/G5 pass. --force: triage SKIP (and a prior
                                        skipped/held row) reported, not stopped. --stale-ok: the user said yes.
  count                                 non-skipped application count
  pool tex                              content-pool.tex minus the two note blocks
  pool notes [entry]                    just those note blocks (factual audit)
  pool entry <name>                     one Experience/Project entry plus its alternate framings
  qa list                               the 23 story headings
  qa get <substr>                       one story body
  pagefit <pdf>                         page count + bottom whitespace + verdict
  atsfix <pdf>                          rewrite ToUnicode maps so hyphens extract as ASCII '-'
  atscheck <pdf>                        ATS text-layer check: non-ASCII hyphens and odd glyphs
  similar <job-posting.md> [--company C] best prior application to reuse
  schema <url>                          ATS application-form schema, compact
  posted <url>                          original posting date + age in days + verdict
  insights                              conversion table over the whole corpus
  sweep-list                            pending job-matcher-feed candidates, by score desc
  sweep-done <job_id>                   mark a swept candidate as processed
  sweep-prune [--days N]                move feed candidates older than N days (default 3) to processed/
  scan-add                              stdin: JSON array of manually-browsed jobs -> feed queue
  track add|set|active|employer|audit|migrate
                                        tracker writes and reads -- the ONLY way rows change

  From jobprep.py (the deterministic half of prep; see its docstring for detail):
  meta <url> [--write]                  posting facts from the ATS job API; --write makes the folder
  triage <folder|job-posting.md>        SKIP / PASS / UNSURE on the eligibility rules, regex only
  formpack <folder> --company ...       writes the static part of form-pack.md
  audit <tex>                           every number in the tailored resume must exist in pool/profile
  salary "<pay line>"|none              desired-salary rows (free text, number, min/max) for a band
  skills <folder|job-posting.md> [--pdf P] keyword coverage against master/skills-inventory.md
  base use|set|list [track] [folder]    track base resumes (security, software, ai) in bases/
  fail add|list|close [id]              the failure log (failures.md)
"""
import argparse
import contextlib
import datetime
import io
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL = os.path.join(ROOT, "master", "content-pool.tex")
QABANK = os.path.join(ROOT, "qa-bank.md")
SWEEP_FEED = os.path.join(ROOT, "job-matcher-feed")

import jobtrack
COLS = jobtrack.COLS
APPS = jobtrack.APPS            # JOBKIT_APPS_ROOT redirects it (tests); default ROOT/applications

# Comment blocks stripped from `pool tex`. Matched against the block's title
# line, never by line number -- the user edits this file and line numbers drift.
STRIP_BLOCKS = ("NOT ON THE RESUME", "VERIFIED PROJECT METRICS")
FENCE = re.compile(r"^%=====")


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------- tracker

def tracker_rows():
    return jobtrack.rows()


# Query keys that identify nothing about the job -- referral/campaign tracking.
# Everything else in the query string is KEPT, because ATSes like Njoyn
# (xweb.asp?Jobid=...) and PeopleSoft (?JobOpeningId=...) put the job id there;
# dropping the whole query collapsed every posting on those hosts into one key
# and produced false duplicates (found 2026-08-22 on cgi.njoyn.com).
TRACKING_KEYS = {"jr_id", "src", "source", "gh_src", "ref", "referrer", "trackid",
                 "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                 "tz", "tzname", "sid", "cid", "gclid", "fbclid", "lang"}


def norm_url(u):
    """Strip scheme, www, tracking params and trailing slash so the same job
    posted under different URLs still matches -- while preserving the query
    parameters that actually identify the posting."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    # Greenhouse: boards. / job-boards. / embed?for=&token= are the same posting
    m = (re.match(r"^(?:www\.)?(?:job-)?boards\.greenhouse\.io/([^/?]+)/jobs/(\d+)", u)
         or re.match(r"^(?:www\.)?(?:job-)?boards\.greenhouse\.io/embed/job_app\?(?=.*\bfor=([^&]+))(?=.*\btoken=(\d+))", u))
    if m:
        return "greenhouse:{}/{}".format(m.group(1), m.group(2))
    u = re.sub(r"^www\.", "", u)
    u = u.split("#")[0]
    base, _, query = u.partition("?")
    base = base.rstrip("/")
    if not query:
        return base
    kept = []
    for part in query.split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        if k in TRACKING_KEYS or not v:
            continue
        kept.append(k + "=" + v)
    return base + ("?" + "&".join(sorted(kept)) if kept else "")


def norm_text(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# ------------------------------------------------------------ requisition ids
# 13 logged dup failures (F-0048, F-0056, F-0088, F-0096, F-0131 ...) were FUZZY hits on a
# different requisition at the same employer. A FUZZY hit is now checked against the req id
# each URL carries. Job boards that re-list other employers' jobs carry THEIR id, not the
# employer's, so they never produce an id (the verdict stays UNKNOWN_REQ).
AGGREGATORS = ("jobright.ai", "linkedin.com", "indeed.com", "ziprecruiter.com", "dice.com",
               "joinhandshake.com", "glassdoor.com", "google.com", "simplify.jobs", "builtin.com",
               "hiring.cafe", "wellfound.com", "ycombinator.com", "welcometothejungle.com")
_UUID = r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}"
# (kind, host substring or "", regex). First hit wins. kind "host" means ids are only
# comparable on the same host (Phenom, custom career sites, generic shapes).
REQ_PATTERNS = (
    ("greenhouse", "", r"[?&]gh_jid=(\d+)"),
    ("greenhouse", "greenhouse.io", r"greenhouse\.io/(?!embed/)[^/?#]+/jobs/(\d+)"),
    ("greenhouse", "greenhouse.io", r"[?&]token=(\d+)"),
    ("lever", "lever.co", r"lever\.co/[^/?#]+/(" + _UUID + ")"),
    ("ashby", "ashbyhq.com", r"ashbyhq\.com/[^/?#]+/(" + _UUID + ")"),
    ("workday", "myworkdayjobs.com", r"/job/(?:[^/?#]+/)?[^/?#]*_([a-z0-9-]+)"),
    ("smartrecruiters", "smartrecruiters.com", r"smartrecruiters\.com/[^/?#]+/(\d{6,})"),
    ("icims", "icims.com", r"/jobs/(\d+)"),
    ("oracle", "oraclecloud.com", r"/(?:job|preview)/(\d+)"),
    ("taleo", "taleo.net", r"[?&]job=([a-z0-9]+)"),
    ("ultipro", "", r"[?&]opportunityId=(" + _UUID + ")"),
    ("paylocity", "paylocity.com", r"/Jobs/Details/(\d+)"),
    ("dayforce", "dayforcehcm.com", r"/jobs/(\d+)"),
    ("amazon", "amazon.jobs", r"/jobs/(\d+)"),
    ("eightfold", "", r"/careers/job/(\d{6,})|/careers/job\?(?:[^#]*&)?pid=(\d+)|eightfold\.ai/.*[?&]pid=(\d+)"),
    ("successfactors", "", r"[?&]career_job_req_id=(\d+)"),
    ("host", "", r"[?&]jobSeqNo=([a-z0-9]+)"),                               # Phenom
    ("host", "", r"/job/([a-z0-9]*\d[a-z0-9]*external[a-z0-9]*)"),           # Phenom seq in path
    ("host", "", r"[?&](?:job_?id|jobopeningid|req_?id|requisition_?id|jobreqid)=([a-z0-9_-]+)"),
    ("host", "", r"/jobs?/(\d{3,})(?=[/?#-]|$)"),                            # Phenom /job/<id>/, custom sites
    ("host", "", r"/(?:j|jobs?)/([a-z0-9]{6,})(?=[/?#]|$)"),                 # Workable /j/<code>, Jobvite
    ("host", "", r"(" + _UUID + ")"),
)
REQ_TOKEN = re.compile(r"(?<![a-z0-9])((?:jr|req|r)[-_]?\d{4,})", re.I)   # JR63439, R-113509, REQ_100


def _norm_id(s):
    s = re.sub(r"(?<=\d{4})[-_]\d{1,2}$", "", s or "")      # Workday/Paradox repost suffix: R171675-1
    s = re.sub(r"[^A-Za-z0-9]", "", s).upper()
    return (s.lstrip("0") or "0") if s.isdigit() else s


def req_id(url):
    """{"kind", "id", "ids"} for the requisition a job URL points at. `id` is the primary id (None when
    nothing is extractable); `ids` adds req-like tokens (JR63439) and the long digit core of each id,
    so the same req on a second ATS (Paradox job_id=JR63439_1 vs Workday ..._JR63439) still overlaps."""
    u = (url or "").strip().rstrip(".,;)*>")
    parsed = urllib.parse.urlparse(u if "://" in u else "https://" + u)
    host = re.sub(r"^www\.", "", parsed.netloc.lower().split(":")[0])
    if any(host == a or host.endswith("." + a) for a in AGGREGATORS):
        return {"kind": "aggregator:" + host, "id": None, "ids": set()}
    kind = rid = None
    for k, hostpart, pat in REQ_PATTERNS:
        if hostpart and hostpart not in host:
            continue
        m = re.search(pat, u, re.I)
        if m:
            rid = next(g for g in m.groups() if g)
            kind = k if k != "host" else "host:" + host
            break
    if not rid:                                     # generic: longest digit run of 5+
        runs = re.findall(r"\d{5,}", norm_url(u).partition("/")[2])
        if runs:
            rid, kind = max(runs, key=len), "host:" + host
    ids = set()
    for tok in ([rid] if rid else []) + REQ_TOKEN.findall(u):
        n = _norm_id(tok)
        ids.add(n)
        runs = re.findall(r"\d{5,}", n)
        if runs:
            ids.add("#" + (max(runs, key=len).lstrip("0") or "0"))
    return {"kind": kind, "id": _norm_id(rid) if rid else None, "ids": ids}


def _row_urls(r):
    """Every URL that identifies a tracker row's posting: the Link column plus the URL /
    Apply URL lines of its folder's job-posting.md (read-only; live folder or JOBKIT_APPS_ROOT)."""
    urls = re.findall(r"https?://[^\s|]+", r.get("link", ""))
    folder = (r.get("folder") or "").strip().rstrip("/")
    if folder and folder.lower() != "none":
        for base in (os.path.join(APPS, os.path.basename(folder)), os.path.join(ROOT, folder)):
            p = os.path.join(base, "job-posting.md")
            if os.path.exists(p):
                head = read(p).split("\n---\n", 1)[0]
                for line in head.splitlines():
                    if "url" in line.lower():
                        urls += re.findall(r"https?://[^\s|)*>]+", line)
                break
    return urls


def req_compare(new_url, old_urls):
    """(verdict, new id, old id) with verdict SAME_REQ, DIFFERENT_REQ or UNKNOWN_REQ.
    DIFFERENT_REQ needs an id of the SAME kind on both sides (two Oracle job ids, two Greenhouse
    tokens); ids from different ATSes are not comparable, so those stay UNKNOWN_REQ."""
    n = req_id(new_url)
    olds = [req_id(u) for u in old_urls]
    for o in olds:
        shared = n["ids"] & o["ids"]
        if shared:
            return "SAME_REQ", n["id"] or sorted(shared)[0], o["id"] or sorted(shared)[0]
    same_kind = [o for o in olds if o["id"] and o["kind"] == n["kind"]]
    if n["id"] and same_kind:
        return "DIFFERENT_REQ", n["id"], same_kind[0]["id"]
    return "UNKNOWN_REQ", n["id"], next((o["id"] for o in olds if o["id"]), None)


_CO_STOP = {"the", "company", "inc", "llc", "ltd", "corp", "corporation", "group", "holdings",
            "technologies", "technology", "systems", "solutions", "services", "international",
            "global", "usa", "america", "labs", "careers"}


def _co_tokens(s):
    return {t for t in norm_text(s).split() if len(t) >= 4 and t not in _CO_STOP}


def dup_check(url, company="", role=""):
    """The dup logic, structured: {"verdict": MATCH|FUZZY|NONE, "req": SAME_REQ|DIFFERENT_REQ|
    UNKNOWN_REQ (FUZZY only), "row", "new_id", "old_id", "more"}."""
    target = norm_url(url)
    rows = tracker_rows()
    for r in rows:
        for u in re.findall(r"https?://\S+", r["link"]):
            if norm_url(u) == target:
                return {"verdict": "MATCH", "row": r}
    if not company:
        return {"verdict": "NONE"}
    co, role_n = norm_text(company), norm_text(role)
    hits = []
    for r in rows:
        if norm_text(r["company"]) != co:
            continue
        if not role_n or role_n in norm_text(r["role"]) or norm_text(r["role"]) in role_n:
            hits.append((r,) + req_compare(url, _row_urls(r)))
    # Same requisition under a looser employer name ("The William Carter Company" vs "Carter's",
    # F-0096): only an id overlap counts here, never the title.
    if req_id(url)["ids"]:
        toks = _co_tokens(company)
        for r in rows:
            if toks & _co_tokens(r["company"]) and norm_text(r["company"]) != co:
                v = req_compare(url, _row_urls(r))
                if v[0] == "SAME_REQ":
                    hits.append((r,) + v)
    if not hits:
        return {"verdict": "NONE"}
    rank = {"SAME_REQ": 0, "UNKNOWN_REQ": 1, "DIFFERENT_REQ": 2}
    hits.sort(key=lambda h: rank[h[1]])
    r, verdict, new_id, old_id = hits[0]
    return {"verdict": "FUZZY", "req": verdict, "row": r, "new_id": new_id, "old_id": old_id,
            "more": len(hits) - 1}


def fmt_dup(res):
    if res["verdict"] == "MATCH":
        return fmt_row(res["row"])
    if res["verdict"] == "NONE":
        return "NONE"
    ids = {"SAME_REQ": "{new_id}", "DIFFERENT_REQ": "{new_id} vs {old_id}",
           "UNKNOWN_REQ": "{new_id} vs {old_id}"}[res["req"]].format(
        new_id=res["new_id"] or "?", old_id=res["old_id"] or "?")
    more = " | +{} more same-employer row(s)".format(res["more"]) if res["more"] else ""
    return "FUZZY {} {} | {}{}".format(res["req"], ids, fmt_row(res["row"])[len("MATCH | "):], more)


def cmd_dup(args):
    print(fmt_dup(dup_check(args.url, args.company, args.role)))
    return 0


def fmt_row(r):
    return "MATCH | {date} | {company} | {role} | status: {status} | {folder}".format(**r)


def cmd_count(args):
    rows = tracker_rows()
    sent = [r for r in rows if r["status"] in jobtrack.SENT]
    open_ = [r for r in rows if r["status"] in jobtrack.OPEN]
    print("total={} sent={} open={} skipped={}".format(
        len(rows), len(sent), len(open_),
        sum(1 for r in rows if r["status"] in ("skipped", "duplicate"))))
    return 0


# ------------------------------------------------------------------------ pool

def split_pool():
    """Return (kept_text, stripped_text).

    A note block is a fenced banner -- `%====`, one or more title lines, `%====`
    -- followed by its body, which runs to the fence that opens the next block
    (or EOF). Title lines are matched against STRIP_BLOCKS; line numbers are
    never used, since the user edits this file and they drift.
    """
    lines = read(POOL).splitlines()

    def scan_to_fence(k):
        while k < len(lines) and not FENCE.match(lines[k]):
            k += 1
        return k

    kept, dropped, i = [], [], 0
    while i < len(lines):
        if FENCE.match(lines[i]):
            close = scan_to_fence(i + 1)          # end of the banner's title
            banner = "\n".join(lines[i + 1:close])
            if any(m in banner for m in STRIP_BLOCKS):
                end = scan_to_fence(close + 1)    # end of the block's body
                dropped.extend(lines[i:end])
                i = end
                continue
        kept.append(lines[i])
        i += 1
    return "\n".join(kept).rstrip() + "\n", "\n".join(dropped).rstrip() + "\n"


def cmd_pool(args):
    kept, dropped = split_pool()
    if args.what == "entry":
        # One Experience/Project entry plus its alternate framings -- for a run
        # that started from a track base and needs to swap one entry in.
        key = norm_text(args.entry)
        if not key:
            print("usage: pool entry \"<employer or project name>\"")
            return 1
        lines, out, block = kept.splitlines(), [], []

        def flush():
            if block and key in norm_text(" ".join(block)):
                out.extend(block + [""])

        for line in lines:
            if (line.startswith("% RELEVANCE:") or re.match(r"^%\s*---", line)
                    or line.startswith("\\end{rSection}") or FENCE.match(line)):
                flush()
                block = []
            block.append(line)
        flush()
        sys.stdout.write("\n".join(out) + "\n" if out else "NONE no pool entry matches '{}'\n".format(args.entry))
        return 0
    if args.what == "tex":
        sys.stdout.write(kept)
    else:
        if args.entry:
            key = norm_text(args.entry)
            out, keep = [], False
            for line in dropped.splitlines():
                if re.match(r"^%\s*---|^%\s{0,3}\w.*---", line):
                    keep = key in norm_text(line)
                if key in norm_text(line):
                    keep = True
                if keep:
                    out.append(line)
            sys.stdout.write("\n".join(out) + "\n" if out else dropped)
        else:
            sys.stdout.write(dropped)
    return 0


# --------------------------------------------------------------------- qa-bank

def qa_sections():
    out, project = [], ""
    for n, line in enumerate(read(QABANK).splitlines(), 1):
        if line.startswith("## ") and not line.startswith("###"):
            project = line[3:].strip()
        elif line.startswith("### "):
            out.append((n, project, line[4:].strip()))
    return out


def cmd_qa(args):
    entries = qa_sections()
    if args.what == "list":
        for n, project, title in entries:
            print("{:>4}  {} :: {}".format(n, project[:38], title))
        print("\n{} stories. Use `qa get <substring>` for one or two -- never more.".format(len(entries)))
        return 0

    key = norm_text(args.story)
    hits = [e for e in entries if key in norm_text(e[2]) or key in norm_text(e[1] + " " + e[2])]
    if not hits:
        print("NO MATCH. Run `qa list` and use a substring of a heading.", file=sys.stderr)
        return 1
    lines = read(QABANK).splitlines()
    starts = [e[0] for e in entries]
    for n, project, title in hits[:2]:
        nxt = next((s for s in starts if s > n), len(lines) + 1)
        print("## {}".format(project))
        print("\n".join(lines[n - 1:nxt - 1]).rstrip())
        print()
    if len(hits) > 2:
        print("({} more matched; narrow the substring)".format(len(hits) - 2), file=sys.stderr)
    return 0


# --------------------------------------------------------------------- pagefit

FULL_THRESHOLD_PT = 40.0


def cmd_pagefit(args):
    from pypdf import PdfReader
    reader = PdfReader(args.pdf)
    page = reader.pages[-1]
    height = float(page.mediabox.height)
    ys = []

    def visit(text, cm, tm, font_dict, font_size):
        if text.strip():
            ys.append(tm[4] * cm[1] + tm[5] * cm[3] + cm[5])

    page.extract_text(visitor_text=visit)
    if not ys:
        print("ERROR: no text found in {}".format(args.pdf), file=sys.stderr)
        return 1
    gap = min(ys)
    pages = len(reader.pages)
    if pages > 1:
        verdict = "OVERFLOW"
    elif gap <= FULL_THRESHOLD_PT:
        verdict = "FULL"
    else:
        verdict = "SHORT"
    print("pages={} gap={:.0f}pt ({:.1f}%) verdict={}".format(
        pages, gap, gap / height * 100, verdict))
    return 0 if verdict == "FULL" else 2


# --------------------------------------------------------------------- atscheck
#
# Added 2026-08-30. The compiled PDF looks perfect on screen but an ATS reads
# the *extracted text layer*, and XeTeX + Calibri emits U+2010 HYPHEN for every
# literal "-" in the source. A parser searching the ASCII string "scikit-learn",
# "full-stack" or "AB1-234" does not match "scikit‐learn". Same class of
# problem for the U+22C4 diamond separator on the contact line. This command
# reads what the machine reads, not what the eye sees.

# chars that are fine in an extracted resume: real bullets, en/em dash between
# dates, curly apostrophe, tilde. Everything else non-ASCII gets reported.
ATS_BENIGN = {0x2022, 0x2013, 0x2014, 0x2019, 0x223C, 0x22C4}
ATS_HYPHENS = {0x2010, 0x2011, 0x2012, 0x2212, 0xFE63, 0xFF0D}


def cmd_atscheck(args):
    from pypdf import PdfReader
    reader = PdfReader(args.pdf)
    text = "\n".join(p.extract_text() or "" for p in reader.pages)

    bad_hyphen = sum(text.count(chr(c)) for c in ATS_HYPHENS)
    other = {}
    for ch in text:
        o = ord(ch)
        if o > 127 and o not in ATS_BENIGN and o not in ATS_HYPHENS:
            other[ch] = other.get(ch, 0) + 1

    # tokens that carry a non-ASCII hyphen AND look like a searchable keyword
    import re
    broken = []
    for tok in re.findall(r"\S*[" + "".join(chr(c) for c in ATS_HYPHENS) + r"]\S*", text):
        tok = tok.strip(".,;:()")
        if any(ch.isdigit() or ch.isupper() for ch in tok) or "." in tok:
            if tok not in broken:
                broken.append(tok)

    verdict = "OK" if not bad_hyphen and not other else "WARN"
    others = " ".join("{}:{}".format(k, v) for k, v in sorted(other.items(), key=lambda kv: -kv[1]))
    print("atscheck pages={} badhyphen={} other={} verdict={}".format(
        len(reader.pages), bad_hyphen, others or "none", verdict))
    for tok in broken[:12]:
        print("  keyword at risk: {}".format(tok))
    return 0 if verdict == "OK" else 2


def cmd_atsfix(args):
    """Rewrite the PDF's ToUnicode maps so hyphens extract as ASCII '-'.

    XeTeX writes Calibri's hyphen glyph and xdvipdfmx reverse-maps it to
    U+2010 HYPHEN, so every "scikit-learn" / "AB1-234" / "(555)-123-4567" in
    the text layer is invisible to an ATS searching the ASCII spelling. Only
    the ToUnicode CMap changes -- the rendered page is byte-identical visually.
    """
    import re
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    reader = PdfReader(args.pdf)
    writer = PdfWriter(clone_from=reader)
    fixed = 0
    seen = set()
    for page in writer.pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for key in list(fonts.keys()):
            font = fonts[key].get_object()
            tu = font.get("/ToUnicode")
            if tu is None:
                continue
            obj = tu.get_object()
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            data = obj.get_data().decode("latin-1")
            new = re.sub(r"(?i)<20(1[0-2]|11)>", "<002D>", data)
            new = new.replace("<2212>", "<002D>")
            if new == data:
                continue
            stream = DecodedStreamObject()
            stream.set_data(new.encode("latin-1"))
            ref = writer._add_object(stream)
            font[NameObject("/ToUnicode")] = ref
            fixed += 1

    if fixed:
        with open(args.pdf, "wb") as fh:
            writer.write(fh)
    print("atsfix {} in {}".format(
        "rewrote {} ToUnicode map(s)".format(fixed) if fixed else "no-change", args.pdf))
    # Self-verifying: one call replaces the old atscheck -> atsfix -> atscheck
    # sequence. The verdict line below is the gate.
    return cmd_atscheck(args)


# --------------------------------------------------------------------- similar
#
# Similarity is computed over the full text of `job-posting.md`, NOT over the
# tracker's "Keywords used" column. Measured 2026-08-21: that column is free
# text phrased differently every run, so true same-company duplicates scored
# 0.05-0.49 -- indistinguishable from unrelated roles. TF-IDF cosine over the
# posting bodies separates cleanly (true dups 0.33-0.64, unrelated 0.05-0.07),
# and costs zero tokens because this script reads the files locally.

STOP = set("""a an the and or of to in for with on at by is are be as we you your our this that will from
have has can they it its their who what which more all any not may must role job work team using via based
apply company position candidates candidate experience years including etc""".split())

PHASE1_THRESHOLD = 0.45   # + same company; see plan Change 8b
PHASE2_THRESHOLD = 0.35   # any company, only after 5 reviewed reuses

# Entry-tier markers. Deliberately does NOT treat "II"/"III" as entry -- only a
# lone trailing "I"/"1" counts, so "Engineer II" stays in the mid tier.
ENTRY_RE = re.compile(
    r"\b(intern|internship|junior|jr\.?|new ?grad|graduate|entry[- ]level|associate"
    r"|university|campus|early[- ]career)\b|\b(?:engineer|developer|analyst)\s+(?:i|1)\b",
    re.I)
SENIOR_RE = re.compile(r"\b(senior|sr\.?|staff|principal|lead|manager|director|ii+|[2-9])\b", re.I)


def is_entry(title):
    t = title or ""
    if SENIOR_RE.search(t) and not ENTRY_RE.search(t):
        return False
    return bool(ENTRY_RE.search(t))


def toks(text):
    return [w for w in re.sub(r"[^a-z0-9+#]+", " ", text.lower()).split()
            if w not in STOP and len(w) > 2]


def posting_index():
    """{folder_name: tfidf_vector} over every applications/*/job-posting.md."""
    from collections import Counter
    raw = {}
    for name in sorted(os.listdir(APPS)):
        path = os.path.join(APPS, name, "job-posting.md")
        if os.path.exists(path):
            try:
                raw[name] = Counter(toks(read(path)))
            except Exception:
                pass
    n = len(raw) or 1
    df = Counter()
    for c in raw.values():
        for w in c:
            df[w] += 1

    def vec(counter):
        v = {w: (1 + math.log(k)) * math.log(n / (1.0 + df[w]))
             for w, k in counter.items() if df[w] > 1}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    return {k: vec(c) for k, c in raw.items()}, df, n


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def cmd_similar(args):
    from collections import Counter
    if not os.path.exists(args.posting):
        print("ERROR: no such posting file: {}".format(args.posting), file=sys.stderr)
        return 1
    index, df, n = posting_index()
    counter = Counter(toks(read(args.posting)))
    v = {w: (1 + math.log(k)) * math.log(n / (1.0 + df[w]))
         for w, k in counter.items() if df.get(w, 0) > 1}
    norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
    query = {w: x / norm for w, x in v.items()}

    self_folder = os.path.basename(os.path.dirname(os.path.abspath(args.posting)))
    by_folder = {r["folder"].strip("/").split("/")[-1]: r for r in tracker_rows()}

    scored = []
    for folder, vec_ in index.items():
        if folder == self_folder or (args.exclude and args.exclude.strip("/") in folder):
            continue
        row = by_folder.get(folder)
        if row and row["status"] in ("skipped", "duplicate", "review"):
            continue
        scored.append((cosine(query, vec_), folder, row))
    scored.sort(reverse=True, key=lambda t: t[0])
    if not scored:
        print("NONE")
        return 0

    score, folder, row = scored[0]
    company = row["company"] if row else "?"
    role = row["role"] if row else "?"
    print("best={:.2f} | {} | {} | applications/{}".format(score, company, role[:60], folder))

    path = os.path.join(APPS, folder)
    tex = os.path.join(path, "Resume_Resume.tex")
    pdf = os.path.join(path, "Resume_Resume.pdf")
    reasons = []
    if score < args.threshold:
        reasons.append("score {:.2f} < {:.2f}".format(score, args.threshold))
    if args.company and row and norm_text(args.company) != norm_text(company):
        reasons.append("different company ({} vs {})".format(company, args.company))
    if not (os.path.exists(tex) and os.path.exists(pdf)):
        reasons.append("prior tex/pdf missing")
    elif os.path.getmtime(tex) < os.path.getmtime(POOL):
        reasons.append("STALE: content-pool.tex edited after that resume was built")
    else:
        # A base change (layout, titles) also retires older resumes, not just a pool edit.
        bases = [os.path.join(ROOT, "bases", f) for f in os.listdir(os.path.join(ROOT, "bases"))
                 if f.endswith(".tex")]
        newest = max((os.path.getmtime(b) for b in bases), default=0)
        if os.path.getmtime(tex) < newest:
            reasons.append("STALE: a base resume was edited after that resume was built")
    if args.role and row and is_entry(args.role) != is_entry(role):
        reasons.append("different seniority tier")

    print("REUSE" if not reasons else "REBUILD (" + "; ".join(reasons) + ")")
    for s2, f2, r2 in scored[1:4]:
        print("  runner-up {:.2f} {}".format(s2, f2))
    return 0


# ---------------------------------------------------------------------- schema

UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
      "Origin": "https://jobs.ashbyhq.com"}

ASHBY_QUERY = ("query A($organizationHostedJobsPageName: String!, $jobPostingId: String!) "
               "{ jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, "
               "jobPostingId: $jobPostingId) { applicationForm { sections { title "
               "fieldEntries { field isRequired } } } } }")


def detect_ats(url):
    u = url.lower()
    for pat, name in (("ashbyhq.com", "ashby"), ("greenhouse.io", "greenhouse"),
                      ("myworkdayjobs.com", "workday"), ("oraclecloud.com", "oracle-cx"),
                      ("smartrecruiters.com", "smartrecruiters"), ("icims.com", "icims"),
                      ("lever.co", "lever")):
        if pat in u:
            return name
    return "unknown"


def http_json(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cmd_schema(args):
    import jobprep
    args.url = jobprep.canonical_url(args.url)      # ?gh_jid=<id> on an employer domain -> Greenhouse
    ats = detect_ats(args.url)
    print("ats={}".format(ats))
    try:
        if ats == "greenhouse":
            m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([^/?]+).*?(\d{6,})", args.url)
            if not m:
                raise ValueError("could not parse org/job id from URL")
            org, jid = m.group(1), m.group(2)
            d = http_json("https://boards-api.greenhouse.io/v1/boards/{}/jobs/{}?questions=true"
                          .format(org, jid))
            print("title={}".format(d.get("title", "")))
            for q in d.get("questions", []):
                f = (q.get("fields") or [{}])[0]
                vals = f.get("values") or []
                print("  {} | {} | key={} | req={}{}".format(
                    (q.get("label") or "").replace("\n", " ")[:70], f.get("type"),
                    f.get("name"), q.get("required"),
                    " | opts=" + " / ".join(str(v.get("label"))[:28] for v in vals[:12]) if vals else ""))
            for block in ("demographic_questions", "compliance"):
                if d.get(block):
                    print("  [{} block present]".format(block))
        elif ats == "ashby":
            m = re.search(r"ashbyhq\.com/([^/?]+)/([0-9a-f-]{36})", args.url)
            if not m:
                raise ValueError("could not parse org/posting id from URL")
            org, pid = m.group(1), m.group(2)
            d = http_json("https://jobs.ashbyhq.com/api/non-user-graphql?op=A",
                          {"operationName": "A", "query": ASHBY_QUERY,
                           "variables": {"organizationHostedJobsPageName": org,
                                         "jobPostingId": pid}})
            if d.get("errors"):
                raise ValueError(d["errors"][0].get("message", "graphql error"))
            posting = (d.get("data") or {}).get("jobPosting")
            if not posting:
                raise ValueError("posting not found (closed?)")
            for s in posting["applicationForm"]["sections"]:
                print("  ## {}".format(s.get("title") or "(main)"))
                for e in s.get("fieldEntries", []):
                    f = e.get("field") or {}
                    vals = f.get("selectableValues") or []
                    print("    {} | {} | key={} | req={}{}".format(
                        (f.get("title") or "")[:66], f.get("type"), f.get("path"),
                        e.get("isRequired"),
                        " | opts=" + " / ".join(str(v.get("label"))[:28] for v in vals[:12]) if vals else ""))
        else:
            print("NO_SCHEMA_API — use the DOM path in ats/{}.md if it exists, else ats/_unknown.md".format(ats))
            return 3
    except Exception as exc:  # noqa: BLE001 - must fail loudly, never fill from a stale plan
        print("SCHEMA_FAILED: {} — fall back to the DOM path, do not guess".format(exc),
              file=sys.stderr)
        return 1
    return 0


# -------------------------------------------------------------------- insights

# ----------------------------------------------------------------- posting date

# whenthisjobwasposted.com -- free, no auth, 60 req/min. Plain urllib with the
# default User-Agent gets a 403, so this reuses the browser UA below.
POSTED_API = "https://mcp.whenthisjobwasposted.com/api/v1/check?url="
STALE_DAYS = 3


def cmd_posted(args):
    req = urllib.request.Request(POSTED_API + urllib.parse.quote(args.url, safe=""),
                                 headers={"User-Agent": UA["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            d = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print("UNKNOWN date=unknown reason=request_failed ({})".format(
            type(e).__name__))
        return 0

    date = d.get("most_probable_date")
    if not date:
        print("UNKNOWN date=unknown reason={}".format(d.get("reason") or "no_date_found"))
        return 0

    try:
        age = (datetime.date.today() - datetime.date(*map(int, date.split("-")))).days
    except ValueError:
        print("UNKNOWN date=unknown reason=unparsable_date")
        return 0

    print("{} date={} age={}d confidence={}".format(
        "STALE" if age > STALE_DAYS else "FRESH", date, age,
        d.get("confidence") or "unknown"))
    return 0


# ------------------------------------------------------------------------ gate

def _capture(fn, **kw):
    """Run an existing subcommand in-process; return (rc, stdout text, namespace)."""
    ns = argparse.Namespace(**kw)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(ns)
    return rc, buf.getvalue().strip(), ns


def cmd_gate(args):
    """G1-G6 in one call, one compact verdict. Each gate is the existing subcommand, run
    in-process; this function only sequences them and condenses the output."""
    import jobprep
    url, lines = args.url, []

    def row_bits(r):
        return "{date} | {company} | {role} | status: {status} | {folder}".format(**r)

    # G1 posting date
    _, out, _ = _capture(cmd_posted, url=url, timeout=args.timeout)
    m = re.match(r"(FRESH|STALE|UNKNOWN) date=(\S+)(?: age=(-?\d+)d confidence=(\S+))?", out)
    kind, date, age, conf = (m.groups() if m else ("UNKNOWN", "unknown", None, None))
    if kind == "STALE" and not args.stale_ok:
        print("GATE STOP G1 STALE | posted {} ({} days ago, confidence {}), older than {} days"
              " | ask the user; on yes rerun with --stale-ok".format(date, age, conf, STALE_DAYS))
        return 0
    if kind == "STALE":
        lines.append("  note: posted {} days ago, the user approved (--stale-ok)".format(age))
    posted_meta = "{} ({} days ago)".format(date, age) if age is not None else "unknown"
    posted = ("{} ({} days{})".format(date, age, ", " + conf if conf else "")
              if age is not None else "unknown")

    # G2 duplicate by URL
    def url_dup(u, gate):
        res = dup_check(u)
        if res["verdict"] != "MATCH":
            return False
        if args.force and res["row"]["status"] in ("skipped", "held"):
            lines.append("  dup: PRIOR_{} row for this URL, continuing on --force | {}".format(
                res["row"]["status"].upper(), row_bits(res["row"])))
            return False
        print("GATE STOP {} DUPLICATE | this URL is already in the tracker | {}".format(
            gate, row_bits(res["row"])))
        return True
    if url_dup(url, "G2"):
        return 0

    # G3 posting facts (fetched now, written after G4/G5 so a stop leaves no orphan folder)
    rc, out, ns = _capture(jobprep.cmd_meta, url=url, write=False, posted=posted_meta,
                           source=args.source)
    if rc == 4:
        print("GATE STOP G3 CLOSED | {} | open the link once to confirm; if gone, log skipped "
              "--notes \"posting closed\"".format(out.split(" -- ")[0]))
        return 0
    if rc != 0 or not getattr(ns, "result", None):
        print("GATE NO_META | posted={} | dup=NONE".format(posted))
        print("  meta: " + (out.splitlines() or ["no output"])[-1][:160])
        return 0
    meta = ns.result
    who = "company={} | role={}".format(meta["company"], meta["role"])

    # G4 duplicate by company + role (plus the canonical / apply URLs meta resolved)
    for u in dict.fromkeys((meta["url"], meta["apply_url"])):
        if norm_url(u) != norm_url(url) and url_dup(u, "G4"):
            return 0
    res = dup_check(url, meta["company"], meta["role"])     # a MATCH here was settled at G2
    if res["verdict"] == "FUZZY":
        if res["req"] == "SAME_REQ" and args.force and res["row"]["status"] in ("skipped", "held"):
            lines.append("  dup: PRIOR_{} row for this req, continuing on --force | {}".format(
                res["row"]["status"].upper(), row_bits(res["row"])))
        elif res["req"] == "SAME_REQ":
            print("GATE STOP G4 DUPLICATE | {} | {} | not written: folder=none".format(
                fmt_dup(res), who))
            return 0
        else:
            lines.append("  dup: {} | new posting location={}".format(
                fmt_dup(res), meta["location"] or "not stated"))

    # G5 employer caps
    _, emp, _ = _capture(jobtrack.cmd_track_employer, company=meta["company"], days=30)
    emp_short = emp.split(": ", 1)[-1]
    if "AT CAP" in emp:
        print("GATE STOP G5 AT_CAP | {} | {} | log held --notes \"cap\", tell the user".format(
            emp_short, who))
        return 0

    # G6 triage, on the folder written now
    path = jobprep.write_posting(meta["_j"], meta["_band"], meta["folder"], meta["url"],
                                 posted_meta, args.source)
    folder = ("applications/" + meta["folder"] if os.path.normcase(APPS) == os.path.normcase(
        os.path.join(ROOT, "applications")) else path)
    _, tri, _ = _capture(jobprep.cmd_triage, target=path)
    tri_lines = tri.splitlines() or ["UNSURE triage printed nothing"]
    head, rest = tri_lines[0], tri_lines[1:]
    also = [l.strip()[len("also: "):] for l in rest if l.strip().startswith("also: ")]
    notes = [l.strip()[len("note: "):] for l in rest if l.strip().startswith("note: ")]
    flags = [l.strip() for l in rest if not l.strip().startswith(("also: ", "note: "))]
    if head.startswith("SKIP"):
        if not args.force:
            print("GATE STOP G6 SKIP | {} | {} | folder={}{}".format(
                head[5:], who, folder, "".join(" | also: " + a for a in also)))
            return 0
        lines += ["  skip(forced): " + s for s in [head[5:]] + also]
    lines += ["  unsure: " + f for f in flags]
    lines += ["  note: " + n for n in notes]

    print("GATE PASS | folder={} | company={} | role={} | location={} | platform={} | pay={} | "
          "apply={} | posted={} | employer={}".format(
              folder, meta["company"], meta["role"], meta["location"] or "not stated",
              meta["platform"], meta["pay"], meta["apply_url"], posted, emp_short))
    for l in lines:
        print(l)
    return 0


# -------------------------------------------------------------------- sweep

def _sweep_pending():
    """Every job-matcher-feed/<track>/<date>/<job_id>.json not yet under a
    'processed' folder, parsed and sorted by overall score descending."""
    pending = []
    if not os.path.isdir(SWEEP_FEED):
        return pending
    for track in sorted(os.listdir(SWEEP_FEED)):
        track_dir = os.path.join(SWEEP_FEED, track)
        if not os.path.isdir(track_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(track_dir):
            if os.path.basename(dirpath) == "processed":
                dirnames[:] = []  # don't descend into it either
                continue
            for fn in filenames:
                if not fn.endswith(".json"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    rec = json.loads(read(path))
                except Exception:
                    continue
                rec["_path"] = path
                pending.append(rec)
    pending.sort(key=lambda r: (_feed_age(r), -((r.get("scores") or {}).get("overall", 0))))
    return pending


def _feed_age(rec):
    """Days since the candidate's best-known date: the connector's posted_at,
    else fetched_at (first seen), else the feed folder's date (scan-add rows).
    Every record has at least the folder date, so nothing is exempt from prune."""
    cands = [(rec.get("posted_at") or "")[:10], (rec.get("fetched_at") or "")[:10],
             os.path.basename(os.path.dirname(rec.get("_path", "")))]
    for p in cands:
        try:
            d = datetime.date(*map(int, p.split("-")))
            return max(0, (datetime.date.today() - d).days)
        except Exception:
            continue
    return 0


def cmd_sweep_prune(args):
    moved = 0
    for rec in _sweep_pending():
        if _feed_age(rec) > args.days:
            track_dir = os.path.dirname(os.path.dirname(rec["_path"]))
            processed_dir = os.path.join(track_dir, "processed")
            os.makedirs(processed_dir, exist_ok=True)
            os.replace(rec["_path"], os.path.join(processed_dir, os.path.basename(rec["_path"])))
            moved += 1
    left = len(_sweep_pending())
    print("pruned {} candidates older than {}d by feed date; {} still pending".format(
        moved, args.days, left))
    return 0


def cmd_sweep_list(args):
    pending = _sweep_pending()
    if not pending:
        print("NONE")
        return 0
    for rec in pending[:args.limit] if args.limit else pending:
        score = (rec.get("scores") or {}).get("overall", 0)
        age = _feed_age(rec)
        print("{} | {} | {} | {} | score={:.2f} | feed_age={}d | {}".format(
            rec.get("job_id", "?"), rec.get("profile_track", "?"),
            rec.get("company", "?"), rec.get("title", "?"), score,
            age, rec.get("url", "")))
    if args.limit and len(pending) > args.limit:
        print("({} more pending)".format(len(pending) - args.limit))
    return 0


TRACKS = ("security-analyst", "software-engineer", "ai-engineer")
TRACK_ALIASES = {"security": "security-analyst", "software": "software-engineer",
                 "swe": "software-engineer", "ai": "ai-engineer", "ml": "ai-engineer",
                 "ai engineer": "ai-engineer", "software engineer": "software-engineer",
                 "security analyst": "security-analyst"}


def cmd_scan_add(args):
    """Read a JSON array from stdin — [{title, company, url, location, track,
    connector, note}] — and write each into job-matcher-feed/<track>/<date>/
    so it joins the sweep queue exactly like a job-matcher export. Idempotent
    by URL hash, same as job-matcher's own idempotency (rglob for existing
    job_id.json). Used by manual browser-scan runs (Handshake/Jobright/
    LinkedIn "recommended for you" pages) that job-matcher's connectors can't
    reach since they need the user's live logged-in session.
    """
    import hashlib
    try:
        items = json.loads(sys.stdin.read())
    except Exception as e:
        print("ERROR invalid JSON on stdin: {}".format(e))
        return 1

    added, skipped, bad = 0, 0, []
    today = datetime.date.today().isoformat()
    for item in items:
        url = item.get("url", "")
        if not url:
            skipped += 1
            continue
        # `track` is a folder name. A loose value ("security") used to create a
        # second folder and split the queue, so aliases are folded and anything
        # else is refused rather than guessed.
        raw_track = (item.get("track") or "").strip().lower()
        track = TRACK_ALIASES.get(raw_track, raw_track)
        if track not in TRACKS:
            bad.append("{} (track={!r})".format(url, item.get("track")))
            continue
        job_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

        # Dedupe across EVERY track, not just this one.
        if os.path.isdir(SWEEP_FEED) and any(
                fn == job_id + ".json"
                for _, _, files in os.walk(SWEEP_FEED) for fn in files):
            skipped += 1
            continue

        record = {
            "job_id": job_id,
            "title": item.get("title", ""),
            "company": item.get("company", ""),
            "location": item.get("location"),
            "url": url,
            "connector": item.get("connector", "browser_scan"),
            "posted_at": item.get("posted_at"),
            "profile_track": track,
            "scores": {"overall": item.get("score", 0.5)},
            "agentic_explanation": item.get("note"),
        }
        date_dir = os.path.join(SWEEP_FEED, track, today)
        os.makedirs(date_dir, exist_ok=True)
        with io.open(os.path.join(date_dir, job_id + ".json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, ensure_ascii=False)
        added += 1

    print("scan-add: {} added, {} skipped (already queued or no url)".format(added, skipped))
    if bad:
        print("REJECTED {} -- track must be one of {}:".format(len(bad), " | ".join(TRACKS)))
        for b in bad:
            print("  " + b)
        return 1
    return 0


def cmd_sweep_done(args):
    for rec in _sweep_pending():
        if rec.get("job_id") == args.job_id:
            track_dir = os.path.dirname(os.path.dirname(rec["_path"]))
            processed_dir = os.path.join(track_dir, "processed")
            os.makedirs(processed_dir, exist_ok=True)
            dest = os.path.join(processed_dir, os.path.basename(rec["_path"]))
            os.replace(rec["_path"], dest)
            print("moved to " + dest)
            return 0
    print("NOT_FOUND job_id={}".format(args.job_id))
    return 1


def cmd_insights(args):
    rows = tracker_rows()

    def bucket(role):
        r = " " + (role or "").lower() + " "
        if any(k in r for k in ("security", " soc ", "cyber", "infosec", "grc")):
            return "security"
        if any(k in r for k in (" ml ", "machine learning", " ai ", "(ai", "ai)", "ai/", "data scien")):
            return "ML/AI"
        if any(k in r for k in ("data engineer", "analytics", "analyst")):
            return "data/analyst"
        return "SWE"

    def tally(key_fn):
        stats = {}
        for r in rows:
            st = r["status"]
            if st not in jobtrack.SENT:
                continue
            b = key_fn(r)
            s_ = stats.setdefault(b, {"sent": 0, "reply": 0, "reject": 0, "pending": 0})
            s_["sent"] += 1
            if st in jobtrack.REPLY:
                s_["reply"] += 1
            elif st in ("rejected", "withdrawn"):
                s_["reject"] += 1
            else:
                s_["pending"] += 1
        return stats

    def table(title, stats):
        print("\n{:<16}{:>6}{:>8}{:>8}{:>9}{:>8}".format(title, "sent", "reply", "reject", "pending", "rate"))
        for b, s_ in sorted(stats.items(), key=lambda kv: -kv[1]["sent"]):
            rate = (100.0 * s_["reply"] / s_["sent"]) if s_["sent"] else 0.0
            print("{:<16}{:>6}{:>8}{:>8}{:>9}{:>7.1f}%".format(
                b[:16], s_["sent"], s_["reply"], s_["reject"], s_["pending"], rate))

    by_role = tally(lambda r: bucket(r["role"]))
    total = sum(v["sent"] for v in by_role.values())
    outcomes = sum(v["reply"] + v["reject"] for v in by_role.values())
    print("{} applications sent | {} with a known outcome".format(total, outcomes))
    table("role type", by_role)
    table("source", tally(lambda r: r["source"] or "direct"))
    table("resume variant", tally(
        lambda r: (re.search(r"rv=(\w+)", r.get("notes") or "") or [None, "v1"])[1]))
    if outcomes < 15:
        print("\nSAMPLE TOO THIN ({} known outcomes). Report tentative observations only; "
              "do not claim patterns.".format(outcomes))
    return 0


# ------------------------------------------------------------------------ main

def main():
    p = argparse.ArgumentParser(prog="jobkit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("dup"); d.add_argument("url")
    d.add_argument("--company", default=""); d.add_argument("--role", default="")
    d.set_defaults(fn=cmd_dup)

    sub.add_parser("count").set_defaults(fn=cmd_count)

    pl = sub.add_parser("pool"); pl.add_argument("what", choices=["tex", "notes", "entry"])
    pl.add_argument("entry", nargs="?", default=""); pl.set_defaults(fn=cmd_pool)

    q = sub.add_parser("qa"); q.add_argument("what", choices=["list", "get"])
    q.add_argument("story", nargs="?", default=""); q.set_defaults(fn=cmd_qa)

    pf = sub.add_parser("pagefit"); pf.add_argument("pdf"); pf.set_defaults(fn=cmd_pagefit)

    af = sub.add_parser("atsfix"); af.add_argument("pdf"); af.set_defaults(fn=cmd_atsfix)

    ac = sub.add_parser("atscheck"); ac.add_argument("pdf"); ac.set_defaults(fn=cmd_atscheck)

    sm = sub.add_parser("similar"); sm.add_argument("posting", help="path to the new job-posting.md")
    sm.add_argument("--company", default=""); sm.add_argument("--role", default="")
    sm.add_argument("--threshold", type=float, default=PHASE1_THRESHOLD)
    sm.add_argument("--exclude", default="", help="folder substring to skip (self-match guard)")
    sm.set_defaults(fn=cmd_similar)

    sc = sub.add_parser("schema"); sc.add_argument("url"); sc.set_defaults(fn=cmd_schema)

    po = sub.add_parser("posted"); po.add_argument("url")
    po.add_argument("--timeout", type=float, default=120.0); po.set_defaults(fn=cmd_posted)

    ga = sub.add_parser("gate", help="G1-G6 in one call: one GATE PASS / STOP / NO_META verdict")
    ga.add_argument("url"); ga.add_argument("--source", default="")
    ga.add_argument("--force", action="store_true",
                    help="the user overrode: triage SKIP (and a prior skipped/held row for this URL) do not stop")
    ga.add_argument("--stale-ok", action="store_true", help="the user said yes to a STALE posting")
    ga.add_argument("--timeout", type=float, default=120.0, help="posting-date lookup timeout")
    ga.set_defaults(fn=cmd_gate)

    sub.add_parser("insights").set_defaults(fn=cmd_insights)

    sl = sub.add_parser("sweep-list"); sl.add_argument("--limit", type=int, default=0)
    sl.set_defaults(fn=cmd_sweep_list)

    sd = sub.add_parser("sweep-done"); sd.add_argument("job_id"); sd.set_defaults(fn=cmd_sweep_done)

    sub.add_parser("scan-add").set_defaults(fn=cmd_scan_add)

    sp = sub.add_parser("sweep-prune"); sp.add_argument("--days", type=int, default=3)
    sp.set_defaults(fn=cmd_sweep_prune)

    jobtrack.register(sub)

    import jobprep
    me = sub.add_parser("meta"); me.add_argument("url")
    me.add_argument("--write", action="store_true", help="create the folder + job-posting.md")
    me.add_argument("--posted", default="", help='e.g. "2026-09-17 (2 days ago)" or "unknown"')
    me.add_argument("--source", default=""); me.set_defaults(fn=jobprep.cmd_meta)

    tr = sub.add_parser("triage"); tr.add_argument("target", help="application folder or job-posting.md")
    tr.set_defaults(fn=jobprep.cmd_triage)

    fp = sub.add_parser("formpack"); fp.add_argument("folder")
    for flag in ("--company", "--role", "--url", "--platform", "--source"):
        fp.add_argument(flag, required=True)
    fp.add_argument("--pay", default=""); fp.add_argument("--posted", default="")
    fp.set_defaults(fn=jobprep.cmd_formpack)

    au = sub.add_parser("audit"); au.add_argument("tex"); au.set_defaults(fn=jobprep.cmd_audit)

    sa = sub.add_parser("salary", help="desired-salary answer for a posted band, e.g. \"$150,000-$220,000\" or none")
    sa.add_argument("pay"); sa.set_defaults(fn=jobprep.cmd_salary)

    sk = sub.add_parser("skills"); sk.add_argument("target", help="application folder or job-posting.md")
    sk.add_argument("--pdf", default="", help="tailored resume PDF: adds the keyword-coverage gate line")
    sk.set_defaults(fn=jobprep.cmd_skills)

    ba = sub.add_parser("base"); ba.add_argument("what", choices=["use", "set", "list"])
    ba.add_argument("track", nargs="?", default=""); ba.add_argument("folder", nargs="?", default="")
    ba.set_defaults(fn=jobprep.cmd_base)

    fl = sub.add_parser("fail"); fl.add_argument("what", choices=["add", "list", "close"])
    fl.add_argument("id", nargs="?", default="", help="F-0001 (close only)")
    fl.add_argument("--phase", choices=jobprep.FAIL_PHASES, default="fill")
    fl.add_argument("--where", default="", help="platform, script command or file the failure lives in")
    fl.add_argument("--happened", default=""); fl.add_argument("--expected", default="")
    fl.add_argument("--workaround", default=""); fl.add_argument("--fix", default="")
    fl.add_argument("--folder", default=""); fl.add_argument("--note", default="")
    fl.add_argument("--all", action="store_true"); fl.add_argument("--wontfix", action="store_true")
    fl.set_defaults(fn=jobprep.cmd_fail)

    args = p.parse_args()
    if not getattr(args, "fn", None):
        p.print_help()
        return 1
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
