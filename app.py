"""Tender PDF Splitter - Streamlit app.

Upload the merged PDF(s) a bidder submitted  ->  the app finds every document inside
(GST, PAN, Incorporation, Turnover, Past Experience ...)  ->  you review / rename  ->
one PDF per document, with Download, View and Print.

Run locally:   streamlit run app.py
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os

import pandas as pd
import streamlit as st

import splitter as sp
from doctypes import DEFAULT_DOC_TYPES, parse_custom_doc_types

st.set_page_config(page_title="Tender PDF Splitter", page_icon="📑", layout="wide")

S = st.session_state
if "bidders" not in S:
    S.bidders = {}

MAX_EMBED_BYTES = 25 * 1024 * 1024      # Open/Print buttons embed the PDF in the page
COLS = ["Include", "Start page", "Title", "Confidence %", "Detected by", "Page text (start)"]


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def bkey(key: str) -> str:
    return hashlib.md5(key.encode()).hexdigest()[:8]


def fmt_size(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{n / 1024:.0f} KB"


@st.cache_data(show_spinner=False, max_entries=600)
def cached_images(cache_id: str, indices: tuple, scale: float, _data: bytes) -> list:
    return sp.render_pages(_data, list(indices), scale)


def embed_html(html: str, height: int) -> None:
    """st.iframe is the current API; older Streamlit versions only have components.v1.html."""
    try:
        if hasattr(st, "iframe"):
            st.iframe(html, height=height)
            return
    except Exception:
        pass
    import streamlit.components.v1 as components
    components.html(html, height=height)


def pdf_tools_html(data: bytes, filename: str) -> str:
    """'Open in new tab' and 'Print' buttons that work on the PDF bytes in the browser."""
    b64 = base64.b64encode(data).decode()
    fn = json.dumps(filename).replace("<", "\\u003c")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif}}
button{{padding:8px 14px;margin:0 8px 0 0;border:1px solid #cbd5e1;border-radius:8px;
background:#fff;color:#0f172a;cursor:pointer;font-size:14px}}
button:hover{{background:#f1f5f9}}
#msg{{font-size:12px;color:#64748b}}
</style></head><body>
<button id="open">🔍 Open in new tab</button><button id="print">🖨️ Print</button><span id="msg"></span>
<script>
(function(){{
  var name = {fn};
  var bin = atob("{b64}");
  var bytes = new Uint8Array(bin.length);
  for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  var url = URL.createObjectURL(new Blob([bytes], {{type: "application/pdf"}}));
  var msg = document.getElementById("msg");
  document.getElementById("open").onclick = function(){{
    var w = window.open(url, "_blank");
    if (!w) msg.textContent = "Pop-up blocked - allow pop-ups for this site.";
  }};
  document.getElementById("print").onclick = function(){{
    var f = document.createElement("iframe");
    f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
    f.onload = function(){{
      try {{ f.contentWindow.focus(); f.contentWindow.print(); }}
      catch (e) {{ window.open(url, "_blank"); msg.textContent = "Press Ctrl+P in the new tab."; }}
    }};
    f.src = url;
    document.body.appendChild(f);
  }};
}})();
</script></body></html>"""


# --------------------------------------------------------------------------- #
# settings (sidebar)
# --------------------------------------------------------------------------- #

def read_settings() -> dict:
    sb = st.sidebar
    sb.header("⚙️ Settings")

    use_bm = sb.checkbox(
        "Use PDF bookmarks if present", True,
        help="Agar bidder ki PDF me bookmarks (merge karte waqt bane) hain to wahi document boundaries maane jayenge.",
    )
    sens_label = sb.select_slider(
        "Detection sensitivity", ["Low", "Medium", "High"], "Medium",
        help="Low = sirf clear titles par split.  High = zyada documents pakadta hai, par galat split bhi ho sakte hain.",
    )
    sens = {"Low": 1, "Medium": 2, "High": 3}[sens_label]

    sb.subheader("Scanned pages (OCR)")
    if sp.ocr_available():
        langs = sp.ocr_languages()
        lang_opts = ["eng"] + (["eng+hin"] if "hin" in langs else [])
        ocr_lang = sb.selectbox("OCR language", lang_opts, help="Hindi add karne se OCR thoda slow hota hai.")
        ocr_mode = sb.radio(
            "When to OCR", ["auto", "always", "off"], horizontal=True,
            help="auto = sirf wo pages jinme text nahi hai (scanned).  always = har page (watermark wali scans ke liye).",
        )
        ocr_scope = sb.radio(
            "OCR scope", ["header", "full"], horizontal=True,
            help="header = sirf page ka upar ka hissa (fast, titles ke liye kaafi).  full = poora page (slow).",
        )
    else:
        ocr_lang, ocr_mode, ocr_scope = "eng", "off", "header"
        sb.warning("OCR available nahi hai (tesseract install nahi). Scanned pages ke titles detect nahi honge. "
                   "Streamlit Cloud par `packages.txt` me `tesseract-ocr` add karein.")

    sb.subheader("Output")
    number_prefix = sb.checkbox("File name me serial number (01_, 02_ …)", True)

    sb.subheader("Custom documents")
    default_custom = ""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_doctypes.txt")
    if os.path.exists(path):
        try:
            default_custom = open(path, encoding="utf-8").read()
        except Exception:
            default_custom = ""
    custom = sb.text_area(
        "Apne document types (optional)", default_custom, height=130,
        placeholder="Solvency Letter = solvency letter | bank solvency\nSite Visit Report = site visit report",
        help="Ek line = ek document:  Title = phrase1 | phrase2.  Phrase wahi likhein jo document ke heading me hota hai.",
    )
    doc_types = parse_custom_doc_types(custom) + DEFAULT_DOC_TYPES
    sb.caption(f"{len(DEFAULT_DOC_TYPES)} built-in document types + {len(doc_types) - len(DEFAULT_DOC_TYPES)} custom")

    return {
        "use_bm": use_bm, "sens": sens, "ocr_lang": ocr_lang, "ocr_mode": ocr_mode,
        "ocr_scope": ocr_scope, "number_prefix": number_prefix, "doc_types": doc_types,
        "ext_sig": (ocr_mode, ocr_lang, ocr_scope),
        "det_sig": (use_bm, sens, hashlib.md5(custom.encode()).hexdigest()),
    }


# --------------------------------------------------------------------------- #
# bidder state
# --------------------------------------------------------------------------- #

def register_files(files) -> None:
    current: dict = {}
    for uf in files:
        key = f"{uf.name}|{uf.size}"
        if key in S.bidders:
            current[key] = S.bidders[key]
            continue
        data = uf.getvalue()
        b = {
            "key": key, "name": os.path.splitext(uf.name)[0], "filename": uf.name, "data": data,
            "n_pages": 0, "error": None, "pages": None, "bookmarks": [], "ext_sig": None,
            "det_sig": None, "seg_df": None, "edited_df": None, "ver": 0,
            "outputs": None, "out_ver": 0, "zip": None, "xlsx": None, "view": 0,
        }
        try:
            b["n_pages"] = sp.page_count(data)
        except Exception as e:  # noqa: BLE001
            b["error"] = f"Is PDF ko open nahi kar paaye ({e}). Password-protected ya damaged ho sakti hai."
        current[key] = b
    S.bidders = current            # files removed from the uploader are dropped (frees memory)


def segs_to_df(segs) -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "Include": s.include, "Start page": s.start + 1, "Title": s.title,
            "Confidence %": int(round(s.confidence * 100)), "Detected by": s.reason,
            "Page text (start)": s.preview,
        } for s in segs],
        columns=COLS,
    )


def df_to_segments(df: pd.DataFrame, n_pages: int, pages) -> tuple[list, list[str]]:
    warns: list[str] = []
    rows = []
    for _, r in df.iterrows():
        v = r.get("Start page")
        if pd.isna(v):
            continue
        start = min(max(int(v), 1), n_pages) - 1
        t = r.get("Title")
        title = "" if pd.isna(t) else str(t).strip()
        inc = r.get("Include")
        inc = True if pd.isna(inc) else bool(inc)
        c = r.get("Confidence %")
        conf = 1.0 if pd.isna(c) else float(c) / 100
        why = r.get("Detected by")
        why = "Manual" if pd.isna(why) or not str(why).strip() else str(why)
        pv = r.get("Page text (start)")
        pv = sp._preview(pages[start]) if (pd.isna(pv) or not str(pv).strip()) and pages else ("" if pd.isna(pv) else str(pv))
        rows.append(sp.Segment(start, title=title, confidence=conf, reason=why, preview=pv, include=inc))
    rows.sort(key=lambda s: s.start)
    uniq = []
    for s in rows:
        if uniq and uniq[-1].start == s.start:
            warns.append(f"Page {s.start + 1} par do documents the - pehla rakha gaya.")
            continue
        uniq.append(s)
    if not uniq:
        return [], ["Koi document row nahi hai."]
    if uniq[0].start != 0:
        warns.append(f"Pehle document ka start page 1 kar diya gaya (pages 1–{uniq[0].start} pehle document me jode gaye).")
        uniq[0].start = 0
    for k, s in enumerate(uniq):
        s.end = (uniq[k + 1].start - 1) if k + 1 < len(uniq) else n_pages - 1
    for k, s in enumerate(uniq, 1):
        if not s.title:
            s.title = f"Document {k}"
    return uniq, warns


def analyze(b: dict, cfg: dict, bar=None) -> None:
    def cb(frac: float, msg: str) -> None:
        if bar is not None:
            bar.progress(min(max(frac, 0.0), 1.0), text=f"{b['name']}: {msg}")

    if b["pages"] is None or b["ext_sig"] != cfg["ext_sig"]:
        b["pages"] = sp.extract_pages(b["data"], cfg["ocr_mode"], cfg["ocr_lang"], cfg["ocr_scope"], progress=cb)
        b["bookmarks"] = sp.read_bookmarks(b["data"])
        b["ext_sig"] = cfg["ext_sig"]
    segs = sp.detect_segments(b["pages"], cfg["doc_types"], b["bookmarks"], cfg["use_bm"], cfg["sens"])
    b["seg_df"] = segs_to_df(segs)
    b["edited_df"] = None
    b["det_sig"] = cfg["det_sig"]
    b["ver"] += 1
    b["outputs"] = None
    b["zip"] = b["xlsx"] = None


def generate(b: dict, cfg: dict, bar=None) -> list[str]:
    df = b["edited_df"] if b["edited_df"] is not None else b["seg_df"]
    segs, warns = df_to_segments(df, b["n_pages"], b["pages"])

    def cb(frac: float, msg: str) -> None:
        if bar is not None:
            bar.progress(min(max(frac, 0.0), 1.0), text=f"{b['name']}: {msg}")

    outs = sp.split_pdf(b["data"], segs, number_prefix=cfg["number_prefix"], progress=cb)
    b["outputs"] = outs
    b["out_ver"] += 1
    b["view"] = 0
    b["xlsx"] = sp.build_index_xlsx([sp.index_dataframe(b["name"], outs)])
    b["zip"] = sp.build_zip([(o.filename, o.data) for o in outs] + [("Index.xlsx", b["xlsx"])])
    return warns


def all_bidders_zip() -> bytes | None:
    done = [b for b in S.bidders.values() if b["outputs"]]
    if not done:
        return None
    sig = tuple((b["key"], b["out_ver"], b["name"]) for b in done)
    cached = S.get("all_zip")
    if cached and cached[0] == sig:
        return cached[1]
    entries, frames, used = [], [], set()
    for b in done:
        folder = sp.safe_folder(b["name"])
        base, c = folder, 2
        while folder.lower() in used:
            folder = f"{base}_{c}"
            c += 1
        used.add(folder.lower())
        entries += [(f"{folder}/{o.filename}", o.data) for o in b["outputs"]]
        frames.append(sp.index_dataframe(b["name"], b["outputs"]))
    entries.append(("Index_all_bidders.xlsx", sp.build_index_xlsx(frames)))
    blob = sp.build_zip(entries)
    S["all_zip"] = (sig, blob)
    return blob


# --------------------------------------------------------------------------- #
# UI blocks
# --------------------------------------------------------------------------- #

def show_review(b: dict, cfg: dict) -> None:
    bk = bkey(b["key"])
    pages = b["pages"]
    n = b["n_pages"]

    unread = sum(1 for p in pages if p.scanned and not p.ocr)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total pages", n)
    c2.metric("Documents found", len(b["seg_df"]))
    c3.metric("OCR-read pages", sum(1 for p in pages if p.ocr))
    low = int((pd.to_numeric(b["seg_df"]["Confidence %"], errors="coerce").fillna(100) < 50).sum())
    c4.metric("Need checking", low, help="Jin documents ka title confidently nahi mila.")

    if b["ext_sig"] != cfg["ext_sig"] or b["det_sig"] != cfg["det_sig"]:
        st.info("Sidebar settings badal gayi hain - naye result ke liye **Analyze** dobara dabayein "
                "(table me kiye gaye edits reset ho jayenge).")
    if unread:
        st.warning(f"{unread} pages scanned (image) hain par OCR off / unavailable hai, isliye unka title detect nahi hoga. "
                   "Sidebar me OCR on karein ya neeche table me manually split dein.")
    if b["seg_df"].shape[0] == 1:
        st.info("Sirf 1 document mila. Sensitivity **High** karke dobara Analyze karein, ya neeche manually split jodein.")

    st.markdown("##### 2️⃣ Review documents")
    st.caption(
        "Title badalna ho to cell par double-click karein • galat split ho to row delete karein (pages pichhle document me jud jayenge) "
        "• naya document jodna ho to table ke neeche **+** se row jodein ya niche 'Page check' use karein • "
        "jo document output me nahi chahiye uska **Include** hata dein."
    )
    edited = st.data_editor(
        b["seg_df"], key=f"ed_{bk}_{b['ver']}", num_rows="dynamic", hide_index=True,
        column_config={
            "Include": st.column_config.CheckboxColumn("Include", default=True),
            "Start page": st.column_config.NumberColumn("Start page", min_value=1, max_value=max(n, 1), step=1, format="%d", required=True),
            "Title": st.column_config.TextColumn("Document title (file name)", required=True, width="medium"),
            "Confidence %": st.column_config.NumberColumn("Confidence", format="%d%%"),
            "Detected by": st.column_config.TextColumn("Detected by"),
            "Page text (start)": st.column_config.TextColumn("First text on start page", width="large"),
        },
        disabled=["Confidence %", "Detected by", "Page text (start)"],
    )
    b["edited_df"] = edited

    segs, warns = df_to_segments(edited, n, pages)
    for w in warns:
        st.warning(w)
    if segs:
        res = pd.DataFrame([{
            "#": k, "Title": s.title, "Pages": f"{s.start + 1} – {s.end + 1}", "Count": s.n_pages,
            "Output": "✅" if s.include else "⛔ skipped",
        } for k, s in enumerate(segs, 1)])
        with st.expander(f"Final split preview - {sum(s.include for s in segs)} PDFs will be created", expanded=False):
            st.dataframe(res, hide_index=True)

    with st.expander("🔎 Page check - boundary verify karein / is page se naya document shuru karein"):
        cc1, cc2 = st.columns([1, 4])
        pg = cc1.number_input("Page number", 1, max(n, 1), 1, key=f"chk_{bk}")
        imgs = cached_images(f"{bk}:src", (pg - 2, pg - 1, pg), 0.5, b["data"])
        cols = cc2.columns(3)
        for col, img, num in zip(cols, imgs, (pg - 1, pg, pg + 1)):
            if img:
                col.image(img, caption=f"Page {num}" + ("  ← selected" if num == pg else ""))
        if cc1.button("➕ Start new document here", key=f"split_{bk}"):
            cur, _ = df_to_segments(edited, n, pages)
            df = segs_to_df(cur)
            if pg in set(df["Start page"]):
                st.warning(f"Page {pg} par pehle se ek document shuru hota hai.")
            else:
                row = {"Include": True, "Start page": pg, "Title": "New Document", "Confidence %": 100,
                       "Detected by": "Manual", "Page text (start)": sp._preview(pages[pg - 1])}
                b["seg_df"] = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values("Start page").reset_index(drop=True)
                b["ver"] += 1
                st.rerun()

    st.markdown("##### 3️⃣ Create PDFs")
    if st.button("✂️ Create separate PDFs", type="primary", key=f"gen_{bk}", disabled=not segs):
        bar = st.progress(0.0, text="Creating PDFs…")
        try:
            for w in generate(b, cfg, bar):
                st.warning(w)
        except Exception as e:  # noqa: BLE001
            st.error(f"PDF banane me error: {e}")
        bar.empty()


def show_results(b: dict) -> None:
    outs = b["outputs"]
    if not outs:
        return
    bk = bkey(b["key"])
    st.markdown("##### 4️⃣ Download · View · Print")
    st.success(f"✅ {len(outs)} PDFs ready - {b['name']}")

    z1, z2, z3 = st.columns(3)
    z1.download_button("📦 Download all (ZIP)", b["zip"], f"{sp.safe_folder(b['name'])}_documents.zip",
                       "application/zip", key=f"zip_{bk}_{b['out_ver']}", type="primary")
    z2.download_button("📊 Index (Excel)", b["xlsx"], f"{sp.safe_folder(b['name'])}_index.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key=f"xl_{bk}_{b['out_ver']}")
    big = all_bidders_zip() if sum(1 for x in S.bidders.values() if x["outputs"]) > 1 else None
    if big:
        z3.download_button("📦 All bidders (ZIP)", big, "all_bidders_documents.zip", "application/zip",
                           key=f"allzip_{bk}_{b['out_ver']}")

    left, right = st.columns([5, 6], gap="large")
    with left:
        for k, o in enumerate(outs):
            r = st.columns([0.5, 3.0, 1.1, 1.0, 1.4, 1.0], vertical_alignment="center")
            r[0].write(f"{k + 1}")
            r[1].markdown(f"**{html.escape(o.title)}**  \n<span style='color:#64748b;font-size:12px'>{html.escape(o.filename)}</span>",
                          unsafe_allow_html=True)
            r[2].caption(f"p.{o.start + 1}–{o.end + 1}  \n{o.n_pages} pg")
            r[3].caption(fmt_size(len(o.data)))
            r[4].download_button("⬇ PDF", o.data, o.filename, "application/pdf", key=f"dl_{bk}_{b['out_ver']}_{k}")
            if r[5].button("👁 View", key=f"vw_{bk}_{k}"):
                b["view"] = k

    with right:
        k = min(b["view"], len(outs) - 1)
        o = outs[k]
        st.markdown(f"**{o.filename}**  ·  {o.n_pages} pages  ·  {fmt_size(len(o.data))}")
        if len(o.data) <= MAX_EMBED_BYTES:
            embed_html(pdf_tools_html(o.data, o.filename), 52)
        else:
            st.info("File badi hai - Open/Print ke liye pehle '⬇ PDF' se download karein.")
        t_pages, t_full = st.tabs(["Page preview", "Full PDF viewer"])
        with t_pages:
            vk = f"{bk}_{b['out_ver']}_{k}"
            if o.n_pages > 1:
                page_no = st.slider("Page", 1, o.n_pages, 1, key=f"pg_{vk}")
            else:
                page_no = 1
            img = cached_images(f"{bk}:{b['out_ver']}:{k}", (page_no - 1,), 1.3, o.data)[0]
            if img:
                st.image(img, caption=f"{o.title} - page {page_no} of {o.n_pages}")
            if o.n_pages > 1 and st.checkbox("Show thumbnails of all pages", key=f"th_{vk}"):
                shown = min(o.n_pages, 40)
                thumbs = cached_images(f"{bk}:{b['out_ver']}:{k}:t", tuple(range(shown)), 0.35, o.data)
                grid = st.columns(4)
                for i, t in enumerate(thumbs):
                    if t:
                        grid[i % 4].image(t, caption=f"{i + 1}")
                if o.n_pages > shown:
                    st.caption(f"First {shown} pages shown.")
        with t_full:
            try:
                st.pdf(o.data, height=720)
            except Exception:
                st.info("In-page PDF viewer ke liye `streamlit[pdf]` chahiye. Abhi **Open in new tab** ya Page preview use karein.")


def show_help() -> None:
    st.info("**Kaise kaam karta hai**  \n"
            "1. Bidder ki merged PDF(s) upload karein  \n"
            "2. **Analyze** dabayein - app har document ki shuruaat dhoondhti hai (title, bookmarks, divider pages, scanned pages OCR se)  \n"
            "3. Table me titles / boundaries check karein, zarurat ho to badlein  \n"
            "4. **Create separate PDFs** → har document alag PDF, ZIP aur Excel index ke saath")


# --------------------------------------------------------------------------- #
# page
# --------------------------------------------------------------------------- #

st.title("📑 Tender PDF Splitter")
st.caption("Bidder ki ek merged PDF me jitne documents hain (GST, PAN, Incorporation, Turnover, Past Experience …) "
           "unhe alag-alag PDF me todta hai - document ke title ke naam se.")

cfg = read_settings()

st.markdown("##### 1️⃣ Upload")
files = st.file_uploader("Bidder ki merged PDF(s)", type=["pdf"], accept_multiple_files=True,
                         help="Ek ya zyada bidders ki PDF ek saath upload kar sakte hain. 400–500 pages bhi chalega.")
register_files(files or [])
bidders = S.bidders

if not bidders:
    show_help()
    st.stop()

keys = list(bidders.keys())
if len(keys) > 1:
    st.write(f"**{len(keys)} bidders** uploaded.")
    a1, a2, _ = st.columns([1, 1, 3])
    if a1.button("🔍 Analyze all bidders"):
        bar = st.progress(0.0, text="Starting…")
        for key in keys:
            if not bidders[key]["error"]:
                try:
                    analyze(bidders[key], cfg, bar)
                except Exception as e:  # noqa: BLE001
                    bidders[key]["error"] = f"Analyze fail: {e}"
        bar.empty()
    if a2.button("⚡ Analyze + create PDFs (all)", help="Review ke bina seedha sab bidders ke PDFs bana deta hai."):
        bar = st.progress(0.0, text="Starting…")
        for key in keys:
            b = bidders[key]
            if b["error"]:
                continue
            try:
                analyze(b, cfg, bar)
                generate(b, cfg, bar)
            except Exception as e:  # noqa: BLE001
                b["error"] = f"Fail: {e}"
        bar.empty()
    sel = st.selectbox("Bidder", keys, format_func=lambda k: f"{bidders[k]['name']}  ({bidders[k]['n_pages']} pages)")
else:
    sel = keys[0]

b = bidders[sel]
bk = bkey(b["key"])
st.divider()
h1, h2 = st.columns([3, 2], vertical_alignment="bottom")
b["name"] = h1.text_input("Bidder name (ZIP / Excel me use hoga)", b["name"], key=f"name_{bk}")
h2.caption(f"📄 {b['filename']} · {b['n_pages']} pages · {fmt_size(len(b['data']))}")

if b["error"]:
    st.error(b["error"])
    st.stop()

label = "🔍 Analyze" if b["seg_df"] is None else "🔄 Re-analyze (edits reset)"
if st.button(label, type="primary" if b["seg_df"] is None else "secondary", key=f"an_{bk}"):
    bar = st.progress(0.0, text="Starting…")
    try:
        analyze(b, cfg, bar)
    except Exception as e:  # noqa: BLE001
        st.error(f"Analyze me error: {e}")
    bar.empty()

if b["seg_df"] is not None:
    show_review(b, cfg)
    show_results(b)
else:
    st.caption("Settings sidebar me hain. Scanned PDF ho to OCR on rakhein. Taiyar ho to **Analyze** dabayein.")
