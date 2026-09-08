#!/usr/bin/env python3
"""jobkit — cheap reads for the /apply-job skill.

Every subcommand exists to replace a large file read with a small stdout payload.
Run with no arguments for usage.

  dup <url> [--company C] [--role R]   one tracker row, or NONE
  count                                 non-skipped application count
  pool tex                              content-pool.tex minus the two note blocks
  pool notes [entry]                    just those note blocks (factual audit)
  qa list                               the 23 story headings
  qa get <substr>                       one story body
  pagefit <pdf>                         page count + bottom whitespace + verdict
  similar <job-posting.md> [--company C] best prior application to reuse
  schema <url>                          ATS application-form schema, compact
  posted <url>                          original posting date + age in days + verdict
  insights                              conversion table over the whole corpus
  sweep-list                            pending job-matcher-feed candidates, by score desc
  sweep-done <job_id>                   mark a swept candidate as processed
  sweep-prune [--days N]                move feed candidates older than N days (default 3) to processed/
  scan-add                              stdin: JSON array of manually-browsed jobs -> feed queue
  track add|set|active|employer|audit   tracker writes and reads -- the ONLY way rows change
"""
import argparse
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
TRACKER = os.path.join(ROOT, "tracker.md")
POOL = os.path.join(ROOT, "master", "content-pool.tex")
QABANK = os.path.join(ROOT, "qa-bank.md")
APPS = os.path.join(ROOT, "applications")
SWEEP_FEED = os.path.join(ROOT, "job-matcher-feed")

import jobtrack
COLS = jobtrack.COLS

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


def cmd_dup(args):
    target = norm_url(args.url)
    rows = tracker_rows()
    for r in rows:
        for u in re.findall(r"https?://\S+", r["link"]):
            if norm_url(u) == target:
                print(fmt_row(r))
                return 0
    if args.company:
        co, role = norm_text(args.company), norm_text(args.role)
        for r in rows:
            if norm_text(r["company"]) != co:
                continue
            if not role or role in norm_text(r["role"]) or norm_text(r["role"]) in role:
                print("FUZZY " + fmt_row(r))
                return 0
    print("NONE")
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
# "full-stack" or "SY0-701" does not match "scikit‐learn". Same class of
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
    U+2010 HYPHEN, so every "scikit-learn" / "SY0-701" / "(555)-123-4567" in
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

    if not fixed:
        print("atsfix no-change {}".format(args.pdf))
        return 0
    with open(args.pdf, "wb") as fh:
        writer.write(fh)
    print("atsfix rewrote {} ToUnicode map(s) in {}".format(fixed, args.pdf))
    return 0


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
    tex = os.path.join(path, "Resume.tex")
    pdf = os.path.join(path, "Resume.pdf")
    reasons = []
    if score < args.threshold:
        reasons.append("score {:.2f} < {:.2f}".format(score, args.threshold))
    if args.company and row and norm_text(args.company) != norm_text(company):
        reasons.append("different company ({} vs {})".format(company, args.company))
    if not (os.path.exists(tex) and os.path.exists(pdf)):
        reasons.append("prior tex/pdf missing")
    elif os.path.getmtime(tex) < os.path.getmtime(POOL):
        reasons.append("STALE: content-pool.tex edited after that resume was built")
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

    added, skipped = 0, 0
    today = datetime.date.today().isoformat()
    for item in items:
        url = item.get("url", "")
        if not url:
            skipped += 1
            continue
        track = item.get("track") or "unclassified"
        job_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

        track_dir = os.path.join(SWEEP_FEED, track)
        if os.path.isdir(track_dir):
            exists = any(
                fn == job_id + ".json"
                for _, _, files in os.walk(track_dir) for fn in files
            )
            if exists:
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

    pl = sub.add_parser("pool"); pl.add_argument("what", choices=["tex", "notes"])
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

    sub.add_parser("insights").set_defaults(fn=cmd_insights)

    sl = sub.add_parser("sweep-list"); sl.add_argument("--limit", type=int, default=0)
    sl.set_defaults(fn=cmd_sweep_list)

    sd = sub.add_parser("sweep-done"); sd.add_argument("job_id"); sd.set_defaults(fn=cmd_sweep_done)

    sub.add_parser("scan-add").set_defaults(fn=cmd_scan_add)

    sp = sub.add_parser("sweep-prune"); sp.add_argument("--days", type=int, default=3)
    sp.set_defaults(fn=cmd_sweep_prune)

    jobtrack.register(sub)

    args = p.parse_args()
    if not getattr(args, "fn", None):
        p.print_help()
        return 1
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
