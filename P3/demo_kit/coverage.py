"""P3: coverage status. Turns the screenshot reader + comparer output into the structure a "coverage view" needs.

Per source:   Captured    read it and it looks complete
              Partial     screenshot is cut off; items below the cut-off are "can't confirm", never "missing"
              Unavailable could not read it; nothing is reported missing (we don't know)
Plus a Needs Review list (missing / changed / new / can't confirm) and a one-line headline.

  python3 coverage.py clean            human-readable
  python3 coverage.py cropped --json   the structure the prototype's coverage view would consume
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SMP = lambda f: os.path.join(HERE, "samples", f)


def coverage(set_name):
    import demo, screenshot_reader as R
    from compare import compare
    cimg, oimg, clean_up = demo.SETS[set_name]
    known = json.load(open(SMP("known_list.json")))
    c_items, cutoff = R.canvas(SMP(cimg))
    o_items = R.outlook(SMP(oimg), threshold=clean_up)

    sources, review = [], []
    for src, kind, items, kn, cut in (("Canvas", "canvas", c_items, known["canvas"], cutoff), ("Outlook", "outlook", o_items, known["outlook"], None)):
        entry = {"name": src, "expected": len(kn), "read": len(items)}
        if cut is None and len(items) < 0.5 * len(kn):
            entry.update(status="Unavailable", detail=f"Could not read this screenshot ({len(items)} of about {len(kn)} items). Nothing is reported missing.")
            sources.append(entry); continue
        rep = compare(kn, items, kind, cutoff=cut)
        if cut:
            entry.update(status="Partial", detail=f"Screenshot is cut off after {cut[0]}. {len(rep['unconfirmed'])} items below it can't be confirmed.")
        else:
            entry.update(status="Captured", detail=f"Read {len(items)} items; looks complete.")
        sources.append(entry)
        for m in rep["missing"]:     review.append({"type": "MISSING", "source": src, "title": m["title"], "why": f"Expected {m['date']} but it is not in the screenshot."})
        for c in rep["changed"]:     review.append({"type": "CHANGED", "source": src, "title": c["title"], "why": "; ".join(f"{f}: {o} -> {n}" for f, o, n in c["diffs"])})
        for e in rep["extra"]:       review.append({"type": "NEW", "source": src, "title": e["title"], "why": f"On {e['date']}, not on your list."})
        for u in rep["unconfirmed"]: review.append({"type": "CANT_CONFIRM", "source": src, "title": u["title"], "why": f"Expected {u['date']}, below the cut-off."})

    ok = [s["name"] for s in sources if s["status"] == "Captured"]
    bad = [f"{s['name']} {s['status'].lower()}" for s in sources if s["status"] != "Captured"]
    headline = (f"{', '.join(ok)} captured. " if ok else "") + (f"{'; '.join(bad)}. " if bad else "") + f"{len(review)} item(s) need review."
    return {"set": set_name, "headline": headline, "sources": sources, "needs_review": review}


if __name__ == "__main__":
    name = next((a for a in sys.argv[1:] if not a.startswith("--")), "clean")
    out = coverage(name)
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        print(f"\nCOVERAGE ({name}): {out['headline']}")
        for s in out["sources"]: print(f"  {s['name']:8s} {s['status']:12s} {s['detail']}")
        for r in out["needs_review"]: print(f"    [{r['type']:12s}] {r['source']:8s} {r['title']}: {r['why']}")
        print()
