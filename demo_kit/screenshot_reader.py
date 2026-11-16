"""Screenshot reader: tesseract OCR + pattern matching. No language model."""
import sys, re, json, datetime as dt
import os
import pytesseract
if os.environ.get("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]   # Windows: path to tesseract.exe if not on PATH
from PIL import Image

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

def to24(h, m, ap):
    h = int(h) % 12
    if ap.lower().startswith("p"): h += 12
    return f"{h:02d}:{int(m):02d}"

def canvas(path):
    im = Image.open(path).convert("L")
    # partial screenshot if dark content touches the bottom edge
    strip = im.crop((0, im.height - int(12 * im.width / 560), im.width, im.height))
    partial = strip.getextrema()[0] < 200
    text = pytesseract.image_to_string(im, config="--psm 6")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items = []
    due_re = re.compile(r"Due\s+([A-Za-z]{3})\w*\s+(\d{1,2})\s+at\s+(\d{1,2}):(\d{2})\s*([ap]m)", re.I)
    for i, l in enumerate(lines):
        m = due_re.search(l)
        if not m: continue
        j = i - 1
        while j >= 0 and ("pts" in lines[j] or due_re.search(lines[j])): j -= 1
        if j < 0: continue
        mon = MONTHS.get(m.group(1).lower()[:3])
        if not mon: continue
        title = re.sub(r"^[A-Za-z0-9]\s+(?=[A-Z])", "", lines[j])   # drop the status-circle icon OCR reads as a stray letter
        items.append({"title": title, "date": str(dt.date(2026, mon, int(m.group(2)))),
                      "time": to24(m.group(3), m.group(4), m.group(5))})
    cutoff = None
    if partial and items:
        last = items[-1]
        cutoff = [last["date"], last["time"]]
    return items, cutoff

def outlook(path, threshold=True):
    im = Image.open(path).convert("RGB")
    if threshold and im.width < 2000:
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)   # upscale phone-size screenshots
    sc0 = im.width / 1240.0
    if threshold:
        im = im.convert("L").point(lambda p: 255 if p > 170 else 0)   # black/white so dark text on light-blue blocks is readable
    d = pytesseract.image_to_data(im, config="--psm 11", output_type=pytesseract.Output.DICT)
    sc = sc0  # normalise to css pixels
    words = [(d["left"][i] / sc, (d["top"][i] + d["height"][i] / 2) / sc, d["width"][i] / sc, d["height"][i] / sc, d["text"][i])
             for i in range(len(d["text"])) if d["text"][i].strip() and int(float(d["conf"][i])) > 0]
    # group words into lines: cluster by row (y), then split each row on large x gaps
    rows = []
    for w in sorted(words, key=lambda w: w[1]):
        for R in rows:
            if abs(R["y"] - w[1]) < 6:
                R["w"].append(w); break
        else:
            rows.append({"y": w[1], "w": [w]})
    lines = []
    for R in rows:
        seg = None
        for w in sorted(R["w"], key=lambda w: w[0]):
            if seg and w[0] - seg["x2"] < 25:
                seg["t"] += " " + w[4]; seg["x2"] = w[0] + w[2]
            else:
                seg = {"x": w[0], "y": R["y"], "x2": w[0] + w[2], "t": w[4]}
                lines.append(seg)
    hdrs = []
    for L in lines:
        m = re.match(r"(Mon|Tue|Wed|Thu|Fri)\w*\s*(\d{1,2})", L["t"])
        if m and L["y"] < 85:
            hdrs.append((L["x"], dt.date(2026, 11, int(m.group(2)))))
    t_re = re.compile(r"(\d{1,2}):(\d{2})\s*([AP]M)\s*[-–—]\s*(\d{1,2}):(\d{2})\s*([AP]M)", re.I)
    ev = []
    for L in lines:
        m = t_re.search(L["t"])
        if not m or L["y"] < 85: continue
        cands = [T for T in lines if 0 < L["y"] - T["y"] < 45 and abs(T["x"] - L["x"]) < 30 and not t_re.search(T["t"])]
        if not cands or not hdrs: continue
        # v2: a title can wrap onto two lines; take every text line above the time line inside this block
        blk = [T for T in lines if 0 < L["y"] - T["y"] < 45 and abs(T["x"] - L["x"]) < 30 and not t_re.search(T["t"])]
        title = " ".join(T["t"] for T in sorted(blk, key=lambda T: T["y"]))
        day = min(hdrs, key=lambda h: abs(h[0] - L["x"]))[1]
        ev.append({"title": title, "date": str(day),
                   "start": to24(m.group(1), m.group(2), m.group(3)), "end": to24(m.group(4), m.group(5), m.group(6))})
    return ev

if __name__ == "__main__":
    c, cutoff = canvas(sys.argv[1])
    o = outlook(sys.argv[2])
    json.dump({"canvas": c, "canvas_cutoff": cutoff, "outlook": o}, open(sys.argv[3], "w"), indent=1)
    print("canvas items", len(c), "cutoff", cutoff, "| outlook events", len(o))
