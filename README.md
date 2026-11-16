# Proof of concept demo kit (CS 415 personal coordination system)

All screenshots here are MOCK Canvas/Outlook screens. No real, school or work data.

## One-time setup (about 10 minutes)
1. Python 3.9+ (python.org). Check: `python3 --version` (Windows: `python --version`).
2. Install Tesseract OCR (reads text from screenshots):
   - Mac:     `brew install tesseract`
   - Windows: installer from https://github.com/UB-Mannheim/tesseract/wiki  (tick "add to PATH", or set TESSERACT_CMD to tesseract.exe)
   - Linux:   `sudo apt install tesseract-ocr`
3. `pip install pillow pytesseract`
4. Unzip this folder, open a terminal inside it.

## Demos (run in this order for a recording)
python3 demo.py screenshots clean --reveal       # works on tidy screenshots, finds all 10 planted differences
python3 demo.py screenshots phone --reveal       # same on phone-quality screenshots
python3 demo.py screenshots cropped --reveal     # screenshot cut off: "CAN'T CONFIRM", not "missing"
python3 demo.py screenshots unreadable --reveal  # cannot read one screenshot: it says so instead of reporting everything lost
python3 demo.py dump                             # one messy spoken dump -> structured items with "check this" flags
python3 demo.py dump "your own sentence here"
python3 demo.py dumps                            # 25-dump test scored against hand labels
python3 demo.py dumps --stress                   # 8 harder phrasings

On Windows use `python` instead of `python3`.
