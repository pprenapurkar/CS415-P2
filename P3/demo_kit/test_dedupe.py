"""Score duplicate / changed-commitment detection on data/dedupe_cases.json (40 cases vs the 24-item known list)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dedupe

FILE = sys.argv[1] if len(sys.argv) > 1 else "dedupe_cases.json"

def run(verbose=True):
    known = dedupe.flatten(json.load(open(os.path.join(HERE, "samples", "known_list.json"))))
    cases = json.load(open(os.path.join(HERE, "data", FILE)))["cases"]
    systems = {
        "P2 (no duplicate check)": lambda c: "NEW",
        "naive title similarity (P2 matcher)": lambda c: dedupe.naive_check(c, known),
        "P3 dedupe.py": lambda c: dedupe.check(c, known)["verdict"],
    }
    res = {}
    for name, fn in systems.items():
        ok = hard_ok = 0; wrong = []
        by = {k: [0, 0] for k in ("DUPLICATE", "UPDATE", "NEW")}
        for c in cases:
            got = fn(c); by[c["expected"]][1] += 1
            if got == c["expected"]:
                ok += 1; by[c["expected"]][0] += 1; hard_ok += c["hard"]
            else:
                wrong.append((c["title"], c["date"], c["expected"], got))
        res[name] = dict(ok=ok, n=len(cases), hard_ok=hard_ok, hard_n=sum(c["hard"] for c in cases), by=by, wrong=wrong)
    if verbose:
        for name, r in res.items():
            b = r["by"]
            print(f"{name}: {r['ok']}/{r['n']} correct ({100*r['ok']/r['n']:.0f}%) | hard cases {r['hard_ok']}/{r['hard_n']} | "
                  f"duplicates {b['DUPLICATE'][0]}/{b['DUPLICATE'][1]} | updates {b['UPDATE'][0]}/{b['UPDATE'][1]} | new {b['NEW'][0]}/{b['NEW'][1]}")
            if name.startswith("P3") or "naive" in name:
                for w in r["wrong"]: print("    wrong:", w)
    return res

if __name__ == "__main__":
    run()
