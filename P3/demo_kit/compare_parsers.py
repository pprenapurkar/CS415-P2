"""P2 parser vs P3 parser on the three dump test sets (same scorer, same labels)."""
import os, sys, json, datetime as dt, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SETS = [("original 25 dumps", ""), ("8 harder phrasings (tuned on)", "stress_"), ("20 held-out dumps", "heldout_")]
for title, pre in SETS:
    os.environ["LABELS"] = os.path.join(HERE, "data", pre + "labels.json")
    import score2; importlib.reload(score2)
    dd = json.load(open(os.path.join(HERE, "data", pre + "dumps.json")))
    print(f"--- {title} ---")
    for mod, name in (("dump_parser_p2", "P2"), ("dump_parser", "P3")):
        P = importlib.import_module(mod); P.TODAY = dt.date(2026, 11, 16)
        S = score2.score({str(d["id"]): P.parse(d["text"]) for d in dd["dumps"]})
        f = S["fields"]; dtn = f["date"][1] + f["time"][1]; dto = f["date"][0] + f["time"][0]
        print(f"  {name}: found {S['found']}/{S['req_items']} | date+time {dto}/{dtn} ({100*dto/dtn:.0f}%) | category {f['category'][0]}/{f['category'][1]} ({100*f['category'][0]/f['category'][1]:.0f}%) | spurious {len(S['spurious'])}")
