#!/usr/bin/env python3
"""jobprep -- the deterministic half of /apply-job's prep phase.

Everything here used to be done by the prep model, per application, in tokens:
fetching and transcribing the posting, the clear-cut eligibility skips, the
static three quarters of form-pack.md, and a token-level fabrication check.
None of it needs judgement, so none of it should cost a model call.

  meta <url> [--write] [--posted S] [--source S]
      Posting facts straight from the ATS's public job API. One line:
      company | role | location | platform | pay=<band|none> | apply_url | folder
      --write also creates the application folder and job-posting.md.
      NO_META means no API for that host: prep fetches the posting itself.

  triage <folder | job-posting.md>
      SKIP <reason> | PASS [notes] | UNSURE + the flagged lines. Regex only.
      SKIP fires on strict phrasing alone; anything negated or merely adjacent
      is UNSURE, which costs the orchestrator ~200 tokens instead of a prep run.
      Skips: auto-skip employers, clearance, citizenship, ITAR / US-person, the
      employer refusing sponsorship in its own voice, a first stated experience
      requirement of 3+ years, senior titles, low pay + government. Note lines
      written by a prep agent ("no sponsorship statement either way") never skip.

  skills <folder | job-posting.md> [--pdf <resume.pdf>]
      The posting against master/skills-inventory.md: TRUE <kw> -> <page wording>,
      BANNED, GAP, then `TRACK ... -> base: <track> [HYBRID: a+b]`. With --pdf it
      adds the gate line `Keyword coverage: n/m (X%) | true-but-missing: k`.

  formpack <folder> --company C --role R --url U --platform P --source S [--pay S]
      Writes form-pack.md: header, platform traps, schema dump, identity, locked
      fields, defaults, education, certification, languages and the work
      experience exactly as it stands on the tailored .tex. The model appends
      only the fill plan and the screener answers.

  audit <tex>
      Every number in the tailored resume must exist in the pool or profile
      (FAIL otherwise); every tech-looking token that does not is a WARN the
      prep model must justify in the match report.

  salary "<pay line>" | none
      Desired-salary rows (free text, single number, min/max pair) anchored to
      the posted band. Accepts "$a-$b", "USD a - b", "a - b USD per year", a
      single figure ("$130K") and hourly rates. No band -> your own range.

  base use|set|list [track] [folder]
      Track base resumes (security, software, ai) under bases/.

  fail add|list|close [id]
      The failure log, failures.md.
"""
import datetime
import html
import io
import json
import math
import os
import re
import shutil
import subprocess
import unicodedata
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jobtrack import APPS       # honours JOBKIT_APPS_ROOT (tests); defaults to ROOT/applications
POOL = os.path.join(ROOT, "master", "content-pool.tex")
PROFILE = os.path.join(ROOT, "master", "profile.md")
SKILL_DIR = os.environ.get("APPLY_JOB_SKILL_DIR") or os.path.join(
    os.path.expanduser("~"), ".claude", "skills", "apply-job")
FORM_DATA = os.path.join(SKILL_DIR, "form-data.md")
RESUME_TEX = "Resume_Resume.tex"
RESUME_PDF = "Resume_Resume.pdf"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) jobkit/1.0",
           "Accept": "application/json"}


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def get_json(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    hdrs = dict(HEADERS)
    if data:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def slug(s, limit=40):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:limit].strip("-") or "unknown"


# Tag body that tolerates ">" inside a quoted attribute: <li class="[&>p]:inline" style="...">
# broke the old <[^>]+> pattern and left `p]:inline" style="..."` on every bullet (F-0003).
_TAG = r"""(?:"[^"]*"|'[^']*'|[^'">])*"""


def html_to_text(s):
    s = html.unescape(s or "")
    if "&lt;" in s or "&amp;" in s:        # Greenhouse double-escapes its content
        s = html.unescape(s)
    s = re.sub(r"(?i)<\s*li\b" + _TAG + ">", "\n- ", s)
    s = re.sub(r"(?i)<\s*(br|/p|/div|/h[1-6]|/li|/ul|/ol|/tr)\b" + _TAG + ">", "\n", s)
    s = re.sub(r"(?i)<\s*h[1-6]\b" + _TAG + ">", "\n\n### ", s)
    s = re.sub(r"<[a-zA-Z/!]" + _TAG + ">", "", s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


PAY_RE = re.compile(
    r"\$\s?(\d{2,3}(?:,\d{3})(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[Kk])\s*(?:USD)?\s*"
    r"(?:-|–|—|(?i:to|and))\s*\$?\s?(\d{2,3}(?:,\d{3})(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[Kk])")


def _money(tok):
    tok = tok.replace(",", "").strip()
    if tok[-1:] in "Kk":
        return int(float(tok[:-1]) * 1000)
    return int(float(tok))


HOURLY_RE = re.compile(r"\$\s?(\d{2,3}(?:\.\d{1,2})?)\s*(?:(?:-|–|—|to)\s*\$?\s?(\d{2,3}(?:\.\d{1,2})?))?\s*"
                       r"(?:/|per|an|a)\s*(?:hr|hour)\b", re.I)


# Line-only shapes (a "Pay range published" line or a `salary` argument, never a posting body):
# a band without "$" ("USD 130,000 - 160,000", "130,000 - 160,000 USD per year") and a single
# figure ("$130,000", "$130K", "130,000 USD"). Both still need a salary context on the line.
_AMT = r"(\d{2,3}(?:,\d{3})(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[Kk])"
PAY_BARE_RE = re.compile(r"(?<![\d,.$])" + _AMT + r"\s*(?:USD)?\s*(?:-|–|—|(?i:to))\s*\$?\s?" + _AMT + r"(?![\d,])")
PAY_ONE_RE = re.compile(r"(?:\$\s?|(?<![\d,.]))" + _AMT + r"(?![\d,])")
PAY_CONTEXT = re.compile(r"\$|\bUSD\b|salary|compensation|base pay|per (year|annum)|/\s?(yr|year)\b|annual|"
                         r"\d\s?[Kk]\b", re.I)


def _widest(pairs):
    best = None
    for lo, hi in pairs:
        if lo < 20000 or hi < lo:          # hourly rates and junk
            continue
        if best is None or hi > best[1]:
            best = (lo, hi)
    return best


def _pairs(regex, text, single=False):
    for m in regex.finditer(text or ""):
        if re.match(r"40[13]\s?[Kk]$", m.group(1)):     # a 401k plan, not a salary
            continue
        try:
            lo = _money(m.group(1))
            hi = lo if single else _money(m.group(2))
        except ValueError:
            continue
        yield lo, hi


def pay_from_text(text, line=False):
    """(lo, hi) of the widest annual-looking band in the text, else None. An hourly rate is
    annualised at 2,080 hours only when no annual band is present. line=True (a pay line, not a
    posting body) also accepts a $-less band and a single figure (x -> (x, x)) when the line
    carries a salary context."""
    best = _widest(_pairs(PAY_RE, text))
    if best is None and line and PAY_CONTEXT.search(text or ""):
        best = _widest(_pairs(PAY_BARE_RE, text))
    if best is None:
        for m in HOURLY_RE.finditer(text or ""):
            lo = float(m.group(1))
            hi = float(m.group(2)) if m.group(2) else lo
            if 10 <= lo <= hi <= 400 and (best is None or hi * 2080 > best[1]):
                best = (int(lo * 2080), int(hi * 2080))
    if best is None and line and PAY_CONTEXT.search(text or ""):
        # One figure -> (x, x). Two or more figures the band shapes missed ("$121,992/year to
        # $181,000/year", "USD $86,000.00/Yr. – USD $110,575.00/Yr.") -> (lowest, highest).
        amts = [lo for lo, _ in _pairs(PAY_ONE_RE, text, single=True) if lo >= 20000]
        best = (min(amts), max(amts)) if amts else None
    return best


def fmt_pay(band):
    return "${:,}-${:,}".format(*band) if band else "none"


SAL_LO, SAL_HI = 100000, 130000     # SET YOUR OWN range, used as-is when no band is posted


def _round5k(x):
    return int(math.floor(x / 5000.0 + 0.5)) * 5000


def salary_answer(band):
    """Desired-salary answer for one posting (the user, 2026-09-28): always anchored to the posted
    band. Min above SAL_LO -> min + 7% rounded to $5k, never above their max. Max under SAL_HI (min
    at or under the floor) -> their max. Band containing your range, or no band -> your own range.
    Returns number, (min, max) pair, free text, and the rule that fired."""
    if band:
        lo, hi = band
        if lo > SAL_LO:
            t = min(hi, _round5k(lo * 1.07))
            rule = "posted min above your floor: min + 7%, rounded to $5k, capped at their max"
        elif hi < SAL_HI:
            t = hi
            rule = "posted max under your ceiling: their max"
        else:
            band = None
    if not band:
        return {"number": (SAL_LO + SAL_HI) // 2, "pair": (SAL_LO, SAL_HI), "text": "Targeting ${}k–{}k".format(SAL_LO // 1000, SAL_HI // 1000),
                "rule": "no band posted, or the band contains your range: your own range"}
    return {"number": t, "pair": (t, min(hi, _round5k(t * 1.15))), "text": "Targeting ${:,}".format(t),
            "rule": rule}


def salary_rows(pay_text):
    band = pay_from_text(pay_text, line=True) if pay_text and pay_text != "none" else None
    s = salary_answer(band)
    rows = ["| Salary expectation, free text | `{}` ({}; posted {}) |".format(s["text"], s["rule"], fmt_pay(band)),
            "| Desired salary, single number field | `{}` |".format(s["number"]),
            "| Desired salary, min / max pair | `{}` / `{}` |".format(*s["pair"])]
    if band and not PAY_RE.search(pay_text) and HOURLY_RE.search(pay_text):
        rows.append("| Desired pay, hourly field (posting is hourly) | `{:.2f}` per hour |".format(s["number"] / 2080))
    return rows


def cmd_salary(args):
    for row in salary_rows(args.pay):
        print(row)
    return 0


# ------------------------------------------------------------------------ meta
def _greenhouse(url):
    m = (re.search(r"greenhouse\.io/embed/job_app\?(?=.*\bfor=([^&]+))(?=.*\btoken=(\d+))", url)
         or re.search(r"greenhouse\.io/([^/?]+)/jobs/(\d+)", url))
    if not m:
        return None
    org, jid = m.group(1), m.group(2)
    d = get_json("https://boards-api.greenhouse.io/v1/boards/{}/jobs/{}?pay_transparency=true"
                 .format(org, jid))
    try:
        company = get_json("https://boards-api.greenhouse.io/v1/boards/" + org).get("name")
    except Exception:
        company = None
    band = None
    for r in d.get("pay_input_ranges") or []:
        try:
            lo, hi = int(r["min_cents"]) // 100, int(r["max_cents"]) // 100
            if hi >= 20000 and (band is None or hi > band[1]):
                band = (lo, hi)
        except Exception:
            pass
    return {"company": company or d.get("company_name") or org, "role": d.get("title", ""),
            "location": (d.get("location") or {}).get("name", ""), "platform": "greenhouse",
            "body": html_to_text(d.get("content", "")), "pay": band,
            "apply_url": "https://job-boards.greenhouse.io/{}/jobs/{}".format(org, jid),
            "updated": (d.get("updated_at") or "")[:10], "jobid": jid}


def _ashby(url):
    m = re.search(r"ashbyhq\.com/([^/?]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    org, pid = m.group(1), m.group(2)
    d = get_json("https://api.ashbyhq.com/posting-api/job-board/{}?includeCompensation=true"
                 .format(org))
    job = next((j for j in d.get("jobs", []) if j.get("id") == pid), None)
    if not job:
        raise ValueError("posting not on the board (closed?)")
    comp = (job.get("compensation") or {}).get("compensationTierSummary") or ""
    return {"company": urllib.parse.unquote(org).replace("-", " ").title(),
            "role": job.get("title", ""), "location": job.get("location", ""),
            "platform": "ashby",
            "body": job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml", "")),
            "pay": pay_from_text(comp), "pay_note": comp,
            "apply_url": "https://jobs.ashbyhq.com/{}/{}/application".format(org, pid),
            "updated": (job.get("publishedAt") or "")[:10], "jobid": pid}


def _lever(url):
    m = re.search(r"jobs\.lever\.co/([^/?]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    org, pid = m.group(1), m.group(2)
    d = get_json("https://api.lever.co/v0/postings/{}/{}".format(org, pid))
    parts = [d.get("descriptionPlain", "")]
    for lst in d.get("lists") or []:
        parts.append("### " + lst.get("text", "") + "\n" + html_to_text(lst.get("content", "")))
    parts.append(d.get("additionalPlain", ""))
    sr = d.get("salaryRange") or {}
    band = (int(sr["min"]), int(sr["max"])) if sr.get("min") and sr.get("max") else None
    # salaryRange carries its own currency: FiscalNote's INR 650,000-750,000 (Gurugram role) was read
    # as USD (2026-09-29). Only a USD (or unstated) band counts; an hourly one is annualised.
    if band and (sr.get("currency") or "USD").upper() != "USD":
        band = None
    elif band and "hour" in (sr.get("interval") or ""):
        band = (int(band[0] * 2080), int(band[1] * 2080))
    return {"company": org.replace("-", " ").title(), "role": d.get("text", ""),
            "location": (d.get("categories") or {}).get("location", ""), "platform": "lever",
            "body": "\n\n".join(p for p in parts if p), "pay": band,
            "apply_url": "https://jobs.lever.co/{}/{}/apply".format(org, pid),
            "updated": "", "jobid": pid}


def _smartrecruiters(url):
    m = re.search(r"smartrecruiters\.com/([^/?]+)/(\d{6,})", url)
    if not m:
        return None
    co, pid = m.group(1), m.group(2)
    d = get_json("https://api.smartrecruiters.com/v1/companies/{}/postings/{}".format(co, pid))
    secs = ((d.get("jobAd") or {}).get("sections") or {})
    body = "\n\n".join("### {}\n{}".format(v.get("title", k), html_to_text(v.get("text", "")))
                       for k, v in secs.items() if isinstance(v, dict) and v.get("text"))
    loc = d.get("location") or {}
    return {"company": (d.get("company") or {}).get("name") or co, "role": d.get("name", ""),
            "location": ", ".join(x for x in (loc.get("city"), loc.get("region"),
                                              (loc.get("country") or "").upper()) if x),
            "platform": "smartrecruiters", "body": body, "pay": None,
            "apply_url": d.get("applyUrl") or url,
            "updated": (d.get("releasedDate") or "")[:10], "jobid": pid}


def _workday(url):
    m = re.search(r"https?://([^./]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?"
                  r"([^/?]+)(/job/[^?#]+)", url)
    if not m:
        return None
    tenant, wd, site, path = m.groups()
    d = get_json("https://{}.{}.myworkdayjobs.com/wday/cxs/{}/{}{}".format(
        tenant, wd, tenant, site, path))
    info = d.get("jobPostingInfo") or {}
    company = ((d.get("hiringOrganization") or {}).get("name") or tenant.title())
    return {"company": company, "role": info.get("title", ""),
            "location": info.get("location", ""), "platform": "workday",
            "body": html_to_text(info.get("jobDescription", "")), "pay": None,
            "apply_url": info.get("externalUrl") or url,
            "updated": (info.get("startDate") or "")[:10],
            "jobid": info.get("jobReqId") or slug(path)[-12:]}


def _eightfold(url):
    """Eightfold career sites (<tenant>.eightfold.ai/careers/job/<id>) have a public job API (F-0022)."""
    m = re.search(r"https?://([a-z0-9-]+)\.eightfold\.ai/careers/(?:job/|[^?]*\?(?:.*&)?pid=)(\d+)", url, re.I)
    if not m:
        return None
    tenant, jid = m.group(1), m.group(2)
    d = get_json("https://{}.eightfold.ai/api/apply/v2/jobs/{}".format(tenant, jid))
    body = html_to_text(d.get("job_description", ""))
    company = d.get("company_name") or d.get("organization") or tenant.replace("-", " ").title()
    created = d.get("t_create")
    return {"company": company, "role": d.get("name", ""), "location": (d.get("location") or "").replace(",", ", "),
            "platform": "eightfold", "body": body, "pay": pay_from_text(body),
            "apply_url": d.get("canonicalPositionUrl") or url,
            "updated": datetime.date.fromtimestamp(created).isoformat() if created else "",
            "jobid": jid}


FETCHERS = (("eightfold.ai", _eightfold), ("greenhouse.io", _greenhouse), ("ashbyhq.com", _ashby), ("lever.co", _lever),
            ("smartrecruiters.com", _smartrecruiters), ("myworkdayjobs.com", _workday))


def folder_for(company, role, url, jobid):
    """One place names the application folder. A second posting from the same
    company and role on the same day gets a job-id suffix instead of colliding."""
    base = "{}_{}_{}".format(datetime.date.today().isoformat(), slug(company, 30), slug(role, 45))
    path = os.path.join(APPS, base)
    posting = os.path.join(path, "job-posting.md")
    if os.path.exists(posting) and url not in read(posting):
        base += "-" + slug(str(jobid))[-8:]
    return base


def canonical_url(url):
    """Greenhouse jobs served from an employer's own domain carry only `?gh_jid=<id>`. Find the
    board token on the page and return the canonical job-boards URL, so meta / schema / formpack
    work (F-0012). Anything else comes back unchanged. Same family as the /embed/job_app rewrite."""
    m = re.search(r"[?&]gh_jid=(\d+)", url)
    if not m or "greenhouse.io" in url.lower():
        return url
    jid = m.group(1)
    tokens = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=25) as resp:
            page = resp.read().decode("utf-8", "ignore")
        tokens += re.findall(r"greenhouse\.io/embed/job_(?:board|app)(?:/js)?\?for=([A-Za-z0-9_-]+)", page)
        tokens += re.findall(r"job_board=([A-Za-z0-9_-]+)", page)
        tokens += re.findall(r"boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([A-Za-z0-9_-]+)/jobs", page)
    except Exception:  # noqa: BLE001  (some careers sites answer 403 to non-browsers)
        pass
    # Careers pages often refuse scripts, so also try the board names employers usually pick.
    host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    labels = [l for l in host.split(".") if l not in ("www", "careers", "jobs", "apply", "com", "org",
                                                      "io", "ai", "co", "net", "app", "dev")]
    for name in labels[-1:]:
        name = re.sub(r"[^a-z0-9]", "", name)
        tokens += [name, name + "careers", name + "jobs", name + "inc", name + "hq", name + "com",
                   name + "1", name + "2"]
    for token in dict.fromkeys(t for t in tokens if t):
        try:
            get_json("https://boards-api.greenhouse.io/v1/boards/{}/jobs/{}".format(token, jid))
            return "https://job-boards.greenhouse.io/{}/jobs/{}".format(token, jid)
        except Exception:  # noqa: BLE001
            continue
    return url


def write_posting(j, band, folder, url, posted="", source=""):
    """applications/<folder>/job-posting.md from a fetcher result (meta --write, jobkit gate)."""
    path = os.path.join(APPS, folder)
    os.makedirs(path, exist_ok=True)
    lines = ["**Posted:** {}".format(posted or "unknown"), "",
             "# {} — {}".format(j["role"], j["company"]), "",
             "- **URL:** " + url,
             "- **Apply URL:** " + j["apply_url"],
             "- **Company:** " + j["company"],
             "- **Role:** " + j["role"],
             "- **Location:** " + (j["location"] or "not stated"),
             "- **Platform:** " + j["platform"],
             "- **Pay range published:** " + (fmt_pay(band) if band else "none")
             + (" ({})".format(j["pay_note"]) if j.get("pay_note") else ""),
             "- **Referral source to use:** " + (source or "unknown"),
             "- **Fetched by:** jobkit meta ({} API), verbatim body below".format(j["platform"]),
             "", "---", "", j["body"], ""]
    with io.open(os.path.join(path, "job-posting.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def cmd_meta(args):
    given = args.url
    args.url = canonical_url(args.url)
    fetch = next((fn for host, fn in FETCHERS if host in args.url.lower()), None)
    if not fetch:
        print("NO_META no public job API for this host -- prep fetches the posting itself")
        return 3
    try:
        j = fetch(args.url)
        if j and given != args.url:
            j["apply_url"] = given          # the employer's own page stays the Apply URL
        if not j or not j.get("role"):
            raise ValueError("URL shape not recognised or empty response")
    except Exception as exc:  # noqa: BLE001
        if getattr(exc, "code", None) in (403, 404, 410):
            # Measured 2026-09-19: live postings answer 200 on all five APIs; the
            # 403/404s were every one of them postings that had been taken down.
            print("CLOSED? the {} job API answered {} -- the posting is probably gone. Open the "
                  "link once to confirm before spending a prep on it.".format(
                      next(h for h, _ in FETCHERS if h in args.url.lower()), exc.code))
            return 4
        print("NO_META {}: {} -- prep fetches the posting itself".format(
            type(exc).__name__, str(exc)[:80]))
        return 3

    band = j.get("pay") or pay_from_text(j["body"])
    folder = folder_for(j["company"], j["role"], args.url, j.get("jobid", ""))
    if args.write:
        write_posting(j, band, folder, args.url, args.posted, args.source)
    # Structured copy for `jobkit gate`, which calls this in-process (without --write, then
    # write_posting() once the duplicate and cap gates pass, so a stop leaves no orphan folder).
    args.result = {"company": j["company"], "role": j["role"], "location": j["location"],
                   "platform": j["platform"], "pay": fmt_pay(band), "apply_url": j["apply_url"],
                   "url": args.url, "folder": folder, "_j": j, "_band": band}
    print("{} | {} | {} | {} | pay={} | {} | {}".format(
        j["company"], j["role"], j["location"] or "?", j["platform"], fmt_pay(band),
        j["apply_url"], "applications/" + folder))
    return 0


# ---------------------------------------------------------------------- triage
def form_data_section(heading):
    """Lines of one `## heading` section of form-data.md."""
    out, on = [], False
    for line in read(FORM_DATA).splitlines():
        if line.startswith("## "):
            on = line[3:].strip().lower().startswith(heading.lower())
            continue
        if on:
            out.append(line)
    return out


def autoskip_employers():
    names = []
    for line in form_data_section("Auto-skip employers"):
        if line.startswith("- "):
            names.extend(n.strip().lower() for n in line[2:].split(",") if n.strip())
    return names


NEG = re.compile(r"\b(no|not|without|n't|never|does not|isn't)\b[^.]{0,25}$", re.I)
CLEAR = re.compile(r"security clearance|ts/sci|top secret|secret clearance|public trust"
                   r"|polygraph|\bdod\b|govcloud|\bitar\b|\bear\b controlled", re.I)
CLEAR_STRICT = re.compile(
    r"(active|current|existing|must (have|hold|possess|maintain)|requires? an?|required:?)"
    r"[^.\n]{0,40}(security clearance|ts/sci|top secret|secret clearance|polygraph)", re.I)
CITIZEN = re.compile(r"u\.?s\.? citizen|us person|u\.s\. person|citizenship", re.I)
CITIZEN_STRICT = re.compile(
    r"(must be|requires?|required|only|limited to)[^.\n]{0,30}(u\.?s\.? citizens?|us persons?)"
    r"|u\.?s\.? citizenship (is )?(a )?(required|requirement)|due to itar", re.I)
CITIZEN_SOFT = re.compile(r"permanent resident|green card|authorized to work|or otherwise"
                          r"|asylee|refugee|visa", re.I)
NOSPONSOR = re.compile(r"(not|unable to|cannot|can't|won't|will not|do(es)? not)[^.\n]{0,40}sponsor"
                       r"|no (visa )?sponsorship|without (the need for )?(visa )?sponsorship", re.I)
OPT_BAR = re.compile(r"(not|unable|cannot|can't|won't|exclud\w+|ineligible)[^.\n]{0,50}"
                     r"\b(opt|stem opt|cpt|ead|h-?1b|f-?1)\b", re.I)
EEO_LINE = re.compile(r"without regard to|equal (employment )?opportunity|national origin|protected veteran|"
                      r"affirmative action|genetic information", re.I)
GRAD_CLASS_TITLE = re.compile(r"new grad|college grad|university grad|graduate|campus|intern|co-?op|early career", re.I)
COHORT = re.compile(r"(graduat\w+|degree|class of)[^.\n]{0,40}\b(2026|2027|2028)\b"
                    r"|\b(2026|2027|2028)\b[^.\n]{0,20}(new grad|graduate program|cohort)", re.I)
FOREIGN = re.compile(r"\b(india|gurgaon|bangalore|bengaluru|hyderabad|pune|canada|toronto|vancouver"
                     r"|united kingdom|london|ireland|dublin|germany|berlin|poland|mexico|singapore"
                     r"|australia|philippines|israel|netherlands|france|spain|brazil|japan|china)\b", re.I)
US_HINT = re.compile(r"\b(united states|usa|u\.s\.|us|remote)\b|,\s*[A-Z]{2}\b")
TITLE_SKIP = re.compile(r"\b(principal|director|vp|vice president|head of|distinguished|fellow)\b", re.I)
TITLE_STAFF = re.compile(r"\bstaff\b", re.I)
TITLE_STAFF_OK = re.compile(r"member of (the )?technical staff|chief of staff|staffing|\bmts\b", re.I)
TITLE_UNSURE = re.compile(r"\b(senior|sr\.?|lead|manager|architect|intern|internship|co-?op|iii|iv)\b", re.I)
NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15}
_NUMWORD = r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen)\b"
# The upper bound of a range may be a word too: "one to three years" must match at "one" (the
# lower bound), not fall through to "three years" (Exiger, 2026-09-22 holdout).
# (?<!\d) / (?!\d): "100+ years of collective experience" must not match "10" inside "100" (Midpoint Markets 2026-09-29).
YOE = re.compile(r"(?<!\d)(\d{1,2}(?!\d)|" + _NUMWORD + r")\s*\+?\s*"
                 r"(?:-|–|to)?\s*(?:(?:\d{1,2}|" + _NUMWORD + r")\s*)?\+?\s*years?", re.I)
# "You don't need 10 years of experience", "no need for 5+ years": the figure is waived, not asked.
YOE_NEG = re.compile(r"(\b(don['’]?t|do not|doesn['’]?t|does not|won['’]?t|will not|needn['’]?t)\s+(need|require|have to have)"
                     r"|\bno need (for|to have)|\bnot required to have)\s+(\w+\s+){0,2}$", re.I)


def yoe_value(match):
    g = match.group(1).lower()
    return NUMWORDS.get(g) or int(g)
# An employer REFUSING sponsorship, in its own voice. The looser NOSPONSOR stays a flag only.
NOSPONSOR_STRICT = re.compile(
    r"\b(unable to|cannot|can't|can not|will not|won't|does not|do not|not able to|are not able to|is not able to)\s+"
    r"(?:\w+\s+){0,3}?(sponsor|provide (visa )?sponsorship|offer (visa )?sponsorship|support (visa )?sponsorship)"
    r"|sponsorship (is|will) not (be )?(available|offered|provided)"
    r"|without (the need for |requiring |needing )?(current or future )?(visa |employer |employment )?sponsorship"
    r"|not eligible for (visa )?sponsorship", re.I)
# Prep agents write notes INTO job-posting.md ("No sponsorship statement either way", "No ITAR
# language"). A line describing that something is ABSENT must never trigger a skip.
META_NOTE = re.compile(
    r"^\W*(no|none|not an?|nothing|unknown|n/a)\b|either way|not a (sponsorship|red|skip|hard)|auto-skip"
    r"|\bno\b[^.\n]{0,60}\b(language|statement|requirement|question|mention|restriction|gate)\b"
    r"|\b(none|nothing)\b[^.\n]{0,40}\b(found|present|stated|posting)|frequently|often|typically|usually|tend to|may not|might not|clearance or ITAR|ITAR or |routinely sponsors|\bsponsors\b|the user", re.I)
SPONSOR_OK = re.compile(r"\b(will|can|able to|happy to|do|does)\s+(provide\s+|offer\s+)?sponsor|"
                        r"sponsorship (is )?(available|offered|provided)", re.I)
RESIDE = re.compile(r"must (currently )?(reside|live|be located|be based)\b|local candidates only|"
                    r"residents? of [A-Z][a-z]+ only", re.I)
US_WIDE = re.compile(r"\b(united states|u\.s\.a?\.?|usa|us\b|within the us|in the us|north america)", re.I)
ITAR = re.compile(r"\bITAR\b[^.\n]{0,40}(requirement|restrict|compliance|regulat)|"
                  r"(requirement|restrict|subject to|comply with)[^.\n]{0,40}\bITAR\b|\bU\.?S\.? persons?\b", re.I)
YOE_HISTORY = re.compile(r"history|founded|collective|combined experience|for over|spans|anniversary|year-old|years old|in business|"
                         r"\b(we|our|the company) (have|has) (spent|been) (more than |over )?\w+ years|"
                         r"years (of )?(driving|serving|leading|innovating|delivering|helping) |celebrat\w* \d+ years|"
                         r"\d+ years (in|of) (the )?(industry|business|financial services|market)|"
                         # company age in the employer's voice: "With over 50 years of experience, we ..."
                         r"\bwith (over|more than|nearly|almost) \w+\+? years of (experience|expertise)\W{0,3}(we|our)\b", re.I)
YOE_SOFT = re.compile(r"prefer|nice to have|bonus|a plus|ideally|desired|or equivalent|masters?|m\.s\.|advanced degree", re.I)
GOV = re.compile(r"\b(state of|county|city of|department of|federal|commonwealth of|"
                 r"public (agency|school|utility)|authority|\.gov\b)", re.I)
GOV_CONTRACTOR = re.compile(r"national security|federal (agenc|government|contract|client|customer|civilian)|"
                            r"government contract|\bDoD\b|\bDHS\b|department of defense|homeland security|"
                            r"intelligence community|public sector (client|customer)|\bGSA\b", re.I)
# Hedged contractor wording ("This role may involve work on federal government contracts",
# About Healthcare 2026-09-24): a flag for the agent, never the low-pay + government skip.
GOV_CONTRACTOR_SOFT = re.compile(r"\b(may|might|could)\s+(also\s+)?(involve|support|include)\b|"
                                 r"\bsome work (on|for|with)\b|\boccasional(ly)?\b", re.I)
# "degree ... and/or 4 years equivalent work experience" or "4 years of experience in lieu of a
# degree" is a substitute for the degree, not an experience bar (Hensel Phelps 2026-09-08).
YOE_DEGREE_SUB_PRE = re.compile(r"\bdegree\b[^.\n]{0,200}\b(and/or|or)\s+(\w+\s+){0,3}$", re.I)
YOE_DEGREE_SUB_POST = re.compile(r"^\s*(of\s+)?(equivalent|comparable)\b", re.I)
YOE_IN_LIEU = re.compile(r"^\s*(of\s+)?(\w+\s+){0,3}experience\s+in lieu of\s+(a\s+|an\s+)?(\w+\s+)?degree", re.I)
EVERIFY = re.compile(r"e-?verify", re.I)
FLOOR = 120000


def gov_contract_hit(body):
    """(kind, excerpt) for the first contractor mention: "hard" if any mention is stated flatly,
    "soft" if every mention is hedged by GOV_CONTRACTOR_SOFT in its own sentence; None if none."""
    first_soft = None
    for m in GOV_CONTRACTOR.finditer(body):
        # Standard E-Verify participation notices name DHS ("www.DHS.gov/E-Verify"); that is
        # employment-eligibility boilerplate, not government / contractor work.
        if EVERIFY.search(body[max(0, m.start() - 250):m.end() + 250]):
            continue
        start =max(body.rfind(".", 0, m.start()), body.rfind("\n", 0, m.start()), m.start() - 120) + 1
        excerpt = body[max(0, m.start() - 80):m.end() + 120].replace("\n", " ")
        if GOV_CONTRACTOR_SOFT.search(body[start:m.start()]):
            first_soft = first_soft or excerpt
        else:
            return "hard", excerpt
    return ("soft", first_soft) if first_soft else None


def _field(text, name):
    m = re.search(r"^- \*\*{}:\*\*\s*(.+)$".format(re.escape(name)), text, re.M)
    return m.group(1).strip() if m else ""


def cmd_triage(args):
    path = args.target
    if os.path.isdir(path):
        path = os.path.join(path, "job-posting.md")
    if not os.path.exists(path):
        print("UNSURE no job-posting.md at {} -- nothing to triage".format(path))
        return 0
    text = read(path)
    company, role = _field(text, "Company"), _field(text, "Role")
    if not role:
        m = re.search(r"^# (.+?) — (.+)$", text, re.M)
        if m:
            role, company = m.group(1), company or m.group(2)
    body = text.split("\n---\n", 1)[-1]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if s.strip()]
    skips, unsure, notes = [], [], []
    first_req = None        # first stated years-of-experience requirement in the posting
    title_flag = False

    hit = next((n for n in autoskip_employers() if n and re.search(
        r"\b" + re.escape(n) + r"\b", company.lower())), None)
    if hit:
        skips.append("defense/gov auto-skip employer ({})".format(hit))

    # A graduating-class program for a later year: the user has graduated and is available now.
    # "2027 Software Engineer New College Grad" cost a full prep before being skipped (F-0001).
    next_year = datetime.date.today().year + 1
    years_in_title = [int(y) for y in re.findall(r"\b(20\d\d)\b", role)]
    if GRAD_CLASS_TITLE.search(role) and any(y >= next_year for y in years_in_title):
        # A FLAG, not a skip: the holdout showed the user does apply to "New Grad 2027" programs
        # so the agent or the user decides; the line just makes it visible early.
        unsure.append(("COHORT", "title names a {} graduating class: {}".format(max(years_in_title), role)))

    if TITLE_SKIP.search(role) or (TITLE_STAFF.search(role) and not TITLE_STAFF_OK.search(role)):
        skips.append("seniority tier in title ({})".format(role))
    elif TITLE_UNSURE.search(role):
        title_flag = True       # resolved after the body scan, once the experience bar is known

    location = _field(text, "Location")
    if location and FOREIGN.search(location) and not US_HINT.search(location):
        unsure.append(("LOCATION", location))

    for s in sentences:
        short = s[:220]
        m = CLEAR_STRICT.search(s)
        if m and not NEG.search(s[:m.start()]) and "prefer" not in s.lower():
            skips.append('clearance required: "{}"'.format(short))
        elif CLEAR.search(s) and not EEO_LINE.search(s):
            unsure.append(("CLEARANCE", short))
        m = CITIZEN_STRICT.search(s)
        if m and not CITIZEN_SOFT.search(s) and not NEG.search(s[:m.start()]):
            skips.append('US citizenship required: "{}"'.format(short))
        elif CITIZEN.search(s) and not EEO_LINE.search(s):
            unsure.append(("CITIZENSHIP", short))
        # the standing rules, 2026-09-20 (from 50 hand-labelled postings: these four text rules
        # reproduced 32 of 32 of the user's skips, where the matcher's ranking did no better than chance).
        if NOSPONSOR_STRICT.search(s) and not SPONSOR_OK.search(s) and not META_NOTE.search(s) and "?" not in s:   # a screener QUESTION about sponsorship is not a refusal
            skips.append('no visa sponsorship: "{}"'.format(short))
        elif NOSPONSOR.search(s) or OPT_BAR.search(s):
            unsure.append(("SPONSORSHIP", short))
        if COHORT.search(s):
            unsure.append(("COHORT", short))
        m = RESIDE.search(s)
        if m and not US_WIDE.search(s[m.start():m.start() + 120]) and not META_NOTE.search(s):
            unsure.append(("RESIDENCY", short))      # a flag, not a skip: the user can relocate
        # Years of experience: the user's degree covers a requirement of up to 2 years; 3+ is a skip.
        # group(1) is the LOWER bound of a range, so "2-6 years" stays a judgement call.
        # The FIRST figure that sits next to an experience word is the requirement; scraped
        # postings often run a whole list together, so judge a window, not the sentence.
        for y in YOE.finditer(s):
            win = s[max(0, y.start() - 90):y.end() + 70]
            if not re.search(r"experience|professional|industry|hands-on", win, re.I) or YOE_HISTORY.search(win):
                continue
            if YOE_NEG.search(s[max(0, y.start() - 40):y.start()]):
                continue
            post = s[y.end():y.end() + 80]
            if YOE_IN_LIEU.search(post) or (YOE_DEGREE_SUB_POST.search(post)
                                            and YOE_DEGREE_SUB_PRE.search(s[max(0, y.start() - 220):y.start()])):
                continue        # degree substitute, not an experience bar
            n_years = yoe_value(y)
            if first_req is None:
                first_req = n_years
                if n_years >= 3 and not YOE_SOFT.search(win) and not META_NOTE.search(s):
                    skips.append('{}+ years of experience required: "{}"'.format(n_years, win.strip()[:200]))
                elif n_years >= 3:
                    unsure.append(("YOE", win.strip()[:200]))
            elif n_years >= 5:
                unsure.append(("YOE", win.strip()[:200]))
            break
        m = ITAR.search(s)
        if m and not META_NOTE.search(s) and not NEG.search(s[:m.start()]):
            skips.append('ITAR / US-person requirement: "{}"'.format(short))

    if title_flag:
        # the user rejected 16 of 16 Senior / Sr / Lead titles (2026-09-20). Keep the old nuance:
        # a "Senior" title whose own bar is 2 years or less stays a judgement call.
        mixed = re.search(r"entry|junior|\bjr\b|new grad|graduate|early|associate|all levels|across levels|\bI{1,2}\b", role, re.I)
        if re.search(r"\b(senior|sr\.?|lead)\b", role, re.I) and not mixed and (first_req is None or first_req >= 3):
            skips.append("seniority tier in title ({}), experience bar {}".format(
                role, "not stated" if first_req is None else "{}+ years".format(first_req)))
        else:
            unsure.append(("TITLE", role))

    band = None
    pay_line = _field(text, "Pay range published")
    if pay_line and pay_line != "none":
        band = pay_from_text(pay_line, line=True)
    band = band or pay_from_text(body)
    gc = gov_contract_hit(body)
    if band:
        if band[1] < FLOOR:
            if GOV.search(company) or GOV.search(body[:600]) or (gc and gc[0] == "hard"):
                skips.append("whole pay band under the floor ({}) AND government employer".format(fmt_pay(band)))
            elif gc:
                notes.append("pay band {} tops out under the floor; contractor wording is hedged, so not a skip".format(fmt_pay(band)))
            else:
                notes.append("pay band {} tops out under the floor (not a skip on its own)".format(fmt_pay(band)))
        elif band[0] >= 200000:
            unsure.append(("PAY", "band {} starts far above the range -- usually a senior role whatever the title says".format(fmt_pay(band))))
        elif band[0] > 150000:
            notes.append("pay band {} outside the target range -- salary answer follows the posting: {}".format(
                fmt_pay(band), salary_answer(band)["text"]))

    if gc and not skips:
        unsure.append(("GOV-CONTRACTOR" if gc[0] == "hard" else "GOV-CONTRACTOR-SOFT", gc[1]))

    if skips:
        print("SKIP " + skips[0])
        for s in skips[1:]:
            print("  also: " + s)
    elif unsure:
        print("UNSURE {} flag(s) -- read these lines, skip only on a genuine eligibility bar:".format(len(unsure)))
        seen = set()
        for kind, line in unsure:
            if (kind, line) not in seen:
                seen.add((kind, line))
                print("  {}: {}".format(kind, line))
    else:
        print("PASS")
    for n in notes[:4]:
        print("  note: " + n)
    return 0


# -------------------------------------------------------------------- formpack
def detex(s):
    s = re.sub(r"\\href\{[^}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}", r"\1", s)
    for _ in range(3):
        s = re.sub(r"\\(?:textbf|textit|emph|underline|textsc|small|bf|it)\s*\{((?:[^{}])*)\}", r"\1", s)
    s = re.sub(r"\{\\(?:bf|it|em)\s+([^{}]*)\}", r"\1", s)
    s = s.replace("\\hfill", " ").replace("\\\\", " ")
    s = s.replace("---", "—").replace("--", "–")
    s = re.sub(r"\\([%&$#_{}])", r"\1", s)
    s = s.replace("~", " ").replace("\\,", " ").replace("``", '"').replace("''", '"')
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", "", s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def tex_section(tex, name):
    m = re.search(r"\\begin\{rSection\}\{" + re.escape(name) + r"\}(.*?)\\end\{rSection\}", tex, re.S)
    return m.group(1) if m else ""


def parse_experience(tex):
    sec = tex_section(tex, "Work Experience")
    entries = []
    head = re.compile(r"\\textbf\{(?P<title>[^}]*)\}\s*\\hfill\s*\\textit\{(?P<loc>[^}]*)\}\s*\\\\\s*\n"
                      r"\s*(?P<emp>.+?)\\hfill\s*\\textit\{(?P<dates>[^}]*)\}")
    marks = list(head.finditer(sec))
    for i, m in enumerate(marks):
        chunk = sec[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(sec)]
        bullets = [detex(b) for b in re.findall(r"\\item\s+(.*?)(?=\\item|\\end\{itemize\})", chunk, re.S)]
        entries.append({"title": detex(m.group("title")), "location": detex(m.group("loc")),
                        "employer": detex(m.group("emp")), "dates": detex(m.group("dates")),
                        "bullets": [b for b in bullets if b]})
    return entries


def parse_projects(tex):
    sec = tex_section(tex, "Selected Projects") or tex_section(tex, "Projects")
    out = []
    for m in re.finditer(r"\\item\s*\\textbf\{([^}]*)\}", sec):
        out.append(detex(m.group(1)))
    return out


MONTHS = {m: i + 1 for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split())}


def split_dates(dates):
    parts = re.split(r"\s*[–—-]+\s*", dates)
    def one(p):
        m = re.match(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", p.strip())
        if not m:
            return p.strip()
        return "{} {} ({:02d}/{})".format(m.group(1), m.group(2),
                                          MONTHS.get(m.group(1).lower(), 0), m.group(2))
    start = one(parts[0]) if parts else ""
    end = one(parts[1]) if len(parts) > 1 else ""
    current = "present" in end.lower()
    return start, ("Present" if current else end), current


def table_rows(lines):
    rows = []
    for line in lines:
        if line.startswith("|") and not re.match(r"^\|\s*-{3,}", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def employer_lookup():
    """employer keyword -> (reason for leaving, location) from form-data.md."""
    sec = form_data_section("Employment")
    reasons = table_rows(sec)[1:]
    loc_text = " ".join(l for l in sec if not l.startswith("|"))
    out = []
    for emp, reason in (r[:2] for r in reasons if len(r) >= 2):
        key = re.sub(r"[^a-z0-9 ]", " ", emp.lower()).split()
        out.append((key, emp, reason))
    return out, loc_text


def match_employer(name, title, table):
    toks = set(re.sub(r"[^a-z0-9 ]", " ", (name + " " + title).lower()).split())
    best, score = None, 0
    for key, emp, reason in table:
        s = len(toks & set(key))
        if s > score:
            best, score = (emp, reason), s
    return best if score >= 2 else None


def pdf_text(path):
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    for c in (0x2010, 0x2011, 0x2012, 0x2212):
        text = text.replace(chr(c), "-")
    return text


def squash(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


ROLE_ABBREV = ((r"software development engineer in test", "SDET"),
               (r"software (development )?engineer(ing)?|software developer", "SWE"),
               (r"cyber\s*security", "Cybersec"),
               (r"machine learning", "ML"),
               (r"artificial intelligence", "AI"))
ROLE_DROP = {"senior", "sr", "jr", "junior", "i", "ii", "iii", "iv", "v", "new", "grad", "grads",
             "graduate", "college", "university", "early", "career", "entry", "level", "associate",
             "mid", "in", "of", "the", "and", "for", "to", "at", "a", "an"}


def role_tag(role):
    """Short file-name tag for the role-named resume copy: "Software Engineer II" -> SWE,
    "Cybersecurity Analyst" -> Cybersec_Analyst. ASCII letters/digits/underscores, max 4 words."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", role or "")
    if ":" in s:    # "Early Career: IT Security Engineer" -> after; "SWE: Payments" -> before
        pre, post = s.split(":", 1)
        pre_level = all(t.lower() in ROLE_DROP or re.fullmatch(r"20\d\d", t) for t in re.findall(r"[A-Za-z0-9]+", pre))
        s = post if pre_level else pre
    s = re.split(r",|\s[-–—|/]\s|\s[–—]|[–—]\s", s)[0]
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    for pat, rep in ROLE_ABBREV:
        s = re.sub(r"\b(?:" + pat + r")\b", rep, s, flags=re.I)
    words = [t for t in re.findall(r"[A-Za-z0-9]+", s)       # 20xx cohort years and bare levels 1-5 drop
             if t.lower() not in ROLE_DROP and not re.fullmatch(r"20\d\d|[1-5]", t)]
    words = [t[0].upper() + t[1:] if t.islower() else t for t in words][:4]
    return "_".join(words) or "Resume"


def cmd_formpack(args):
    folder = args.folder if os.path.isabs(args.folder) else os.path.join(ROOT, args.folder)
    tex_path, pdf_path = os.path.join(folder, RESUME_TEX), os.path.join(folder, RESUME_PDF)
    for p in (tex_path, pdf_path):
        if not os.path.exists(p):
            print("FORMPACK_FAILED missing {}".format(p))
            return 1
    tex = read(tex_path)
    entries = parse_experience(tex)
    if len(entries) < 3:
        print("FORMPACK_FAILED parsed only {} work-experience entries from the .tex "
              "(floor is 3) -- the resume layout changed; write the pack by hand".format(len(entries)))
        return 1
    page = squash(pdf_text(pdf_path))
    for e in entries:
        for b in e["bullets"]:
            probe = squash(b)[:60]
            if probe and probe not in page:
                print("FORMPACK_FAILED a parsed bullet is not on the compiled PDF (stale PDF or "
                      "parse error): \"{}...\"".format(b[:70]))
                return 1
        if len(e["bullets"]) < 1:
            print("FORMPACK_FAILED entry with no bullets: {}".format(e["employer"]))
            return 1

    # Role-named copy for upload (the user, 2026-09-28): recruiters see "Resume_SWE.pdf".
    # Resume_Resume.pdf/.tex stay the working files every other command reads. An older
    # copy under a different tag is left alone (never delete files here).
    upload_pdf = os.path.normpath(os.path.abspath(
        os.path.join(folder, "Resume_{}.pdf".format(role_tag(args.role)))))
    if os.path.normcase(upload_pdf) != os.path.normcase(os.path.normpath(os.path.abspath(pdf_path))):
        shutil.copy2(pdf_path, upload_pdf)

    table, loc_text = employer_lookup()
    out = []
    w = out.append
    w("# Form Pack — {} @ {}".format(args.role, args.company))
    w("")
    w("> Sections down to **Work experience** are generated by `jobkit formpack` from")
    w("> `form-data.md`, `profile.md` and the tailored `.tex`. Do not retype them. The prep")
    w("> agent may edit the **Flags:** line below (e.g. `t2-h1b`) and appends **FILL PLAN**,")
    w("> **Screener answers** and an optional `## Notes for this posting` at the bottom.")
    w("")
    w("**Apply URL (resolved):** " + args.url)
    w("**Platform:** `{}`".format(args.platform))
    w("**Referral source:** **{}** — if not offered, the company careers-site option, then "
      "\"Other\" with `{}` typed in.".format(args.source, args.source))
    w("**Résumé PDF:** `{}`".format(upload_pdf))
    w("**Published pay range:** {}".format(args.pay or "none"))
    w("**Flags:** none")
    w("**Posted:** {}".format(args.posted or "unknown"))
    w("")

    play = os.path.join(SKILL_DIR, "ats", args.platform + ".md")
    if not os.path.exists(play):
        play = os.path.join(SKILL_DIR, "ats", "_unknown.md")
    w("---\n\n## Platform playbook (verbatim from `ats\\{}`) — the fill phase does not re-read it\n"
      .format(os.path.basename(play)))
    w(re.sub(r"(?m)^#", "###", read(play)).strip())
    w("")

    for title, heading in (("Identity", "Identity"),
                           ("Locked fields — FILLED, not asked", "Locked fields"),
                           ("Standard defaults", "Standard defaults"),
                           ("Not known — leave blank", "Not known")):
        w("---\n\n## " + title + "\n")
        sec = form_data_section(heading)
        body = [l for l in sec if l.startswith("|") or l.startswith("- ")]
        if heading == "Locked fields":
            # desired salary is computed per posting from its published band (salary_answer)
            keep = [l for l in body if not re.match(r"\|\s*(Salary expectation|Forced single number)", l)]
            at = next((i for i, l in enumerate(keep) if l.startswith("| Notice period")), len(keep))
            body = keep[:at] + salary_rows(args.pay) + keep[at:]
        out.extend(body)
        w("")

    w("---\n\n## Education — enter BOTH, every sub-field\n")
    out.extend(l for l in form_data_section("Education") if l.startswith("|"))
    w("")
    out.extend(l for l in form_data_section("Form-pack notes — education") if l.startswith("- "))
    w("")
    w("---\n\n## Certification\n")
    out.extend(l for l in form_data_section("Certifications") if l.startswith("|"))
    w("\n---\n\n## Languages\n")
    out.extend(l for l in form_data_section("Languages") if l.startswith("|"))
    w("\n---\n\n## Transcripts\n")
    out.extend(l for l in form_data_section("Transcripts") if l.startswith("|"))
    out.extend(l for l in form_data_section("Form-pack notes — transcripts") if l.startswith("- "))
    w("")

    w("---\n\n## Work experience — {} entries, in PDF order (enter every one, every field)\n"
      .format(len(entries)))
    for i, e in enumerate(entries, 1):
        start, end, current = split_dates(e["dates"])
        hit = match_employer(e["employer"], e["title"], table)
        w("### {}. {} — {}".format(i, e["title"], e["employer"]))
        w("")
        w("| Field | Value |")
        w("|---|---|")
        w("| Job title | {} |".format(e["title"]))
        w("| Employer | {} |".format(e["employer"]))
        w("| Location | {} |".format(e["location"]))
        w("| Start | {} (day, if forced: 15) |".format(start))
        w("| End | {} |".format("— tick **I currently work here**, no end date" if current else end + " (day, if forced: 15)"))
        w("| Reason for leaving | {} |".format(hit[1] if hit else "NOT IN form-data.md — leave blank"))
        w("")
        w("Description (paste whole, verify after save):")
        w("")
        w("```")
        for b in e["bullets"]:
            w("• " + b)
        w("```")
        w("({} chars)".format(sum(len(b) + 2 for b in e["bullets"])))
        w("")
    projects = parse_projects(tex)
    if projects:
        w("Projects on the PDF, in order (for a Projects section if the form offers one): "
          + "; ".join(projects) + ". Bullets: copy from the PDF.")
        w("")

    w("---\n\n## Form schema (raw `jobkit schema` output)\n")
    try:
        res = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "jobkit.py"), "schema", args.url],
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
        schema = (res.stdout or "") + (res.stderr or "")
    except Exception as exc:  # noqa: BLE001
        schema = "SCHEMA_FAILED: {}".format(exc)
    has_schema = "NO_SCHEMA_API" not in schema and "SCHEMA_FAILED" not in schema
    w("```\n" + schema.strip() + "\n```\n")
    w("---\n\n## FILL PLAN\n")
    if has_schema:
        w("<!-- PREP AGENT: replace this line with the ordered `field key -> value` list, every "
          "dropdown answer matched to the schema's own option strings, real-click fields flagged. -->")
    else:
        w("**NO SCHEMA — DOM path.** The fill phase explores the form itself.")
    w("\n---\n\n## Screener answers\n")
    w("<!-- PREP AGENT: paste screener-answers.md here verbatim, each answer with its character count. -->")
    w("")

    dest = os.path.join(folder, "form-pack.md")
    with io.open(dest, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("formpack OK {} | upload copy {} | work-ex {} entries, bullets verified against the PDF | schema={} | "
          "TODO for prep: {}Screener answers".format(
              dest, os.path.basename(upload_pdf), len(entries), "yes" if has_schema else "none",
              "FILL PLAN + " if has_schema else ""))
    return 0


# ----------------------------------------------------------------------- audit
LAYOUT = re.compile(r"\\(?:hyphenpenalty|exhyphenpenalty|emergencystretch|tolerance)\s*=\s*[\d.]+\w*"
                    r"|\\(?:vspace|hspace|fontsize|setlength|usepackage|documentclass|geometry"
                    r"|newcommand|setmainfont|begin\{tabular\})\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})*")
NUM = re.compile(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?")
TECH = re.compile(r"[A-Za-z][A-Za-z0-9+#]*(?:[./-][A-Za-z0-9+#]+)*")


def _plain(tex):
    body = tex.split("\\begin{document}", 1)[-1]
    body = re.sub(r"(?m)(?<!\\)%.*$", "", body)
    body = LAYOUT.sub(" ", body)
    body = re.sub(r"\\href\{[^}]*\}", " ", body)
    return detex(body)


def cmd_audit(args):
    if not os.path.exists(args.tex):
        print("audit ERROR no such file: {}".format(args.tex))
        return 1
    tex = read(args.tex)
    source_raw = read(POOL) + "\n" + read(PROFILE)
    source = detex(re.sub(r"(?m)^\s*%+", " ", LAYOUT.sub(" ", source_raw)))
    src_nums = {n.replace(",", "") for n in NUM.findall(source)}
    src_words = {w.lower() for w in TECH.findall(source)}
    # Skills-inventory wording is a third source for TERMS only -- never for numbers.
    inv_text = " ".join(" ".join([r["wording"]] + r["terms"])
                        for r in load_inventory() if not r["banned"])
    src_words |= {w.lower() for w in TECH.findall(inv_text)}
    inv_num_wordings = [detex(r["wording"]) for r in load_inventory()
                        if not r["banned"] and re.search(r"\d", r["wording"])]
    src_squash = squash(source) + " " + re.sub(r"\d", "", squash(inv_text))

    posting = os.path.join(os.path.dirname(os.path.abspath(args.tex)), "job-posting.md")
    post_words = {w.lower() for w in TECH.findall(read(posting))} if os.path.exists(posting) else set()

    fails, warns, ctx_warns = [], [], []
    for raw in tex.split("\\begin{document}", 1)[-1].splitlines():
        line = _plain(raw)
        if not line:
            continue
        for nm in NUM.finditer(line):
            n = nm.group(0)
            if n.replace(",", "") not in src_nums and any(
                    w.lower() in line.lower() and n in NUM.findall(w) for w in inv_num_wordings):
                continue        # part of an approved skill wording, e.g. "OAuth 2.0" (F-0017)
            if n.replace(",", "") not in src_nums:
                fails.append((n, line[:110]))
                continue
            # The number exists somewhere in the pool -- but "12" existing does not
            # make "12-person team" true. It must sit next to the same word it
            # sits next to in the pool, on at least one side.
            prev = re.findall(r"[A-Za-z0-9.]+", line[:nm.start()])[-1:]
            nxt = re.findall(r"[A-Za-z0-9.]+", line[nm.end():])[:1]
            sides = [squash(p + n) for p in prev] + [squash(n + x) for x in nxt]
            if sides and not any(s in src_squash for s in sides):
                ctx_warns.append((n, line[max(0, nm.start() - 40):nm.end() + 40]))
        for m_ in TECH.finditer(line):
            w_ = m_.group(0)
            before = line[:m_.start()].rstrip()
            opener = not before or before[-1] in ".:;•"   # sentence start, not a proper noun
            if len(w_) < 2 or w_.lower() in src_words:
                continue
            techish = (any(c.isdigit() for c in w_) or any(c in "+#./-" for c in w_)
                       or any(c.isupper() for c in w_[1:]) or (w_[0].isupper() and not opener))
            if not techish:
                continue
            if squash(w_) and squash(w_) in src_squash:   # "CI/CD" vs "CI / CD", hyphenation
                continue
            warns.append((w_, "in posting" if w_.lower() in post_words else "NOT in posting", line[:90]))

    seen = set()
    warns = [w_ for w_ in warns if not (w_[0].lower() in seen or seen.add(w_[0].lower()))]
    if fails:
        print("audit FAIL -- {} number(s) not found in content-pool.tex or profile.md:".format(len(fails)))
        for n, line in fails:
            print("  {}  <-  {}".format(n, line))
    if warns:
        print("audit {} -- {} term(s) not in the pool; justify each in the match report "
              "(truthful mirror of the posting) or revert it:".format(
                  "WARN" if not fails else "also WARN", len(warns)))
        for w_, where, line in warns[:25]:
            print("  {} ({})  <-  {}".format(w_, where, line))
    if ctx_warns:
        print("audit NUMBER-CONTEXT -- {} number(s) exist in the pool but next to different words; "
              "confirm each still measures the same thing:".format(len(ctx_warns)))
        for n, ctx in ctx_warns[:15]:
            print("  {}  <-  ...{}...".format(n, ctx))
    if not fails and not warns and not ctx_warns:
        print("audit OK -- every number and tech term traces to the pool or profile")
    return 2 if fails else 0


# ---------------------------------------------------------------------- skills
# Master skills inventory (added 2026-09-19). The pool stores every bullet, but
# the only store of "true, just not always listed" skills was a prose sentence in
# resume-style.md, so prep re-derived "is this keyword true?" by judgement and
# dropped real ones (measured: a resume shipped at 6/30 coverage). The
# inventory is one row per skill with its evidence and the only wording allowed
# on the page; this command matches a posting against it.
INVENTORY = os.path.join(ROOT, "master", "skills-inventory.md")
INV_COLS = ("skill", "aliases", "level", "evidence", "wording", "row", "never")
# inventory row category -> resume track. Languages and Practices say nothing about the track.
TRACK_OF_ROW = {"security": "security", "ml": "ai", "backend": "software", "data": "software",
                "cloud": "software", "testing": "software", "project": "software"}
TRACK_PRIORITY = ["security", "ai", "software"]       # when a title names several, this one is the base
TITLE_WEIGHT = 6                                      # a track word in the title is worth this many hits
SECURITY_TITLE = re.compile(r"security|appsec|infosec|\bsoc\b|detection|threat|vulnerab|incident|\bgrc\b|cyber", re.I)
AI_TITLE = re.compile(r"\bAI\b|\bML\b|machine learning|\bLLM\b|applied ai|genai|generative|data scien|\bNLP\b", re.I)
SOFTWARE_TITLE = re.compile(r"software|full.?stack|back.?end|front.?end|developer|\bsdet\b|\bweb\b|mobile|platform", re.I)
TITLE_RX = {"security": SECURITY_TITLE, "ai": AI_TITLE, "software": SOFTWARE_TITLE}
# Sections that describe the employer, not the job. A keyword that only appears here must not
# pick the track (one posting's only AI phrase sat in its About paragraph).
BOILER_HEAD = re.compile(r"about (us|the company|[A-Z]\w+)|who we are|our (company|story|mission|values)|"
                         r"benefits|perks|compensation|equal (employment )?opportunity|\beeo\b|why (join|work)|"
                         r"what we offer|life at", re.I)
KEYWORD_HEAD = re.compile(r"(?ims)^#{1,4}\s*(keywords?|key words|required skills|skills|technologies|tech stack)\b[^\n]*\n"
                          r"(.*?)(?=^#{1,4} |\Z)")
# General technology vocabulary, used ONLY to notice a posting term the inventory has no row for
# (a headline requirement once came out as neither TRUE, BANNED nor GAP).
# Seeded from an aggregator's skill vocabulary; copied, not imported, so the two
# projects stay independent. Terms in CASE_SENSITIVE_VOCAB are ordinary English words too.
TECH_VOCAB = [
    "ActiveMQ", "Airflow", "Angular", "Ansible", "ArgoCD", "ASP.NET", "Avro", "Azure DevOps", "BigQuery",
    "C#", ".NET", "Cassandra", "CircleCI", "ClickHouse", "CloudFormation", "CockroachDB", "Cypress", "Dart",
    "Datadog", "dbt", "Django", "DynamoDB", "EC2", "Elasticsearch", "Elixir", "Envoy", "Express.js", "Flask",
    "Flink", "Flutter", "GCP", "Google Cloud", "GitLab CI", "Go", "Golang", "Gradle", "Grafana", "GraphQL",
    "gRPC", "Hadoop", "Helm", "Hugging Face", "Istio", "Jenkins", "Jest", "Jira", "JUnit", "Kafka", "Kotlin",
    "Kubernetes", "LangChain", "Laravel", "LlamaIndex", "MATLAB", "Maven", "MLflow", "MongoDB", "MySQL",
    "NestJS", "New Relic", "Nginx", "Nuxt", "Objective-C", "OpenTelemetry", "Oracle", "Perl", "PHP",
    "Pinecone", "Power BI", "Prometheus", "Pulumi", "PyTorch", "RabbitMQ", "Rails", "Ruby", "Redis",
    "Redshift", "Rust", "S3", "Salesforce", "SAP", "Scala", "Selenium", "Sentry", "ServiceNow", "Snowflake",
    "Snyk", "SonarQube", "Spark", "Spring", "Spring Boot", "SQL Server", "Svelte", "Swift", "SwiftUI",
    "Tableau", "TensorFlow", "Terraform", "Unity", "Unreal", "Vue", "Webpack", "WebSockets", "Xamarin",
    # security / detection tooling (one posting named six of these and none surfaced)
    "Sigma", "YARA", "CrowdStrike", "Microsoft Defender", "Defender for Endpoint", "SentinelOne",
    "Carbon Black", "Tanium", "Microsoft Sentinel", "Azure Sentinel", "QRadar", "Elastic Security", "Chronicle",
    "Sumo Logic", "Palo Alto", "Cortex XSOAR", "XSOAR", "SOAR", "Tenable", "Qualys", "Rapid7", "Okta",
    "CyberArk", "SailPoint", "Zscaler", "Proofpoint", "Wiz", "Prisma Cloud", "Snort", "Suricata", "Zeek",
    "Velociraptor", "osquery", "Semgrep", "Checkmarx", "Veracode", "Fortinet", "KQL", "PCI DSS", "HIPAA",
    "SOC 2", "FedRAMP", "GDPR",
]
CASE_SENSITIVE_VOCAB = {"Sigma", "Chronicle", "Wiz", "Zeek", "SOAR", "Okta", "Go", "Dart", "Helm", "Spark", "Spring", "Swift", "Rails", "Ruby", "Rust", "Flask",
                        "Unity", "Unreal", "Oracle", "Sentry", "Envoy", "Perl", "Scala", "Jest", "SAP", "Vue"}


def load_inventory():
    if not os.path.exists(INVENTORY):
        return []
    rows = []
    for cells in table_rows(read(INVENTORY).splitlines()):
        if len(cells) < len(INV_COLS) or cells[0].lower() == "skill":
            continue
        r = dict(zip(INV_COLS, cells))
        r["terms"] = [r["skill"]] + [a.strip() for a in r["aliases"].split(";") if a.strip(" -")]
        r["banned"] = r["level"].lower().startswith("banned")
        rows.append(r)
    return rows


def _term_re(term, case_sensitive=False):
    # 1-2 letter names ("Go", "R", "C") are only ever meant case-sensitively.
    if len(term) <= 2 or case_sensitive:      # "Go-getter" is not Go, "swift response" is not Swift
        return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(term) + r"(?![A-Za-z0-9-])")
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"s?(?![A-Za-z0-9])", re.I)


def _section_keywords(text):
    """Keywords from any explicit keyword-style section (old prep-written postings, one board's
    '## Required Skills'). Postings written by `jobkit meta` have none: the scan covers those."""
    out, seen = [], set()
    for m in KEYWORD_HEAD.finditer(text):
        for k in re.split(r"[·•,;|\n]", m.group(2)):
            k = k.strip(" .*`-\t")
            if 1 < len(k) < 40 and k.lower() not in seen:
                seen.add(k.lower())
                out.append(k)
    return out


def _row_for(keyword, inv):
    for test in (lambda t: t.lower() == keyword.lower(),
                 lambda t: bool(_term_re(t).search(keyword)),
                 lambda t: bool(_term_re(keyword).search(t))):
        for r in inv:
            if any(test(t) for t in r["terms"]):
                return r
    return None


def _core_text(text):
    """The posting minus employer-boilerplate sections, for track counting only."""
    out, skipping = [], False
    for line in text.split("\n"):
        head = re.match(r"^\s*(?:#{1,6}\s+|\*\*)(.{2,80}?)(?:\*\*)?:?\s*$", line)
        if head:
            skipping = bool(BOILER_HEAD.search(head.group(1)))
        if not skipping:
            out.append(line)
    return "\n".join(out)


def cmd_skills(args):
    target = args.target if os.path.isabs(args.target) else os.path.join(ROOT, args.target)
    posting = os.path.join(target, "job-posting.md") if os.path.isdir(target) else target
    if not os.path.exists(posting):
        print("skills ERROR no job-posting.md at {}".format(posting))
        return 1
    inv = load_inventory()
    if not inv:
        print("skills ERROR {} is missing or has no rows".format(INVENTORY))
        return 1
    text = read(posting)
    core = _core_text(text)

    hits, banned = [], []               # (posting spellings found, row)
    for r in inv:
        found = []
        for t in r["terms"]:
            m = _term_re(t).search(text)
            if m and m.group(0).lower() not in [f.lower() for f in found]:
                found.append(m.group(0))
        if found:
            (banned if r["banned"] else hits).append((found, r))

    unknown = []
    for term in TECH_VOCAB:
        m = _term_re(term, term in CASE_SENSITIVE_VOCAB).search(text)
        if m and _row_for(term, inv) is None and term.lower() not in [u.lower() for u in unknown]:
            unknown.append(term)

    # The keyword set the coverage gate is scored on: any explicit section, plus what the scan
    # itself found (first spelling per row), plus unknown technologies.
    section = _section_keywords(text)
    mapped, keywords = {}, []
    for k, row in ([(k, _row_for(k, inv)) for k in section]
                   + [(found[0], r) for found, r in hits + banned]
                   + [(u, None) for u in unknown]):
        if k.lower() not in [x.lower() for x in keywords]:
            keywords.append(k)
            mapped[k] = row
    gaps = [k for k in section if mapped.get(k) is None and k.lower() not in [u.lower() for u in unknown]]

    print("skills {} inventory rows | {} TRUE | {} banned | {} unknown | {} GAP | {} keywords ({})".format(
        len(inv), len(hits), len(banned), len(unknown), len(gaps), len(keywords),
        "section+scan" if section else "scan only"))
    for found, r in sorted(hits, key=lambda h: (h[1]["row"], h[1]["skill"].lower())):
        never = "" if r["never"] in ("", "-") else " | never: " + r["never"]
        print("TRUE {} -> {} [{}] ({}){}".format(", ".join(found), r["wording"], r["row"], r["level"], never))
    for found, r in banned:
        print("BANNED {} -- {}".format(", ".join(found), r["evidence"]))
    for u in unknown:
        print("UNKNOWN {} -- no inventory row: treat as a gap, keep it off the page, report it under pool gaps".format(u))
    for k in gaps:
        print("GAP {}".format(k))

    # Which track base to start from (tailoring.md 3-0b). Counted, not guessed.
    counts = {t: 0 for t in TRACK_PRIORITY}
    for found, r in hits:
        track = TRACK_OF_ROW.get(r["row"].strip().lower())
        if track and any(_term_re(f).search(core) for f in found):     # boilerplate-only hits do not count
            counts[track] += 1
    role = _field(text, "Role") or (re.search(r"^# (.+)$", text, re.M) or [None, ""])[1]
    title_tracks = [t for t in TRACK_PRIORITY if TITLE_RX[t].search(role)]
    weight = {t: counts[t] + (TITLE_WEIGHT if t in title_tracks else 0) for t in TRACK_PRIORITY}
    if title_tracks:
        first = title_tracks[0]
    else:                                   # no track word in the title: needs 2+ hits, ties go to software
        order = ["software", "ai", "security"]
        best = max(order, key=lambda t: (counts[t], -order.index(t)))
        first = best if counts[best] >= 2 else "software"
    others = [t for t in ["software", "ai", "security"] if t != first]
    second = max(others, key=lambda t: (weight[t], -others.index(t)))
    # ONE hybrid rule (tailoring.md 3-0b states the same): the title names two tracks, or the
    # runner-up has 2+ hits and at least half the winner's weight.
    hybrid = len(title_tracks) >= 2 and second in title_tracks or (
        counts[second] >= 2 and weight[second] * 2 >= weight[first])
    print("TRACK security={security} software={software} ai={ai} -> base: {base}{hyb}".format(
        base=first, hyb=" HYBRID: {}+{}".format(first, second) if hybrid else "", **counts))

    if args.pdf:
        if len(keywords) < 3:
            print("NO_KEYWORDS posting too thin to score ({} keyword(s) found) -- the coverage gate gave no "
                  "evidence; say so in the match report".format(len(keywords)))
            return 0
        page = " ".join(pdf_text(args.pdf).split())
        def _wording_on_page(row):
            w = " ".join(detex(row["wording"]).split())
            return bool(w) and " ".join(w.split()).lower() in page.lower()

        def _on_page(k):
            if _term_re(k).search(page):
                return True
            row = mapped.get(k)
            if not row:
                return False
            # the row's own page wording counts ("embeddings and semantic search" covers RAG,
            # which its never-list keeps off the page), as does an inventory term inside a
            # free-form section phrase ("Basics C++" -> "C++")
            return _wording_on_page(row) or any(
                _term_re(t).search(k) and _term_re(t).search(page) for t in row["terms"])
        on_page = [k for k in keywords if _on_page(k)]
        missing = [k for k in keywords
                   if k not in on_page and mapped[k] is not None and not mapped[k]["banned"]]
        soft = [k for k in on_page if mapped.get(k) and not mapped[k]["banned"] and not _term_re(k).search(page)
                and not _term_re(k).search(mapped[k]["never"] or "")]
        print("Keyword coverage: {}/{} ({}%) | true-but-missing: {}{}".format(
            len(on_page), len(keywords), round(100.0 * len(on_page) / len(keywords)), len(missing),
            " | THIN: only {} keywords found, read the requirements by hand".format(len(keywords))
            if len(keywords) < 6 else ""))
        for k in missing:
            print("  MISSING {} -> {}   (neither the posting spelling nor the page wording is on the page)".format(k, mapped[k]["wording"]))
        for k in soft:
            print("  COVERED-BY-WORDING {} -> {}   (page wording present; add \"({})\" beside it if the posting's spelling matters to the ATS)".format(k, mapped[k]["wording"], k))
    return 0


# ------------------------------------------------------------------------ base
# Track base resumes (added 2026-09-19). Tailoring every posting from the raw
# pool meant Opus re-wrote a ~5k-token .tex per application. A base is a full,
# already-audited one-page resume for a track; prep copies it and EDITS only the
# summary, the skills-row order, the routed bullets and any entry swap.
BASES = os.path.join(ROOT, "bases")
TRACKS = ("security", "software", "ai")


def _base_paths(track):
    return os.path.join(BASES, track + ".tex"), os.path.join(BASES, track + ".source.txt")


def cmd_base(args):
    import shutil
    if args.what == "list":
        for t in TRACKS:
            tex, src = _base_paths(t)
            if not os.path.exists(tex):
                print("{:<9} MISSING".format(t))
                continue
            stale = os.path.getmtime(tex) < os.path.getmtime(POOL)
            print("{:<9} {} | from {}".format(
                t, "STALE (pool edited since)" if stale else "ok",
                read(src).strip() if os.path.exists(src) else "?"))
        return 0
    if args.track not in TRACKS:
        print("ERROR track must be one of: " + " | ".join(TRACKS))
        return 1
    tex, src = _base_paths(args.track)
    folder = args.folder if os.path.isabs(args.folder) else os.path.join(ROOT, args.folder)
    if args.what == "set":
        seed = os.path.join(folder, RESUME_TEX)
        if not os.path.exists(seed):
            print("ERROR no {} in {}".format(RESUME_TEX, folder))
            return 1
        if os.path.getmtime(seed) < os.path.getmtime(POOL):
            print("ERROR that resume predates the last content-pool.tex edit -- pick a newer one")
            return 1
        os.makedirs(BASES, exist_ok=True)
        shutil.copyfile(seed, tex)
        with io.open(src, "w", encoding="utf-8") as fh:
            fh.write("{} (set {})".format(os.path.basename(os.path.normpath(folder)),
                                          datetime.date.today().isoformat()))
        print("base {} <- {}".format(args.track, seed))
        return 0
    # use
    if not os.path.exists(tex):
        print("NO_BASE no base for track '{}' -- tailor from `jobkit pool tex`".format(args.track))
        return 3
    if os.path.getmtime(tex) < os.path.getmtime(POOL):
        print("BASE_STALE content-pool.tex was edited after this base was set -- tailor from "
              "`jobkit pool tex` and say in your return that the {} base needs re-setting".format(args.track))
        return 3
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, RESUME_TEX)
    shutil.copyfile(tex, dest)
    shutil.copyfile(os.path.join(ROOT, "master", "resume.cls"), os.path.join(folder, "resume.cls"))
    print("BASE {} -> {} (resume.cls copied). Read it, then Edit -- do not rewrite it whole."
          .format(args.track, dest))
    return 0


# ------------------------------------------------------------------------ fail
# The skill's own bug tracker. Anything that went wrong in a way the SKILL should
# have prevented gets one entry here, written by whichever phase hit it. The file
# is never read during a run -- only `/apply-job fixes` reads it, to turn entries
# into edits of the skill. Written by script so the format stays greppable.
FAILURES = os.path.join(ROOT, "failures.md")
FAIL_HEADER = ("# apply-job failure log\n\n"
               "Written only by `jobkit fail add`; reviewed by `/apply-job fixes`. One entry per\n"
               "thing the skill should have prevented. Never loaded during a normal run.\n")
FAIL_PHASES = ("gate", "prep", "fill", "sweep", "scan", "inbox", "script", "instructions")
FAIL_HEAD_RE = re.compile(r"^## (F-\d{4}) · (\S+) · (\S+) · (.*?) · (open|fixed|wontfix)\s*$", re.M)


def _one_line(s):
    return re.sub(r"\s+", " ", s or "").strip()


def cmd_fail(args):
    text = read(FAILURES) if os.path.exists(FAILURES) else FAIL_HEADER
    heads = list(FAIL_HEAD_RE.finditer(text))

    if args.what == "add":
        if not args.happened:
            print("ERROR --happened is required")
            return 1
        where = _one_line(args.where) or "-"
        # Same phase + same place + still open = the same failure again. Count it
        # instead of writing a second entry, so a flaky widget cannot flood the log.
        for i, m in enumerate(heads):
            if (m.group(5) == "open" and m.group(3) == args.phase
                    and m.group(4).lower() == where.lower()):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
                body = text[m.end():end]
                if squash(_one_line(args.happened))[:50] in squash(body):
                    seen = re.search(r"^- Seen: (\d+)x", body, re.M)
                    n = int(seen.group(1)) + 1 if seen else 2
                    line = "- Seen: {}x, last {} ({})".format(
                        n, datetime.date.today().isoformat(), _one_line(args.folder) or "-")
                    body = (re.sub(r"^- Seen: .*$", line, body, flags=re.M) if seen
                            else body.rstrip("\n") + "\n" + line + "\n\n")
                    text = text[:m.end()] + body + text[end:]
                    with io.open(FAILURES, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(text)
                    print("fail {} seen again ({}x) -- not duplicated".format(m.group(1), n))
                    return 0
        num = max([int(m.group(1)[2:]) for m in heads] or [0]) + 1
        fid = "F-{:04d}".format(num)
        entry = ["## {} · {} · {} · {} · open".format(
            fid, datetime.date.today().isoformat(), args.phase, where)]
        for label, val in (("Posting", args.folder), ("What happened", args.happened),
                           ("Expected", args.expected), ("Workaround used", args.workaround),
                           ("Suggested skill fix", args.fix)):
            if _one_line(val):
                entry.append("- {}: {}".format(label, _one_line(val)))
        text = text.rstrip("\n") + "\n\n" + "\n".join(entry) + "\n"
        with io.open(FAILURES, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("fail {} logged".format(fid))
        return 0

    if args.what == "list":
        shown = 0
        for i, m in enumerate(heads):
            if m.group(5) != "open" and not args.all:
                continue
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            print(text[m.start():end].rstrip() + "\n")
            shown += 1
        print("{} {} entr{}".format(shown, "total" if args.all else "open", "y" if shown == 1 else "ies"))
        return 0

    # close
    m = next((m for m in heads if m.group(1) == args.id), None)
    if not m:
        print("ERROR no entry {}".format(args.id))
        return 1
    status = "wontfix" if args.wontfix else "fixed"
    head = text[m.start():m.end()]
    new_head = head[:head.rindex("·") + 2] + status
    note = "- Closed {}: {}\n".format(datetime.date.today().isoformat(),
                                      _one_line(args.note) or status)
    i = heads.index(m)
    end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
    body = text[m.end():end].rstrip("\n") + "\n" + note + ("\n" if end < len(text) else "")
    text = text[:m.start()] + new_head + body + text[end:]
    with io.open(FAILURES, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("fail {} -> {}".format(args.id, status))
    return 0
