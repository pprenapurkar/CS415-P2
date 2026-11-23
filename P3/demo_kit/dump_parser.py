"""Rule-based dump parser: regex + keyword lists. No language model.
P3: adds spoken clock phrases (half past / quarter to), "a week from <day>", holidays, "end of the month",
"pushed to", "it's the <title>" clauses, and a category_reason on every item.
Usage: python3 dump_parser.py dumps.json out.json
Output: {"<id>": [{"title","date","time","category","unsure":[...]}]}
"""
import re, sys, json, datetime as dt

TODAY = dt.date(2026, 11, 16)  # Monday
WD = {d: i for i, d in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])}
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                         "september", "october", "november", "december"])}
NUMW = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
ORD = {}
_ones = "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth".split()
for i, w in enumerate(_ones): ORD[w] = i + 1
ORD["twentieth"] = 20; ORD["thirtieth"] = 30
for i, w in enumerate(_ones[:9]): ORD["twenty-" + w] = 21 + i
ORD["thirty-first"] = 31
NUMRE = "|".join(sorted(NUMW, key=len, reverse=True))
HOLIDAYS = {"christmas eve": (2026, 12, 24), "christmas": (2026, 12, 25), "thanksgiving": (2026, 11, 26),
            "new year's eve": (2026, 12, 31), "new year's day": (2027, 1, 1)}
MOVEWORDS = ("moved", "pushed", "rescheduled", "bumped")

CATS = {
    "Work": ["work", "invoice", "manager", "standup", "sprint", "ga ", "office hours", "retro", "team", "budget", "design review", "report", "1:1"],
    "School": ["hci", "hw", "quiz", "homework", "lab ", "reading", "professor", "prof ", "class", "study group", "itm", "proposal",
               "milestone", "slides", "peer review", "write-up", "extension", "advisor", "capstone"],
    "Projects": ["ugc", "wireframe", "figma", "project sync", "checkout"],
    "Personal": ["dentist", "doctor", "rent", "mom", "dinner", "groceries", "appointment", "car ", "drinks", "lunch", "personal", "call "],
}
STOP = set("""i my have has had need needs to a an the is are was due on at by for and also oh then so um okay alright brain dump don't
forget really that's too same time think maybe it's thirty points got moved from with in of before after afterwards one am pm
half past quarter first thing eod pushed i'm i've i'd i'll gotta like""".split())
DATEWORDS = set(list(WD) + list(MONTHS) + ["tomorrow", "today", "tonight", "next", "week", "weeks", "morning", "afternoon", "evening", "sometime"])
CUE = re.compile(r"\b(need to|have to|gotta|got to|get the|submit|email|call|pay|buy|finish|send|bring|keep the|pick up)\b")


def nextwd(wd, plus=0):
    d = (wd - TODAY.weekday()) % 7
    if d == 0: d = 7
    return TODAY + dt.timedelta(days=d + plus)


def parse_date(s):
    """-> (date|None, unsure, found)"""
    s = s.lower()
    for name in sorted(HOLIDAYS, key=len, reverse=True):
        if name in s: return dt.date(*HOLIDAYS[name]), False, True
    if re.search(r"\bend of (the|this) month\b", s):
        nxt = dt.date(TODAY.year + (TODAY.month == 12), TODAY.month % 12 + 1, 1)
        return nxt - dt.timedelta(days=1), True, True      # "end of the month" is vague: flag the date
    if "day after tomorrow" in s: return TODAY + dt.timedelta(days=2), False, True
    if "tomorrow" in s: return TODAY + dt.timedelta(days=1), False, True
    if re.search(r"\b(today|tonight|this morning|this evening)\b", s): return TODAY, False, True
    m = re.search(r"\bin (\d+|%s) (week|weeks|day|days)\b" % NUMRE, s)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else NUMW[m.group(1)]
        return TODAY + dt.timedelta(days=n * (7 if m.group(2).startswith("week") else 1)), False, True
    m = re.search(r"\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?\b" % "|".join(MONTHS), s)
    if m: return dt.date(2026, MONTHS[m.group(1)], int(m.group(2))), False, True
    m = re.search(r"\bthe (\d{1,2})(?:st|nd|rd|th)\b", s)
    day = int(m.group(1)) if m else None
    if day is None:
        m = re.search(r"\bthe (%s)\b" % "|".join(sorted(ORD, key=len, reverse=True)), s)
        if m: day = ORD[m.group(1)]
    if day:
        mon = TODAY.month if day >= TODAY.day else TODAY.month + 1
        return dt.date(2026, mon, day), False, True
    m = re.search(r"\b(?:a|one) week from (%s)\b" % "|".join(WD), s)
    if m: return nextwd(WD[m.group(1)], 7), False, True
    m = re.search(r"\bnext (%s)\b" % "|".join(WD), s)
    if m: return nextwd(WD[m.group(1)], 7), True, True
    m = re.search(r"\b(%s)\b" % "|".join(WD), s)
    if m: return nextwd(WD[m.group(1)]), False, True
    if re.search(r"\b(next week|sometime|this weekend|next month)\b", s): return None, True, True
    return None, False, False


def infer_pm(h, s, explicit=None):
    if explicit:
        return (h % 12) + (12 if explicit.startswith("p") or "evening" in explicit or "afternoon" in explicit else 0)
    if re.search(r"\b(morning)\b", s): return h % 12
    if re.search(r"\b(evening|afternoon|tonight)\b", s) and h < 12: return h + 12
    if 1 <= h <= 7: return h + 12
    return h


def parse_time(s, bare=False):
    s = s.lower()
    if re.search(r"\bnoon\b", s): return "12:00"
    m = re.search(r"\b(half past|quarter past|quarter to)\s+(\d{1,2}|%s)\b" % NUMRE, s)
    if m:
        h = int(m.group(2)) if m.group(2).isdigit() else NUMW[m.group(2)]
        if m.group(1) == "quarter to": h, mn = (h - 1) or 12, 45
        else: mn = 30 if m.group(1) == "half past" else 15
        return f"{infer_pm(h, s):02d}:{mn:02d}"
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?", s)
    if m: return f"{infer_pm(int(m.group(1)), s, m.group(3)):02d}:{m.group(2)}"
    pre = r"(?:at|around|about|maybe|think|by|before)\s+" if not bare else r"(?:at|around|about|maybe|think|by|before|to)?\s*"
    m = re.search(r"\b%s(\d{1,2}|%s)(?:-ish)?(?:\s+(thirty|fifteen|forty-five))?\s*(am|pm|in the morning|in the evening|in the afternoon)?(?![\d:])" % (pre, NUMRE), s)
    if m:
        h = int(m.group(1)) if m.group(1).isdigit() else NUMW[m.group(1)]
        if 1 <= h <= 12:
            mn = {"thirty": 30, "fifteen": 15, "forty-five": 45}.get(m.group(2), 0)
            return f"{infer_pm(h, s, m.group(3)):02d}:{mn:02d}"
    m = re.search(r"\b(\d{1,2}|%s)(?:-ish)?\s*(am|pm)\b" % NUMRE, s)
    if m:
        h = int(m.group(1)) if m.group(1).isdigit() else NUMW[m.group(1)]
        return f"{infer_pm(h, s, m.group(2)):02d}:00"
    return None


def split_clauses(sent):
    parts = re.split(r"\s*[,;]\s*|\s+(?:and then|and also|oh and|and|also|then)\s+", sent.strip().rstrip(".?!"))
    parts = [p.strip() for p in parts if p and p.strip()]
    out, pending = [], None
    for p in parts:
        p = re.sub(r"^(?:and then|and also|oh and|oh|and|also|then|but)\s+", "", p, flags=re.I)
        toks = [re.sub(r"-ish$", "", t) for t in re.findall(r"[a-z0-9:'-]+", p.lower())]
        left = [t for t in toks if t not in STOP and t not in DATEWORDS and t not in NUMW and not re.fullmatch(r"[\d:]+(?:st|nd|rd|th)?", t)]
        if not left and out:
            out[-1] += " " + p   # orphan fragment -> belongs to the previous clause
        elif not left:
            pending = p          # leading "Half past nine tomorrow," -> belongs to the NEXT clause
        else:
            out.append((pending + " " + p) if pending else p); pending = None
    if pending: out.append(pending)
    return out


def title_of(c):
    t = c.lower()
    t = re.sub(r"\b(half past|quarter past|quarter to)\s+(\d{1,2}|%s)\b" % NUMRE, " ", t)
    t = re.sub(r"\b(a|one) week from\b|\bend of (the|this) month\b|\bfirst thing\b|\bbefore\s+(\d{1,2}|%s)\b|\bbefore\b|\beod\b" % NUMRE + r"", " ", t)
    t = re.sub(r"\b(\d{1,2}:\d{2}\s*(am|pm)?|(at|around|about|maybe)\s+(\d{1,2}|%s)(?![:\d])(\s+thirty)?(\s*(am|pm|in the morning))?)\b" % NUMRE, " ", t)
    t = re.sub(r"\b(%s|tomorrow|today|tonight|next|morning|afternoon|evening|sometime|week|weeks)\b" % "|".join(list(WD) + list(MONTHS)), " ", t)
    t = re.sub(r"\bthe (\d{1,2}(st|nd|rd|th)|%s)\b" % "|".join(ORD), " ", t)
    words = [w for w in re.findall(r"[a-z0-9:'-]+", t) if w not in STOP]
    return " ".join(words) or c


def category(c):
    low = " " + c.lower() + " "
    hits, why = [], {}
    for k, kws in CATS.items():
        for w in kws:
            if re.search(r"(?<![a-z0-9])" + re.escape(w.strip()) + r"(?![a-z0-9])", low):
                hits.append(k); why[k] = w.strip(); break
    if len(hits) == 1: return hits[0], False, f"matched '{why[hits[0]]}'"
    if len(hits) > 1: return hits[0], True, "matched " + " and ".join(f"'{why[h]}' ({h})" for h in hits) + ", so please pick one"
    return None, True, "no known keyword"


def parse(text):
    items = []
    for sent in re.split(r"(?<=[.?!])\s+", text.strip()):
        corr = None
        m = re.search(r",?\s*\b(?:wait no|no wait)\b,?\s*", sent, re.I)
        if m: sent, corr = sent[:m.start()], sent[m.end():]
        prev = None
        for c in split_clauses(sent):
            low = c.lower()
            if re.search(r"\b(cancel|anymore|not doing)\b", low): continue
            mt = re.match(r"(?:it's|its|it is|that's|that is)\s+(?:the\s+)?(.+)", low)
            if mt and items and items[-1].get("moved"):
                cat, cu, cr = category(mt.group(1)); items[-1].update(title=title_of(mt.group(1)), category=cat, category_reason=cr, moved=False)
                items[-1]["unsure"] = [u for u in items[-1]["unsure"] if u != "category"] + (["category"] if cu else [])
                continue
            src = low
            moved = any(w in low for w in MOVEWORDS)
            if moved: src = low.split(" to ")[-1]
            d, dunsure, dfound = parse_date(src)
            if moved and not dfound:
                d, dunsure, dfound = parse_date(low.split(" to ")[0])
            t = parse_time(src, bare=moved)
            if "same time" in low and (prev or items): t = (prev or items[-1])["time"]
            if not (dfound or t or CUE.search(low)): continue
            unsure = []
            if d is None and t and prev and prev["date"]:
                d = dt.date.fromisoformat(prev["date"]); unsure.append("date")
            if dunsure and "date" not in unsure: unsure.append("date")
            if t and re.search(r"\b(i think|maybe|-ish|\?)", low) and not moved: unsure.append("time")
            cat, cunsure, creason = category(c)
            if cunsure: unsure.append("category")
            it = {"title": title_of(c), "date": d.isoformat() if d else None, "time": t, "category": cat, "category_reason": creason, "unsure": unsure}
            if moved: it["moved"] = True
            items.append(it); prev = it
        if corr and items:
            d2, _, f2 = parse_date(corr); t2 = parse_time(corr, bare=True)
            if f2 and d2: items[-1]["date"] = d2.isoformat()
            if t2: items[-1]["time"] = t2
    for it in items: it.pop("moved", None)
    return items


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    out = {str(d["id"]): parse(d["text"]) for d in data["dumps"]}
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    print("parsed", sum(len(v) for v in out.values()), "items from", len(out), "dumps")
