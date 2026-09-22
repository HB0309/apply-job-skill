"""jobtrack -- the tracker layer for jobkit (imported by jobkit.py).

tracker.md is a 12-column markdown table. Rows are written ONLY through
`jobkit track add|set`, never by hand: the script escapes pipes, keeps the
status inside the closed vocabulary below, dates the update, and puts every
narrative into Notes.

Columns: Date | Company | Role | Link | Folder | Keywords | Framing | Status |
         Last update | Posted | Source | Notes
"""
import datetime
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKER = os.environ.get("JOBKIT_TRACKER") or os.path.join(ROOT, "tracker.md")
APPS = os.path.join(ROOT, "applications")

COLS = ["date", "company", "role", "link", "folder", "keywords", "framing",
        "status", "updated", "posted", "source", "notes"]
HEADER = ("| Date | Company | Role | Link | Folder | Keywords used | Top-third framing "
          "| Status | Last update | Posted | Source | Notes |")
SEP = "|" + "|".join("---" for _ in COLS) + "|"

# Closed vocabulary. Anything else goes into Notes.
STATUSES = ["prepped", "filled", "applied", "viewed", "oa", "interview", "offer",
            "rejected", "withdrawn", "skipped", "duplicate", "blocked", "held", "review"]
LIVE = {"applied", "viewed", "oa", "interview", "offer"}       # inbox watches these
OPEN = {"prepped", "filled"}                                    # prepped but not sent
SENT = {"applied", "viewed", "oa", "interview", "offer", "rejected", "withdrawn"}
REPLY = {"viewed", "oa", "interview", "offer"}

SOURCES = ["Handshake", "Jobright", "LinkedIn", "Indeed", "Wellfound", "job-matcher",
           "direct", "other"]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Known published employer caps: company-name substring -> (max, window_days)
EMPLOYER_CAPS = {
    "openai": (5, 182),
    "tiktok": (2, 182),
    "canonical": (4, 182),
    "google": (3, 30),      # Google Careers, account-wide, rolling 30 days
    "retell": (2, 60),      # stated only in the posting body
}


def today():
    return datetime.date.today().isoformat()


def esc(s):
    return (s or "").replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()


def unesc(s):
    return (s or "").replace("\\|", "|")


def split_row(line):
    """Split a table line on unescaped pipes."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", body)]


def read_lines():
    with io.open(TRACKER, encoding="utf-8") as fh:
        return fh.read().splitlines()


def write_lines(lines):
    with io.open(TRACKER, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")


def is_row(line):
    return line.startswith("|") and not re.match(r"^\|[\s\-|:]+\|$", line) \
        and not line.lower().startswith("| date ")


def parse_row(line):
    cells = split_row(line)
    cells = cells + [""] * (len(COLS) - len(cells))
    return dict(zip(COLS, [unesc(c) for c in cells[:len(COLS)]]))


def rows():
    return [parse_row(l) for l in read_lines() if is_row(l)]


def fmt(r):
    return "| " + " | ".join(esc(r.get(c, "")) for c in COLS) + " |"


def detect_source(url, hint=""):
    u = (url or "").lower()
    h = (hint or "").lower()
    if "jobright" in h or "jobright.ai" in u or "jr_id=" in u or "src=jobright" in u:
        return "Jobright"
    if "handshake" in h or "joinhandshake.com" in u:
        return "Handshake"
    if "linkedin" in h or "linkedin.com" in u or "jobfeeds-linkedin" in u:
        return "LinkedIn"
    if "indeed" in h or "indeed.com" in u or "srm_indeed" in u:
        return "Indeed"
    if "wellfound" in h or "wellfound.com" in u:
        return "Wellfound"
    if "job-matcher" in h or "sweep" in h:
        return "job-matcher"
    return "direct"


def norm_status(text):
    """Map free text to (status, remainder). Used by migrate and by `track set`
    when someone passes a sentence instead of a token."""
    t = (text or "").strip()
    low = t.lower()
    rules = [
        (r"^(skipped|skip\b)", "skipped"),
        (r"^duplicate|^skipped\s*[-—]\s*duplicate", "duplicate"),
        (r"^rejected|^closed\s*-\s*not pursuing", "rejected"),
        (r"^withdrawn|^closed - not pursuing", "withdrawn"),
        (r"^offer", "offer"),
        (r"^interview|^in progress", "interview"),
        (r"^(oa\b|take-home|coderbyte|online assessment|ai voice screening)", "oa"),
        (r"^applied.*(assessment|oa\b|take-home|screening).*completed", "oa"),
        (r"^applied", "applied"),
        (r"^viewed", "viewed"),
        (r"^filled\s*[-—]\s*held|^held", "held"),
        (r"^filled|^ready|^resume ready", "filled"),
        (r"^prepped|^prep complete|^prep done|^tailored", "prepped"),
        (r"^blocked", "blocked"),
        (r"^review", "review"),
    ]
    for pat, st in rules:
        m = re.search(pat, low)
        if m:
            rem = t if ".*" in pat else t[m.end():]
            rem = rem.strip(" -—:(),.|")
            return st, rem
    if low in ("", "—", "-", "n/a"):
        return "review", t
    return "review", t


# --------------------------------------------------------------------- commands

def find_row_index(lines, key):
    """Return index of the row whose folder or link matches key (substring on
    folder, normalised match on link)."""
    from jobkit import norm_url  # lazy to avoid import cycle
    k = (key or "").strip()
    kn = norm_url(k) if k.startswith("http") else None
    for i, l in enumerate(lines):
        if not is_row(l):
            continue
        r = parse_row(l)
        if kn and any(norm_url(u) == kn for u in re.findall(r"https?://\S+", r["link"])):
            return i
        if not kn and k and k.strip("/").split("/")[-1] in r["folder"]:
            return i
    return -1


def cmd_track_add(a):
    lines = read_lines()
    if a.status not in STATUSES:
        print("ERROR status must be one of: " + ", ".join(STATUSES))
        return 1
    idx = find_row_index(lines, a.link)
    if idx >= 0 and not a.force:
        print("EXISTS " + lines[idx][:160])
        return 2
    folder = a.folder.replace("\\", "/")
    if folder and not folder.startswith("applications/"):
        folder = "applications/" + folder.strip("/").split("/")[-1]
    r = {
        "date": a.date or today(), "company": a.company, "role": a.role, "link": a.link,
        "folder": folder, "keywords": a.keywords or "", "framing": a.framing or "",
        "status": a.status, "updated": today(), "posted": a.posted or "unknown",
        "source": a.source or detect_source(a.link), "notes": a.notes or "",
    }
    if r["source"] not in SOURCES:
        r["source"] = "other (" + r["source"] + ")"
    lines.append(fmt(r))
    write_lines(lines)
    print("ADDED " + fmt(r)[:200])
    return 0


def cmd_track_set(a):
    lines = read_lines()
    idx = find_row_index(lines, a.key)
    if idx < 0:
        print("NOT_FOUND " + a.key)
        return 1
    r = parse_row(lines[idx])
    if a.status:
        if a.status in STATUSES:
            r["status"] = a.status
        else:
            st, rem = norm_status(a.status)
            r["status"] = st
            if rem:
                a.notes = (rem + ("; " + a.notes if a.notes else ""))
    if a.notes:
        stamp = today() + ": " + a.notes.strip()
        r["notes"] = (r["notes"] + " · " + stamp) if r["notes"] else stamp
    if a.posted:
        r["posted"] = a.posted
    if a.source:
        r["source"] = a.source
    r["updated"] = today()
    lines[idx] = fmt(r)
    write_lines(lines)
    print("SET " + fmt(r)[:200])
    return 0


def cmd_track_active(a):
    """Companies with a live application, for the inbox sweep. --query prints
    Gmail OR-queries in chunks of 20 names."""
    seen, out = set(), []
    for r in rows():
        if r["status"] in LIVE:
            c = re.sub(r"\s*\(.*?\)\s*", " ", r["company"]).strip()
            c = c.split(" - ")[0].split(" — ")[0].strip()
            if c.lower() not in seen:
                seen.add(c.lower())
                out.append(c)
    if a.query:
        chunk = 20
        for i in range(0, len(out), chunk):
            names = ['"%s"' % n if " " in n or "&" in n else n for n in out[i:i + chunk]]
            print("(%s) newer_than:%s" % (" OR ".join(names), a.newer))
        return 0
    print("\n".join(out))
    print("\n%d companies with a live application" % len(out))
    return 0


def cmd_track_employer(a):
    """How many applications went to this employer in the last N days, plus
    any known published cap."""
    key = a.company.lower()
    cutoff = datetime.date.today() - datetime.timedelta(days=a.days)
    n = 0
    for r in rows():
        if key in r["company"].lower() and r["status"] in SENT and DATE_RE.match(r["date"]):
            if datetime.date(*map(int, r["date"].split("-"))) >= cutoff:
                n += 1
    cap = next(((m, w) for k, (m, w) in EMPLOYER_CAPS.items() if k in key), None)
    if cap:
        m, w = cap
        cutoff2 = datetime.date.today() - datetime.timedelta(days=w)
        n2 = sum(1 for r in rows() if key in r["company"].lower() and r["status"] in SENT
                 and DATE_RE.match(r["date"])
                 and datetime.date(*map(int, r["date"].split("-"))) >= cutoff2)
        print("%s: %d sent in last %dd | CAP %d per %dd, %d used%s" % (
            a.company, n, a.days, m, w, n2, " -- AT CAP, pause and ask" if n2 >= m else ""))
    else:
        print("%s: %d sent in last %dd | no published cap" % (a.company, n, a.days))
    return 0


def cmd_track_audit(a):
    lines = read_lines()
    rs = [parse_row(l) for l in lines if is_row(l)]
    problems = 0

    print("## rows with a bad status / date")
    for r in rs:
        bad = []
        if r["status"] not in STATUSES:
            bad.append("status=" + r["status"][:40])
        if not DATE_RE.match(r["updated"]):
            bad.append("updated=" + r["updated"][:20])
        if not (DATE_RE.match(r["posted"]) or r["posted"] == "unknown"):
            bad.append("posted=" + r["posted"][:20])
        if bad:
            problems += 1
            print("  %s | %s | %s" % (r["date"], r["company"][:30], "; ".join(bad)))

    print("## rows whose folder is missing on disk")
    tracked = set()
    for r in rs:
        f = r["folder"].strip("/").split("/")[-1]
        if f and r["folder"].startswith("applications/"):
            tracked.add(f)
            if not os.path.isdir(os.path.join(APPS, f)):
                problems += 1
                print("  %s | %s | %s" % (r["date"], r["company"][:30], r["folder"]))

    print("## folders with no row")
    for name in sorted(os.listdir(APPS)):
        if name not in tracked and os.path.isdir(os.path.join(APPS, name)):
            problems += 1
            files = os.listdir(os.path.join(APPS, name))
            print("  %s (%s)" % (name, ", ".join(sorted(files))[:80]))

    print("## prepped/filled but never submitted (older than %d days)" % a.days)
    cutoff = datetime.date.today() - datetime.timedelta(days=a.days)
    for r in rs:
        if r["status"] in OPEN and DATE_RE.match(r["updated"]):
            if datetime.date(*map(int, r["updated"].split("-"))) < cutoff:
                problems += 1
                print("  %s | %s | %s | %s" % (r["date"], r["company"][:30], r["role"][:40], r["status"]))

    print("\n%d problems" % problems)
    return 0 if problems == 0 else 2


# --------------------------------------------------------------------- migrate

OLD_COLS = ["date", "company", "role", "link", "folder", "keywords", "framing",
            "status", "updated", "posted"]


def _parse_old(line):
    """Old rows: naive pipe split, 9-14 cells. Rebuild status/updated/posted
    from the tail by finding the date-shaped cells."""
    cells = split_row(line)
    if len(cells) < 8:
        return None
    head, tail = cells[:7], cells[7:]
    # the trailing run of date-shaped cells is [updated, posted, extras...];
    # everything before it is status text (which may itself contain pipes)
    k = len(tail)
    while k > 1 and (DATE_RE.match(tail[k - 1]) or tail[k - 1] in ("unknown", "")):
        k -= 1
    run = [c for c in tail[k:] if c]
    status = " | ".join(c for c in tail[:k] if c)
    updated = run[0] if run and DATE_RE.match(run[0]) else ""
    posted = run[1] if len(run) > 1 else ""
    if len(run) > 2:
        status += " (extra date cells: " + ", ".join(run[2:]) + ")"
    r = dict(zip(OLD_COLS, [unesc(c) for c in head] + [status, updated, posted]))
    return r


def cmd_track_migrate(a):
    lines = read_lines()
    backup = TRACKER.replace("tracker.md", "tracker.backup-%s.md" % today())
    if not os.path.exists(backup):
        with io.open(backup, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
    new = []
    body = []
    header_done = False
    review = 0
    for l in lines:
        if l.lower().startswith("| date "):
            header_done = True
            continue
        if header_done and re.match(r"^\|[\s\-|:]+\|$", l):
            continue
        if is_row(l):
            r = _parse_old(l)
            if not r:
                continue
            st, rem = norm_status(r["status"])
            if st == "review":
                review += 1
            notes = rem
            if not r["updated"]:
                r["updated"] = r["date"] if DATE_RE.match(r["date"]) else today()
            if not r["posted"]:
                r["posted"] = "unknown"
            src = detect_source(r["link"], r["status"] + " " + r["framing"])
            body.append({**r, "status": st, "notes": notes, "source": src})
        elif not header_done:
            new.append(l)
    # orphan folders -> review rows
    tracked = {r["folder"].strip("/").split("/")[-1] for r in body}
    orphans = 0
    for name in sorted(os.listdir(APPS)):
        p = os.path.join(APPS, name)
        if name in tracked or not os.path.isdir(p):
            continue
        files = sorted(os.listdir(p))
        m = re.match(r"^(\d{4}-\d{2}-\d{2})_([^_]+)_(.+)$", name)
        date = m.group(1) if m else today()
        company = m.group(2).replace("-", " ").title() if m else name
        role = m.group(3).replace("-", " ").title() if m else ""
        has_pack = "form-pack.md" in files
        has_pdf = any(f.endswith(".pdf") for f in files)
        st = "prepped" if (has_pack or has_pdf) else "review"
        body.append({"date": date, "company": company, "role": role, "link": "",
                     "folder": "applications/" + name, "keywords": "", "framing": "",
                     "status": st, "updated": today(), "posted": "unknown", "source": "other",
                     "notes": "%s: no tracker row found at migration; folder had %s" % (
                         today(), ", ".join(files)[:120])})
        orphans += 1
    # rebuild the file: keep the preamble (title/comment) then table
    preamble = [l for l in new if not l.startswith("|")]
    # replace the status-lifecycle line
    pre2 = []
    for l in preamble:
        if l.startswith("Status lifecycle"):
            l = ("Status vocabulary (closed): " + " · ".join("`%s`" % s for s in STATUSES)
                 + " — anything else belongs in Notes. Rows are written only by "
                   "`jobkit track add|set`.")
        pre2.append(l)
    out = pre2 + [HEADER, SEP] + [fmt(r) for r in body]
    write_lines(out)
    print("migrated %d rows (%d left as `review`), %d orphan folders added, backup at %s" % (
        len(body) - orphans, review, orphans, os.path.basename(backup)))
    return 0


def register(sub):
    t = sub.add_parser("track", help="tracker writes/reads (add|set|active|employer|audit|migrate)")
    ts = t.add_subparsers(dest="tcmd")

    ad = ts.add_parser("add")
    for k in ("company", "role", "link", "folder", "status"):
        ad.add_argument("--" + k, required=True)
    for k in ("keywords", "framing", "posted", "source", "notes", "date"):
        ad.add_argument("--" + k, default="")
    ad.add_argument("--force", action="store_true", help="append even if the link already has a row")
    ad.set_defaults(fn=cmd_track_add)

    st = ts.add_parser("set")
    st.add_argument("key", help="folder name or link")
    st.add_argument("--status", default="")
    st.add_argument("--notes", default="")
    st.add_argument("--posted", default="")
    st.add_argument("--source", default="")
    st.set_defaults(fn=cmd_track_set)

    ac = ts.add_parser("active")
    ac.add_argument("--query", action="store_true", help="print Gmail OR-queries, 20 companies each")
    ac.add_argument("--newer", default="2d")
    ac.set_defaults(fn=cmd_track_active)

    em = ts.add_parser("employer")
    em.add_argument("company")
    em.add_argument("--days", type=int, default=30)
    em.set_defaults(fn=cmd_track_employer)

    au = ts.add_parser("audit")
    au.add_argument("--days", type=int, default=7)
    au.set_defaults(fn=cmd_track_audit)

    mg = ts.add_parser("migrate")
    mg.set_defaults(fn=cmd_track_migrate)
