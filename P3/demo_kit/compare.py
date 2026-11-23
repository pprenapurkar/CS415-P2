"""Shared compare step: known list vs extracted items -> missing / changed / extra / unconfirmed.
Both the rule-based and the Claude run feed their extraction into this same function.
"""
import json, difflib, re

def norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
def ratio(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()

def compare(known, extracted, kind, cutoff=None, thresh=0.7, seen_undated=()):
    """kind: 'canvas' or 'outlook'. cutoff: (date,time) of last visible item when screenshot is partial."""
    pairs = []
    for ki, k in enumerate(known):
        for ei, e in enumerate(extracted):
            r = ratio(k["title"], e["title"])
            if r < thresh: continue
            same_date = k["date"] == e["date"]
            same_time = (k["time"] == e["time"]) if kind == "canvas" else (k["start"] == e["start"])
            pairs.append((r * 10 + same_date * 2 + same_time, ki, ei))
    pairs.sort(reverse=True)
    used_k, used_e, match = set(), set(), {}
    for _, ki, ei in pairs:
        if ki in used_k or ei in used_e: continue
        used_k.add(ki); used_e.add(ei); match[ki] = ei
    rep = {"missing": [], "changed": [], "extra": [], "unconfirmed": []}
    for ki, k in enumerate(known):
        if ki in match:
            e = extracted[match[ki]]
            diffs = []
            if k["date"] != e["date"]: diffs.append(("date", k["date"], e["date"]))
            if kind == "canvas":
                if k["time"] != e["time"]: diffs.append(("time", k["time"], e["time"]))
            else:
                if k["start"] != e["start"] or k["end"] != e["end"]:
                    diffs.append(("time", f'{k["start"]}-{k["end"]}', f'{e["start"]}-{e["end"]}'))
            if diffs:
                rep["changed"].append({"title": k["title"], "diffs": diffs})
        else:
            beyond = (cutoff and (k["date"], k.get("time", k.get("start"))) > tuple(cutoff)) or \
                     any(ratio(k["title"], t) >= thresh for t in seen_undated)
            (rep["unconfirmed"] if beyond else rep["missing"]).append({"title": k["title"], "date": k["date"]})
    for ei, e in enumerate(extracted):
        if ei not in used_e:
            rep["extra"].append({"title": e["title"], "date": e["date"]})
    return rep

if __name__ == "__main__":
    import sys
    known = json.load(open("known_list.json"))
    ext = json.load(open(sys.argv[1]))
    out = {}
    out["canvas"] = compare(known["canvas"], ext["canvas"], "canvas", ext.get("canvas_cutoff"), seen_undated=ext.get("canvas_seen_undated", ()))
    out["outlook"] = compare(known["outlook"], ext["outlook"], "outlook")
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    for src in out:
        for k, v in out[src].items():
            print(src, k, len(v))
