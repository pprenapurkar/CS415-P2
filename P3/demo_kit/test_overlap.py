"""P3: two screenshots of the same calendar -> does the second upload create duplicates?
(The issue friends raised: uploading several overlapping screenshots adds the same task twice.)
Screenshot A's items become the existing list; screenshot B's items are checked against it."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import screenshot_reader as R, dedupe
S = lambda f: os.path.join(HERE, "samples", f)

def items(img):
    return R.canvas(S(img))[0]

def run(label, a, b, expect_dup, expect_new):
    ex = [{"id": f"a{i}", "title": x["title"], "date": x["date"], "time": x["time"], "course": None, "source": "earlier upload"} for i, x in enumerate(a)]
    out = {"DUPLICATE": 0, "UPDATE": 0, "NEW": 0}
    for x in b: out[dedupe.check(x, ex)["verdict"]] += 1
    ok = out["DUPLICATE"] == expect_dup and out["NEW"] == expect_new and out["UPDATE"] == 0
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {out}  (expected {expect_dup} duplicate, {expect_new} new)")
    return ok

if __name__ == "__main__":
    full, part, phone = items("canvas_full.png"), items("canvas_partial.png"), items("phone_canvas_full.jpg")
    r = [run("partial screenshot, then full screenshot (6 overlap)", part, full, 6, 5),
         run("full screenshot, then partial screenshot", full, part, 6, 0),
         run("clean screenshot, then phone-quality screenshot of the same screen", full, phone, 11, 0),
         run("same screenshot uploaded twice", full, full, 11, 0)]
    print(f"{sum(r)}/{len(r)} scenarios passed")
