"""Score an extraction against labels.json.
Usage: python3 score2.py extraction.json [--detail]
Rules: date/time null in the label means 'not stated': inventing a value is wrong. alt_* values count only if that field is flagged.
"""
import json, sys

import os
labels = json.load(open(os.environ.get("LABELS", "labels.json")))["labels"]

def score(ext):
    S = dict(req_items=0, found=0, spurious=[], forbidden=[], fields={"date": [0, 0], "time": [0, 0], "category": [0, 0]},
             flags_expected=0, flags_caught=0, flags_unneeded=0, wrong=[], missed=[], unneeded=[])
    for did, lab in labels.items():
        items = list(ext.get(did, []))
        used = set()
        for f in lab.get("forbidden", []):
            for i, e in enumerate(items):
                if any(k in e["title"].lower() for k in f["kw"]) and e["date"] == f["date"]:
                    S["forbidden"].append((did, e["title"]))
                    used.add(i)
        for li in lab["items"]:
            opt = li.get("optional", False)
            cands = [i for i, e in enumerate(items) if i not in used and any(k in e["title"].lower() for k in li["kw"])]
            if cands:
                best = next((i for i in cands if items[i]["date"] == li["date"]), cands[0])
                used.add(best); e = items[best]
            else:
                e = None
            if opt:
                continue
            S["req_items"] += 1
            exp = set(li.get("unsure", []))
            if li.get("alt_cat"): exp.add("category")
            if li.get("alt_date"): exp.add("date")
            if li.get("alt_time"): exp.add("time")
            if e is None:
                S["missed"].append((did, li["kw"][0]))
                for f in S["fields"]: S["fields"][f][1] += 1
                S["flags_expected"] += len(exp)
                continue
            S["found"] += 1
            fl = set(e.get("unsure", []))
            def ok(field):
                v = e.get(field if field != "category" else "category")
                if field == "category":
                    if li["cat"] is None: return v is None or "category" in fl
                    return v == li["cat"] or (v in li.get("alt_cat", []))
                lab_v = li[field]
                if v == lab_v: return True
                return v in li.get("alt_" + field, []) and field in fl
            for f in ("date", "time", "category"):
                S["fields"][f][1] += 1
                if ok(f): S["fields"][f][0] += 1
                else: S["wrong"].append((did, li["kw"][0], f, e.get(f), li[f] if f != "category" else li["cat"]))
            for f in exp:
                S["flags_expected"] += 1
                if f in fl: S["flags_caught"] += 1
                else: S["missed"].append((did, li["kw"][0], "flag:" + f))
            for f in fl - exp:
                S["flags_unneeded"] += 1; S["unneeded"].append((did, li["kw"][0], f))
        for i, e in enumerate(items):
            if i not in used: S["spurious"].append((did, e["title"]))
    return S

def report(name, S, detail=False):
    f = S["fields"]; pct = lambda a: 100.0 * a[0] / a[1] if a[1] else float("nan")
    dt_ok = f["date"][0] + f["time"][0]; dt_n = f["date"][1] + f["time"][1]
    print(f"{name}: items found {S['found']}/{S['req_items']} | date {f['date'][0]}/{f['date'][1]} ({pct(f['date']):.0f}%) | time {f['time'][0]}/{f['time'][1]} ({pct(f['time']):.0f}%)"
          f" | date+time {dt_ok}/{dt_n} ({100*dt_ok/dt_n:.0f}%) | category {f['category'][0]}/{f['category'][1]} ({pct(f['category']):.0f}%)"
          f" | expected flags raised {S['flags_caught']}/{S['flags_expected']} | unneeded flags {S['flags_unneeded']}"
          f" | spurious items {len(S['spurious'])} | forbidden created {len(S['forbidden'])}")
    if detail:
        for k in ("missed", "wrong", "spurious", "forbidden", "unneeded"):
            for x in S[k]: print("   ", k, x)

if __name__ == "__main__":
    S = score(json.load(open(sys.argv[1])))
    report(sys.argv[1], S, "--detail" in sys.argv)
