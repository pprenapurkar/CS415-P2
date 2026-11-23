#!/usr/bin/env python3
"""Proof of concept demo: can the tool build a checkable picture from sources it can't connect to?

  python3 demo.py screenshots clean        read clean mock Canvas + Outlook screenshots, compare to your known list
  python3 demo.py screenshots phone        same, phone-quality (small, compressed) screenshots
  python3 demo.py screenshots cropped      Canvas screenshot cut off halfway: what can it NOT confirm?
  python3 demo.py screenshots unreadable   Outlook screenshot it cannot read: does it admit that?
  python3 demo.py dump                     turn a messy spoken/typed dump into structured items (built-in example)
  python3 demo.py dump "your own text"     same, your own text
  python3 demo.py dumps                    run the 25-dump test set and score it against hand labels
  python3 demo.py dumps --heldout          20 fresh dumps written before the P3 parser changes
  python3 demo.py coverage clean           P3: per-source status (Captured / Partial / Unavailable) + Needs Review list
  python3 demo.py dupes                    P3: duplicate / changed-commitment test (40 cases, then 16 blind cases)
  python3 demo.py check "Quiz 5" 2026-11-19 09:00   P3: is this a duplicate, an update, or new?

Add --reveal to 'screenshots' to show the planted answer key and a score.
All screenshots are MOCK screens (no real Canvas/Outlook/work data).
"""
import sys, os, json, argparse, datetime as dt, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SMP = lambda f: os.path.join(HERE, "samples", f)

SETS = {  # name: (canvas image, outlook image, use image clean-up before reading)
    "clean": ("canvas_full.png", "outlook_full.png", True),
    "phone": ("phone_canvas_full.jpg", "phone_outlook_full.jpg", True),
    "cropped": ("canvas_partial.png", "outlook_full.png", True),
    "unreadable": ("phone_canvas_full.jpg", "phone_outlook_full.jpg", False),
}
DESC = {
    "clean": "clean screenshots",
    "phone": "phone-quality screenshots (shrunk and compressed)",
    "cropped": "Canvas screenshot cut off partway down",
    "unreadable": "phone-quality screenshots read WITHOUT image clean-up (to show what happens when it can't read)",
}


def when(d, t=None):
    day = dt.date.fromisoformat(d)
    s = f"{day.strftime('%a %b')} {day.day}"
    if t:
        h, m = map(int, t.split(":")[:2])
        s += f" {(h % 12) or 12}:{m:02d}{'am' if h < 12 else 'pm'}"
    return s


def clock(t):
    h, m = map(int, t.split(":")[:2])
    return f"{(h % 12) or 12}:{m:02d}{'am' if h < 12 else 'pm'}"


def key_of(it, kind):
    return (it["date"], it["time"] if kind == "canvas" else it["start"])


def screenshots(name, reveal):
    import screenshot_reader as R
    from compare import compare, ratio
    cimg, oimg, clean_up = SETS[name]
    known = json.load(open(SMP("known_list.json")))
    print(f"\n=== Screenshot demo: {DESC[name]} ===")
    print(f"Your known list: {len(known['canvas'])} Canvas items, {len(known['outlook'])} Outlook events\n")
    c_items, cutoff = R.canvas(SMP(cimg))
    o_items = R.outlook(SMP(oimg), threshold=clean_up)

    reports, notes = {}, []
    print("COVERAGE (what this tool could actually see)")
    for src, items, kn, cut in (("Canvas", c_items, known["canvas"], cutoff), ("Outlook", o_items, known["outlook"], None)):
        if cut is None and len(items) < 0.5 * len(kn):
            print(f"  {src:8s}: COULD NOT READ this screenshot (read {len(items)} of about {len(kn)} expected items)")
            notes.append(f"{src}: not reporting anything as missing, because the screenshot could not be read. Try a larger or clearer one.")
            continue
        state = f"read {len(items)} items; screenshot is CUT OFF after {when(*cut)}" if cut else f"read {len(items)} items; looks complete"
        print(f"  {src:8s}: {state}")
        kind = "canvas" if src == "Canvas" else "outlook"
        reports[kind] = compare(kn, items, kind, cutoff=cut)

    print("\nWHAT DIFFERS FROM YOUR LIST")
    shown = 0
    for kind, label in (("canvas", "Canvas "), ("outlook", "Outlook")):
        rep = reports.get(kind)
        if not rep:
            continue
        for m in rep["missing"]:
            print(f"  [MISSING]       {label} {m['title']} (you expected {when(m['date'])}) - not in this screenshot"); shown += 1
        for c in rep["changed"]:
            bits = ", ".join(f"{f}: {when(o) if f == 'date' else o} -> {when(n) if f == 'date' else n}" for f, o, n in c["diffs"])
            print(f"  [CHANGED]       {label} {c['title']} ({bits})"); shown += 1
        for e in rep["extra"]:
            print(f"  [NEW]           {label} {e['title']} on {when(e['date'])} - not on your list"); shown += 1
        for u in rep["unconfirmed"]:
            print(f"  [CAN'T CONFIRM] {label} {u['title']} (expected {when(u['date'])}) - below the cut-off, not visible"); shown += 1
    if not shown:
        print("  nothing to report")
    for n in notes:
        print("  NOTE:", n)

    if reveal:
        key = json.load(open(SMP("answer_key.json")))
        titles = {c["id"]: c["title"] for c in known["canvas"] + known["outlook"]}
        for rows in (key["canvas_shown"], key["outlook_shown"]):
            for r in rows:
                titles[r[0]] = r[1]
        planted = [(("canvas" if "canvas" in k else "outlook"), p["type"], titles[p["id"]]) for k in ("canvas", "outlook") for p in key[k]]
        caught = hidden = 0
        for src, typ, t in planted:
            rep = reports.get(src)
            if rep is None:
                continue
            pool = {"missing": rep["missing"], "extra": rep["extra"], "changed": rep["changed"]}[typ]
            if any(ratio(t, x["title"]) >= 0.7 for x in pool):
                caught += 1
            elif any(ratio(t, x["title"]) >= 0.7 for x in rep["unconfirmed"]):
                hidden += 1
        reported = sum(len(r[k]) for r in reports.values() for k in ("missing", "changed", "extra"))
        false_alarms = reported - caught
        print(f"\nANSWER KEY: {len(planted)} differences were planted | caught {caught} | hidden by the cut-off {hidden} | false alarms {false_alarms}")
    print()


def dump(text, today):
    import dump_parser as P
    P.TODAY = dt.date.fromisoformat(today)
    print(f"\n=== Dump demo (today = {P.TODAY.strftime('%A %b')} {P.TODAY.day}, {P.TODAY.year}) ===")
    print(f'You said: "{text}"\n')
    items = P.parse(text)
    if not items:
        print("  Nothing that looks like a commitment.\n"); return
    import dedupe
    known = dedupe.flatten(json.load(open(SMP("known_list.json"))))
    print(f"{'TITLE':30s} {'DATE':12s} {'TIME':8s} {'CATEGORY':10s} {'CHECK THIS':16s} VS YOUR LIST")
    for it in items:
        d = when(it["date"]) if it["date"] else "(none)"
        t = clock(it["time"]) if it["time"] else "(none)"
        v = dedupe.check(it, known)
        print(f"{it['title'][:29]:30s} {d:12s} {t:8s} {(it['category'] or '(unsure)'):10s} {', '.join(it['unsure']) or '-':16s} {v['verdict']}")
        print(f"{'':30s} category: {it['category_reason']}")
        if v["verdict"] != "NEW" or v.get("needs_review"): print(f"{'':30s} list: {v['reason']}")
    print("\n'CHECK THIS' = the tool is unsure and wants you to confirm before saving. '(none)' = you never said, so it did not guess.")
    print("'VS YOUR LIST' = DUPLICATE (already there), UPDATE (same item, changed date/time) or NEW. The reason is shown so you can confirm.\n")


def dumps(stress, heldout=False):
    data = "heldout_" if heldout else ("stress_" if stress else "")
    os.environ["LABELS"] = os.path.join(HERE, "data", data + "labels.json")
    import score2
    importlib.reload(score2)
    import dump_parser as P
    P.TODAY = dt.date(2026, 11, 16)
    dd = json.load(open(os.path.join(HERE, "data", data + "dumps.json")))
    ext = {str(d["id"]): P.parse(d["text"]) for d in dd["dumps"]}
    print(f"\n=== Dump test: {'20 held-out dumps' if heldout else '8 harder phrasings' if stress else '25 messy dumps'} (today = Mon Nov 16, 2026) ===")
    score2.report("rule-based parser", score2.score(ext), detail=True)
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("screenshots"); s.add_argument("set", choices=list(SETS)); s.add_argument("--reveal", action="store_true")
    d = sub.add_parser("dump"); d.add_argument("text", nargs="?"); d.add_argument("--today", default="2026-11-16")
    ds = sub.add_parser("dumps"); ds.add_argument("--stress", action="store_true"); ds.add_argument("--heldout", action="store_true")
    cv = sub.add_parser("coverage"); cv.add_argument("set", choices=list(SETS)); cv.add_argument("--json", action="store_true")
    sub.add_parser("dupes")
    ck = sub.add_parser("check"); ck.add_argument("title"); ck.add_argument("date"); ck.add_argument("time", nargs="?")
    a = ap.parse_args()
    if a.cmd == "screenshots":
        try:
            screenshots(a.set, a.reveal)
        except ImportError as e:
            sys.exit(f"Missing Python package ({e}). Run:  pip install pillow pytesseract")
        except Exception as e:
            if e.__class__.__name__ == "TesseractNotFoundError":
                sys.exit("Tesseract OCR is not installed or not on PATH. Install it (see README step 2), "
                         "or set TESSERACT_CMD to the full path of tesseract.exe.")
            raise
    elif a.cmd == "dump":
        dump(a.text or "Tomorrow I have a work meeting at 10, HCI is due Friday, I need to finish my UGC wireframes tonight, and I have a personal appointment at 4.", a.today)
    elif a.cmd == "dumps": dumps(a.stress, a.heldout)
    elif a.cmd == "coverage":
        sys.argv = ["coverage.py", a.set] + (["--json"] if a.json else [])
        import runpy; runpy.run_path(os.path.join(HERE, "coverage.py"), run_name="__main__")
    elif a.cmd == "dupes":
        import test_dedupe
        for f in ("dedupe_cases.json", "dedupe_blind.json"):
            print(f"\n=== {f} ==="); test_dedupe.FILE = f; test_dedupe.run()
    elif a.cmd == "check":
        import dedupe
        print(json.dumps(dedupe.check({"title": a.title, "date": a.date, "time": a.time}, dedupe.flatten(json.load(open(SMP("known_list.json"))))), indent=1))
    else: ap.print_help()


if __name__ == "__main__":
    main()
