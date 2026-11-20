# 📑 Tender PDF Splitter

Bidder ek hi PDF me 10–25 documents (GST, PAN, Incorporation, Turnover, Past Experience …) merge karke
submit kar dete hain — 400–500 pages tak. Ye app us merged PDF ko analyse karke **har document ko
uske title ke naam se alag PDF** me tod deti hai.

**Features**

- Document boundaries automatic detect: PDF bookmarks → heading/title match → divider pages
  (“Annexure-3”) → page-size change / “Page 1 of N”
- **Scanned (image) pages** bhi: OCR (Tesseract, English + Hindi)
- **Review table**: title rename, galat split hatana (merge), naya split jodna, document skip (Include off)
- **Page check**: kisi bhi page ke aas-paas ke pages dekh kar boundary verify
- Output: har document ki alag PDF — **Download**, **View** (page preview + full viewer), **Print**
- **ZIP** of all PDFs + **Excel index** (title, pages, start/end, size, confidence)
- Ek saath **kai bidders** (har bidder ka alag folder ZIP me)
- Apne document types add kar sakte hain (sidebar ya `custom_doctypes.txt`)
- Command-line version (`cli.py`) bhi hai

---

## 🚀 Deploy: GitHub + Streamlit Community Cloud

1. **GitHub par repo banayein** (private rakhna better hai) aur ye saari files upload karein:

   ```bash
   git init
   git add .
   git commit -m "Tender PDF splitter"
   git branch -M main
   git remote add origin https://github.com/<your-username>/tender-pdf-splitter.git
   git push -u origin main
   ```

2. <https://share.streamlit.io> → **Create app** → apni repo, branch `main`,
   **Main file path = `app.py`** → *Advanced settings* me Python **3.11 ya 3.12** → **Deploy**.

   `requirements.txt` (Python libraries) aur `packages.txt` (Tesseract OCR) apne-aap install ho jate hain.

3. ⚠️ **Tender documents confidential hote hain.** App settings → *Sharing* me app ko
   **private** rakhein (sirf allowed email IDs). Kabhi bidder ki PDF GitHub par commit na karein
   (`.gitignore` me `*.pdf` already block hai, sirf `sample/` allowed hai).

### Local par chalana

```bash
pip install -r requirements.txt
# OCR ke liye Tesseract chahiye:
#   Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-hin
#   Windows: https://github.com/UB-Mannheim/tesseract/wiki  (install ke baad PATH me add karein)
#   macOS: brew install tesseract tesseract-lang
streamlit run app.py
```

Bina OCR ke bhi app chalti hai — bas scanned pages ke titles detect nahi honge
(text-based PDFs par koi farak nahi).

---

## 🧭 Use kaise karein

1. **Upload** — bidder ki merged PDF(s).
2. **Analyze** — documents dhoondhe jate hain. (Scanned PDF ho to thoda time lagta hai: ~0.3 sec/page OCR.)
3. **Review** — table me har document ka start page aur title dikhta hai.
   - Title galat → cell par double-click karke badlein
   - Galat split → row delete karein (pages pichhle document me jud jayenge)
   - Missing split → *Page check* me page number daalkar **Start new document here**, ya table me row jodein
   - Document nahi chahiye → **Include** untick karein
   - **Confidence** kam (<50%) wale rows ko dhyan se check karein
4. **Create separate PDFs** → neeche list me har PDF ka **⬇ PDF / 👁 View**, upar **ZIP** aur **Excel index**.
   - **View** → page preview, thumbnails, full PDF viewer
   - **Open in new tab** → browser ka apna PDF viewer
   - **Print** → print dialog (Chrome/Edge par seedha; agar browser block kare to *Open in new tab* → `Ctrl+P`)

## 🎯 Accuracy kaise badhayein

- **Bookmarks**: agar bidder ne Adobe/online tool se merge kiya hai to aksar har document ka bookmark hota hai —
  app wahi use karti hai (sidebar: *Use PDF bookmarks*), ye sabse accurate hai.
- **Sensitivity**: Low = sirf clear titles; High = zyada documents pakadta hai par galat split bhi ho sakte hain.
- **Custom documents**: koi document baar-baar “Unidentified Document N” aaye to uska heading-phrase add karein:

  ```
  Solvency Letter = solvency letter | bank solvency
  Site Visit Report = site visit report
  ```
  (sidebar me likhein, ya `custom_doctypes.txt` me — wo GitHub me save rahega)
- **Scanned PDFs**: OCR language `eng+hin` karein agar Hindi headings hain; watermark wali scans ke liye *When to OCR = always*.
- Built-in list: `doctypes.py` (≈40 types: GST, PAN, Incorporation, MOA/AOA, MSME/Udyam, Turnover, Balance Sheet, ITR,
  Net Worth, Solvency, EMD, Bank Guarantee, PoA, Affidavit, Non-blacklisting, EPF/ESIC, ISO, Past Experience, OEM/MAF,
  Price Bid, Technical Bid …). Isme apne hisaab se phrases badal/add kar sakte hain.

## ⚠️ Limitations (seedhi baat)

- Detection **heading/keyword + layout hints** par chalti hai, AI model par nahi. Clear titles wale documents me bahut
  accurate hai, par bina heading wale ya unusual documents “Unidentified Document N” ban sakte hain —
  isliye **review step** rakha gaya hai.
- Ek bada document (jaise 100-page signed tender document) jiske andar ke pages par dusre documents ke
  keywords heading me hon, wahan extra splits aa sakte hain — row delete karke merge karein.
- Jo documents ek jaise type ke hain aur lagatar aate hain (jaise 10 work orders) wo **ek hi document**
  (“Past Experience”) me rehte hain. Alag chahiye to table me split jodein.
- OCR header-only mode page ke upar ke ~40% hisse se title padhta hai. Tirche / ulte scanned pages par OCR kamzor hota hai.
- Password se locked (open-password) PDF open nahi hogi. Sirf edit/print-restricted PDF theek chalti hai.
- Free Streamlit Cloud par RAM limited hoti hai — bahut badi (100+ MB) scanned PDFs ek-ek karke process karein.

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q                      # engine edge cases
python tests/run_detection_test.py --huge      # ~490-page synthetic PDF vs ground truth
python tests/run_detection_test.py --huge --allscan   # saari pages scanned (OCR) - ~2.5 min
python cli.py sample/sample_merged_bidder.pdf --dry-run
```

`sample/sample_merged_bidder.pdf` ek synthetic 48-page demo PDF hai (22 documents, 3 scanned) — app try karne ke liye.

## 📁 Structure

```
app.py               Streamlit UI
splitter.py          engine: text/OCR → boundary detection → split → ZIP/Excel
doctypes.py          document types + heading phrases (edit/add here)
custom_doctypes.txt  your own types (optional)
cli.py               command-line version
requirements.txt     Python libraries        packages.txt   Tesseract OCR (Streamlit Cloud)
.streamlit/config.toml   upload limit (400 MB)
tests/  sample/
```
