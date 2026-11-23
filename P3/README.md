# Proof of concept demo kit (CS 415 personal coordination system)


## One-time setup (about 10 minutes)
1. Python 3.9+ (python.org). Check: `python3 --version` (Windows: `python --version`).
2. Install Tesseract OCR (reads text from screenshots):
   - Mac:     `brew install tesseract`
   - Windows: installer from https://github.com/UB-Mannheim/tesseract/wiki  (tick "add to PATH", or set TESSERACT_CMD to tesseract.exe)
   - Linux:   `sudo apt install tesseract-ocr`
3. `pip install pillow pytesseract`
4. Unzip this folder, open a terminal inside it.

## Demos 
python3 demo.py screenshots clean --reveal       # works on tidy screenshots, finds all 10 planted differences

python3 demo.py screenshots phone --reveal       # same on phone-quality screenshots

python3 demo.py screenshots cropped --reveal     # screenshot cut off: "CAN'T CONFIRM", not "missing"

python3 demo.py screenshots unreadable --reveal  # cannot read one screenshot: it says so instead of reporting everything lost

python3 demo.py dump                             # one messy spoken dump -> structured items with "check this" flags

python3 demo.py dump "your own sentence here"

python3 demo.py dumps                            # 25-dump test scored against hand labels

python3 demo.py dumps --stress                   # 8 harder phrasings


On Windows use `python` instead of `python3`.

## P3 additions (see RESULTS_P3.md)
python3 demo.py dump                              # now also shows DUPLICATE / UPDATE / NEW vs your list + a category reason
python3 demo.py check "Quiz 5" 2026-11-19 09:00   # duplicate / update / new for one item
python3 demo.py dupes                             # 40 dev cases + 16 blind cases for duplicate detection
python3 demo.py coverage cropped [--json]         # per-source Captured / Partial / Unavailable + Needs Review
python3 demo.py dumps --heldout                   # 20 held-out dumps
(dump_parser_p2.py is the untouched P2 parser, kept for comparison.)
python3 test_overlap.py                           # overlapping / repeated screenshots: duplicates?
python3 compare_parsers.py                       # P2 parser vs P3 parser on all three dump sets
