"""P3: duplicate / changed-commitment detection. Rules only, no language model.

Given an incoming item (title, date, time) and the list the system already holds, say whether it is
  DUPLICATE  the same commitment, nothing to change
  UPDATE     the same commitment, but the date or time differs ("this looks like X, which moved")
  NEW        a different commitment, even if the title looks similar

Why not just use string similarity (what compare.py does)? "Quiz 5" vs "Quiz 7" and "Homework 6" vs
"Homework 7" are ~85% similar as strings but are different commitments, and a weekly "Team standup" a week
later is a new occurrence, not a move of the old one. So matching is number-aware, course-aware, and
date-aware. Every verdict carries a plain-English reason so the interface can show it for the user to confirm.
"""
import re, json, datetime as dt

STOP = {"with", "the", "a", "an", "of", "my", "for", "to", "and", "in", "on", "at", "our", "w"}
COURSE = re.compile(r"\b(cs|itm|ece|math|mas|bus)\s*(\d{3})\b", re.I)
UPDATE_WINDOW_DAYS = 3      # same title, date differs by <= this many days -> "moved"; further apart -> new occurrence


def _norm(title):
    t = title.lower()
    t = t.replace("1:1", " oneonone ").replace("w/", " with ").replace("stand-up", "standup").replace("write-up", "writeup")
    courses = {m.group(1) + m.group(2) for m in COURSE.finditer(t)}
    t = COURSE.sub(" ", t)
    toks = re.findall(r"[a-z0-9]+", t)
    nums = {x for x in toks if x.isdigit()}
    words = {x for x in toks if not x.isdigit() and x not in STOP}
    return words, nums, courses


def title_match(a, b, a_course=None, b_course=None):
    """-> 'strong' | 'partial' | None"""
    wa, na, ca = _norm(a); wb, nb, cb = _norm(b)
    if a_course: ca |= {re.sub(r"\s+", "", a_course.lower())}
    if b_course: cb |= {re.sub(r"\s+", "", b_course.lower())}
    if ca and cb and not (ca & cb): return None            # different courses
    if na and nb and na != nb: return None                 # Quiz 5 vs Quiz 7
    if not wa or not wb: return None
    wa, wb = wa | na, wb | nb                              # a matching number ("lab 7") is evidence too
    inter = wa & wb
    if not (inter - na - nb) : return None                 # must share at least one real word, not just a number
    jac = len(inter) / len(wa | wb)
    if jac >= 0.75: return "strong"
    if (wa <= wb or wb <= wa) and jac >= 0.4: return "partial"
    return None


def _hhmm(t): return t[:5] if t else None
def _day(s): return dt.date.fromisoformat(s)
def _nice(d, t=None):
    day = _day(d); s = f"{day.strftime('%a %b')} {day.day}"
    if t:
        h, m = map(int, t[:5].split(":")); s += f" {(h % 12) or 12}:{m:02d}{'am' if h < 12 else 'pm'}"
    return s


def flatten(known):
    """samples/known_list.json -> one uniform list of {id,title,date,time,course,source}"""
    out = []
    for it in known.get("canvas", []):
        out.append({"id": it["id"], "title": it["title"], "date": it["date"], "time": it["time"], "course": it.get("course"), "source": "Canvas"})
    for it in known.get("outlook", []):
        out.append({"id": it["id"], "title": it["title"], "date": it["date"], "time": it["start"], "course": None, "source": "Outlook"})
    return out


def check(item, existing, window=UPDATE_WINDOW_DAYS):
    """item: {title,date,time}. Returns {verdict, match, reason, changes}."""
    if not item.get("date"):
        # without a date we cannot tell a repeat from a new occurrence: surface the closest title, don't decide
        for e in existing:
            if title_match(item["title"], e["title"], None, e.get("course")):
                return {"verdict": "NEW", "match": None, "changes": [], "needs_review": True,
                        "reason": f"No date given and the title resembles '{e['title']}' ({_nice(e['date'])}). Please confirm whether it is the same item."}
        return {"verdict": "NEW", "match": None, "changes": [], "reason": "No similar item on your list."}

    best = None
    for e in existing:
        tm = title_match(item["title"], e["title"], item.get("course"), e.get("course"))
        if not tm: continue
        gap = abs((_day(item["date"]) - _day(e["date"])).days)
        same_t = _hhmm(item.get("time")) == _hhmm(e["time"]) or not item.get("time")
        rank = (tm == "strong", -gap, same_t)               # prefer the closest occurrence of a recurring item
        if best is None or rank > best[0]:
            best = (rank, e, tm, gap, same_t)
    if not best:
        return {"verdict": "NEW", "match": None, "changes": [], "reason": "No similar item on your list."}
    _, e, tm, gap, same_t = best
    changes = []
    if gap: changes.append(("date", _nice(e["date"]), _nice(item["date"])))
    if item.get("time") and not same_t: changes.append(("time", _nice(e["date"], e["time"]).split(" ", 2)[-1], _nice(item["date"], item["time"]).split(" ", 2)[-1]))
    label = f"'{e['title']}' from {e['source']}"
    if tm == "strong":
        if not changes:
            return {"verdict": "DUPLICATE", "match": e["id"], "changes": [], "reason": f"Same as {label}, {_nice(e['date'], e['time'])}."}
        if gap <= window:
            return {"verdict": "UPDATE", "match": e["id"], "changes": changes, "needs_review": True,
                    "reason": f"Looks like {label}, but " + "; ".join(f"{f} is now {n} (was {o})" for f, o, n in changes) + "."}
        return {"verdict": "NEW", "match": None, "changes": [], "reason": f"Similar to {label} but {gap} days apart, so treated as a new occurrence."}
    # partial title match: weaker evidence, so the date has to agree
    if gap == 0 and same_t:
        return {"verdict": "DUPLICATE", "match": e["id"], "changes": [], "needs_review": True,
                "reason": f"Probably {label}: part of the title matches and the date and time agree."}
    if gap == 0:
        return {"verdict": "UPDATE", "match": e["id"], "changes": changes, "needs_review": True,
                "reason": f"Probably {label}, now at a different time ({changes[0][1]} to {changes[0][2]})."}
    return {"verdict": "NEW", "match": None, "changes": [], "reason": f"Title partly resembles {label}, but the date differs, so treated as a different item."}


def naive_check(item, existing, thresh=0.7):
    """The P2-style matcher (compare.py: string similarity >= 0.7, nothing else), used as a comparison."""
    from compare import ratio
    for e in existing:
        if ratio(item["title"], e["title"]) >= thresh:
            same = item["date"] == e["date"] and _hhmm(item.get("time")) == _hhmm(e["time"])
            return "DUPLICATE" if same else "UPDATE"
    return "NEW"


if __name__ == "__main__":
    import sys
    known = flatten(json.load(open("samples/known_list.json")))
    r = check({"title": sys.argv[1], "date": sys.argv[2], "time": sys.argv[3] if len(sys.argv) > 3 else None}, known)
    print(json.dumps(r, indent=1))
