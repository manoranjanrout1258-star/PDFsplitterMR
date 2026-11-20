"""Core engine: one merged tender PDF  ->  separate document PDFs.

Pipeline
  1. extract_pages()    read the text of every page (OCR for scanned pages)
  2. detect_segments()  find where each document starts (bookmarks, titles,
                        divider pages, page-size change, "Page 1 of N")
  3. split_pdf()        write one PDF per document
  4. build_zip() / build_index_xlsx()  package the results

Only pip-installable libraries are used (pypdfium2, pypdf, Pillow, pytesseract);
the `tesseract` program is needed only for scanned pages (OCR).
"""

from __future__ import annotations

import io
import os
import re
import shutil
import threading
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Optional

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter

from doctypes import DEFAULT_DOC_TYPES

# pdfium is not thread-safe; Streamlit runs every user session in its own thread.
_PDFIUM_LOCK = threading.RLock()

ProgressCB = Callable[[float, str], None]


# --------------------------------------------------------------------------- #
# text normalisation and phrase matching
# --------------------------------------------------------------------------- #

_KEEP = re.compile(r"[^\wऀ-ॿ]+")  # keep letters/digits and Devanagari


def norm(text: str) -> str:
    """lower-case, strip punctuation, single spaces, padded with one space each side."""
    text = unicodedata.normalize("NFKC", text or "").lower().replace("_", " ")
    text = _KEEP.sub(" ", text)
    return " " + re.sub(r"\s+", " ", text).strip() + " "


@dataclass(frozen=True)
class _Phrase:
    spaced: str      # " gst reg 06 "
    squashed: str    # "gstreg06"  (helps with OCR that drops / adds spaces)


def _phrase(p: str) -> _Phrase:
    n = norm(p)
    return _Phrase(n, n.replace(" ", ""))


@dataclass
class CompiledType:
    name: str
    strong: list[_Phrase]
    weak: list[_Phrase]


def compile_types(types: list[dict]) -> list[CompiledType]:
    return [
        CompiledType(
            t["name"],
            [_phrase(p) for p in t.get("strong", []) if p.strip()],
            [_phrase(p) for p in t.get("weak", []) if p.strip()],
        )
        for t in types
    ]


def _has(p: _Phrase, spaced: str, squashed: str) -> bool:
    if p.spaced in spaced:
        return True
    return len(p.squashed) >= 10 and p.squashed in squashed


# --------------------------------------------------------------------------- #
# page extraction (text + OCR)
# --------------------------------------------------------------------------- #

@dataclass
class PageInfo:
    index: int                 # 0-based
    width: float
    height: float
    text: str = ""
    header: str = ""           # first few lines
    scanned: bool = False      # almost no text layer
    ocr: bool = False          # text came from OCR


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return False
    return shutil.which("tesseract") is not None


def ocr_languages() -> list[str]:
    if not ocr_available():
        return []
    try:
        import pytesseract
        return sorted(pytesseract.get_languages(config=""))
    except Exception:
        return ["eng"]


def _header_of(text: str, max_lines: int = 8, max_chars: int = 500) -> str:
    lines = [l.strip() for l in text.replace("\r", "\n").split("\n") if l.strip()]
    return "\n".join(lines[:max_lines])[:max_chars]


def _ocr_image(img, lang: str) -> str:
    import pytesseract
    try:
        return pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    except Exception:
        return ""


def extract_pages(
    data: bytes,
    ocr_mode: str = "auto",       # "off" | "auto" | "always"
    ocr_lang: str = "eng",
    ocr_scope: str = "header",    # "header" (top 40%, fast) | "full"
    progress: Optional[ProgressCB] = None,
    min_chars: int = 40,
) -> list[PageInfo]:
    """Read text of every page.  Pages with (almost) no text are OCR-ed when allowed."""
    pages: list[PageInfo] = []
    with _PDFIUM_LOCK:
        pdf = pdfium.PdfDocument(data)
        try:
            n = len(pdf)
            for i in range(n):
                page = pdf[i]
                try:
                    w, h = page.get_size()
                    tp = page.get_textpage()
                    try:
                        text = tp.get_text_range() or ""
                    finally:
                        tp.close()
                finally:
                    page.close()
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                scanned = len(re.sub(r"\s+", "", text)) < min_chars
                pages.append(PageInfo(i, float(w), float(h), text, _header_of(text), scanned))
                if progress and (i % 20 == 0 or i == n - 1):
                    progress(0.35 * (i + 1) / n, f"Reading text… page {i + 1}/{n}")
        finally:
            pdf.close()

    want = (
        [p.index for p in pages]
        if ocr_mode == "always"
        else [p.index for p in pages if p.scanned] if ocr_mode == "auto" else []
    )
    if want and ocr_available():
        _ocr_into(pages, data, want, ocr_lang, ocr_scope, progress)
    elif progress:
        progress(1.0, "Text read")
    return pages


def _ocr_into(pages: list[PageInfo], data: bytes, idxs: list[int], lang: str,
              scope: str, progress: Optional[ProgressCB]) -> None:
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")   # one thread per tesseract process
    workers = max(1, min(4, os.cpu_count() or 1))
    batch = workers * 4
    crop = 0.40 if scope == "header" else 1.0
    dpi = 150 if scope == "header" else 130
    total = len(idxs)
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        for b in range(0, total, batch):
            chunk = idxs[b:b + batch]
            imgs = []
            with _PDFIUM_LOCK:
                pdf = pdfium.PdfDocument(data)
                try:
                    for i in chunk:
                        page = pdf[i]
                        try:
                            img = page.render(scale=dpi / 72).to_pil().convert("L")
                        finally:
                            page.close()
                        if crop < 1.0:
                            img = img.crop((0, 0, img.width, int(img.height * crop)))
                        imgs.append(img)
                finally:
                    pdf.close()
            for i, text in zip(chunk, ex.map(lambda im: _ocr_image(im, lang), imgs)):
                pg = pages[i]
                if len(re.sub(r"\s+", "", text)) >= len(re.sub(r"\s+", "", pg.text)):
                    pg.text = text
                    pg.header = _header_of(text)
                    pg.ocr = True
            done += len(chunk)
            if progress:
                progress(0.35 + 0.65 * done / total, f"OCR… {done}/{total} scanned pages")


# --------------------------------------------------------------------------- #
# bookmarks
# --------------------------------------------------------------------------- #

def read_bookmarks(data: bytes) -> list[tuple[int, str, int]]:
    """[(level, title, page_index)] from the PDF outline, [] when none."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            reader.decrypt("")
        outline = reader.outline
    except Exception:
        return []
    out: list[tuple[int, str, int]] = []

    def walk(items, level):
        for it in items:
            if isinstance(it, list):
                walk(it, level + 1)
                continue
            try:
                pg = reader.get_destination_page_number(it)
                title = str(it.title)
            except Exception:
                continue
            if pg is not None and pg >= 0:
                out.append((level, title, int(pg)))

    try:
        walk(outline, 1)
    except Exception:
        return []
    return out


# --------------------------------------------------------------------------- #
# boundary detection
# --------------------------------------------------------------------------- #

@dataclass
class Segment:
    start: int                 # 0-based first page
    end: int = -1              # 0-based last page (inclusive)
    title: str = ""
    confidence: float = 0.0    # 0..1
    reason: str = ""
    preview: str = ""          # first words of the first page
    include: bool = True

    @property
    def n_pages(self) -> int:
        return self.end - self.start + 1


_PAGE1_RE = re.compile(r"\bpage\s*(?:no\.?)?\s*:?\s*1\s*(?:of|/|out of)\s*\d{1,4}\b", re.I)

_DIVIDER_RE = re.compile(
    r"^\s*(annexure|annex|appendix|attachment|enclosure|exhibit|schedule|tab|document|doc|"
    r"part|section|volume|folder|file|अनुलग्नक|परिशिष्ट|संलग्नक)\b"
    r"[\s\-–—:.#]*((?:\d{1,3}|[ivx]{1,4}|[a-z])(?![a-z]))?",
    re.I,
)


_FUNC_WORDS = {"of", "and", "for", "the", "to", "in", "on", "at", "by", "as", "or", "a", "an",
               "under", "with", "from", "is", "no", "cum"}


def _is_title_like(line: str) -> bool:
    """Headings are short, rarely end with a full stop and are mostly Capitalised / UPPER.
    A sentence that merely *mentions* "GST returns" is not a heading."""
    s = line.strip()
    words = s.split()
    if not words or len(words) > 14:
        return False
    if s.endswith((".", ",", ";")) and len(words) > 3:
        return False
    if len(words) <= 4:
        return True
    content = [w for w in re.findall(r"[^\W\d_]+", s) if w.lower() not in _FUNC_WORDS and len(w) > 1]
    if not content:
        return False
    return sum(1 for w in content if w[0].isupper()) / len(content) >= 0.7


@dataclass
class _Feat:
    units: list[tuple[str, str]]    # heading candidates: (spaced, squashed)
    h_sp: str
    h_sq: str
    f_sp: str
    f_sq: str
    n_words: int
    page1: bool
    divider: bool


def _features(p: PageInfo, strict_titles: bool = True) -> _Feat:
    h_sp = norm(p.header)
    f_sp = norm(p.text)
    lines = [l for l in p.header.split("\n") if l.strip()]
    ok = [(strict_titles is False) or _is_title_like(l) for l in lines]
    units: list[tuple[str, str]] = []
    for k, l in enumerate(lines):
        if ok[k]:
            n1 = norm(l)
            units.append((n1, n1.replace(" ", "")))
            if k + 1 < len(lines) and ok[k + 1]:          # heading split over two lines
                n2 = norm(l + " " + lines[k + 1])
                units.append((n2, n2.replace(" ", "")))
    first = next((l.strip() for l in p.text.split("\n") if l.strip()), "")
    n_words = len(p.text.split())
    return _Feat(
        units, h_sp, h_sp.replace(" ", ""), f_sp, f_sp.replace(" ", ""), n_words,
        bool(_PAGE1_RE.search(p.text)),
        bool(first and n_words <= 35 and _DIVIDER_RE.match(first)),
    )


def _score(ct: CompiledType, f: _Feat) -> float:
    hs = sum(1 for p in ct.strong if any(_has(p, sp_, sq_) for sp_, sq_ in f.units))
    hw = sum(1 for p in ct.weak if _has(p, f.h_sp, f.h_sq))
    fs = sum(1 for p in ct.strong if _has(p, f.f_sp, f.f_sq))
    fw = sum(1 for p in ct.weak if _has(p, f.f_sp, f.f_sq))
    s = 0.0
    if hs:
        s += 10 + 2 * min(hs - 1, 2)
    s += 2 * min(hw, 3)
    s += 3 * min(max(fs - hs, 0), 2)
    s += 1 * min(max(fw - hw, 0), 4)
    return s


def _clean_title(s: str, maxlen: int = 60) -> str:
    s = re.sub(r"\s+", " ", s or "").strip(" -–—:.#_|")
    s = re.sub(r"^\(?[0-9a-zA-Z]{1,2}[\).]\s+", "", s)
    if len(s) > maxlen:
        s = s[:maxlen].rsplit(" ", 1)[0]
    return s.strip()


def _divider_title(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return ""
    first = lines[0]
    m = _DIVIDER_RE.match(first)
    rest = first[m.end():].strip(" -–—:.#") if m else first
    if len(rest) < 3 and len(lines) > 1:
        rest = lines[1]
    if len(rest) < 3:
        rest = first
    return _clean_title(rest)


def _preview(p: PageInfo) -> str:
    lines = [l.strip() for l in p.text.split("\n") if l.strip()]
    return re.sub(r"\s+", " ", " / ".join(lines[:2]))[:90]


def _size_changed(a: PageInfo, b: PageInfo) -> bool:
    return (abs(a.width - b.width) / max(a.width, 1) > 0.04
            or abs(a.height - b.height) / max(a.height, 1) > 0.04)


def _bookmark_segments(pages, bookmarks) -> Optional[list[Segment]]:
    if not bookmarks:
        return None
    top = min(b[0] for b in bookmarks)
    firsts: dict[int, str] = {}
    for level, title, pg in bookmarks:
        if level == top and 0 <= pg < len(pages) and pg not in firsts:
            firsts[pg] = title
    if len(firsts) < 2:
        return None
    segs = []
    for pg in sorted(firsts):
        t = re.sub(r"\.pdf$", "", firsts[pg].strip(), flags=re.I)
        t = _clean_title(re.sub(r"[_]+", " ", t))
        segs.append(Segment(pg, title=t or f"Document {len(segs) + 1}", confidence=1.0,
                            reason="PDF bookmark", preview=_preview(pages[pg])))
    if segs[0].start > 0:
        segs.insert(0, Segment(0, title="Front pages", confidence=0.4,
                               reason="Pages before first bookmark", preview=_preview(pages[0])))
    return segs


def detect_segments(
    pages: list[PageInfo],
    doc_types: Optional[list[dict]] = None,
    bookmarks: Optional[list[tuple[int, str, int]]] = None,
    use_bookmarks: bool = True,
    sensitivity: int = 2,           # 1 low, 2 medium, 3 high
) -> list[Segment]:
    n = len(pages)
    if n == 0:
        return []

    if use_bookmarks:
        segs = _bookmark_segments(pages, bookmarks or [])
        if segs:
            return _finish(segs, n)

    types = compile_types(doc_types or DEFAULT_DOC_TYPES)
    feats = [_features(p, strict_titles=sensitivity < 3) for p in pages]
    scores = [[_score(ct, f) for ct in types] for f in feats]

    def best(i: int) -> tuple[Optional[int], float]:
        row = scores[i]
        if not row:
            return None, 0.0
        m = max(row)
        return (row.index(m), m) if m > 0 else (None, 0.0)

    thr = {1: 10.0, 2: 10.0, 3: 7.0}.get(sensitivity, 10.0)
    boost_thr = {1: 10.0, 2: 6.0, 3: 4.0}.get(sensitivity, 6.0)

    segs: list[Segment] = []
    cur: Optional[int] = None          # type index of the current document
    pending_divider = False

    # first page always starts a document
    b_idx, b_sc = best(0)
    if feats[0].divider:
        title = types[b_idx].name if (b_idx is not None and b_sc >= 4) else _divider_title(pages[0].text)
        segs.append(Segment(0, title=title, confidence=0.8, reason="Divider page",
                            preview=_preview(pages[0])))
        cur = b_idx if (b_idx is not None and b_sc >= 4) else None
        pending_divider = True
    elif b_idx is not None and b_sc >= boost_thr:
        segs.append(Segment(0, title=types[b_idx].name, confidence=min(1.0, b_sc / 14),
                            reason="Title match", preview=_preview(pages[0])))
        cur = b_idx
    else:
        segs.append(Segment(0, title="", confidence=0.25, reason="First page (title not found)",
                            preview=_preview(pages[0])))

    for i in range(1, n):
        f = feats[i]
        b_idx, b_sc = best(i)
        cur_sc = scores[i][cur] if cur is not None else 0.0
        size_chg = _size_changed(pages[i - 1], pages[i])

        # 1. divider page ("Annexure 5", "Tab 3", ...) -----------------------------------
        if f.divider:
            known = b_idx is not None and b_sc >= 4
            title = types[b_idx].name if known else _divider_title(pages[i].text)
            segs.append(Segment(i, title=title, confidence=0.8,
                                reason="Divider page: " + _preview(pages[i])[:40],
                                preview=_preview(pages[i])))
            cur = b_idx if known else None
            pending_divider = True
            continue

        # page right after a divider: only gives the divider its real type
        if pending_divider:
            pending_divider = False
            if cur is None and b_idx is not None and b_sc >= boost_thr:
                segs[-1].title = types[b_idx].name
                segs[-1].confidence = max(segs[-1].confidence, min(1.0, b_sc / 14))
                cur = b_idx
            continue

        # 2. a different document type has its title on this page -----------------------
        new_type = (b_idx is not None and b_idx != cur and b_sc - cur_sc >= 3)
        reason = ""
        if new_type and b_sc >= thr:
            reason = "Title match"
        elif new_type and b_sc >= boost_thr and (size_chg or f.page1):
            reason = "Title match + " + ("page size changed" if size_chg else "'Page 1 of N'")
        elif sensitivity >= 3 and f.page1 and not new_type and (cur is None or cur_sc < 6):
            reason = "'Page 1 of N' (title not found)"

        if reason:
            segs.append(Segment(
                i,
                title=types[b_idx].name if (new_type and b_idx is not None) else "",
                confidence=min(1.0, b_sc / 14) if new_type else 0.3,
                reason=reason,
                preview=_preview(pages[i]),
            ))
            cur = b_idx if new_type else None

    return _finish(segs, n, pages)


def _finish(segs: list[Segment], n: int, pages: Optional[list[PageInfo]] = None) -> list[Segment]:
    segs.sort(key=lambda s: s.start)
    for k, s in enumerate(segs):
        s.end = (segs[k + 1].start - 1) if k + 1 < len(segs) else n - 1
    # note page-size changes inside a segment (possible missed boundary)
    if pages:
        for s in segs:
            for j in range(s.start + 1, s.end + 1):
                if _size_changed(pages[j - 1], pages[j]):
                    s.reason += f" | page size changes at p.{j + 1}"
                    break
    # name unidentified documents
    u = 0
    for s in segs:
        if not s.title:
            u += 1
            s.title = f"Unidentified Document {u}"
    return segs


# --------------------------------------------------------------------------- #
# splitting
# --------------------------------------------------------------------------- #

@dataclass
class OutDoc:
    title: str
    filename: str
    start: int
    end: int
    data: bytes
    confidence: float = 1.0
    reason: str = ""

    @property
    def n_pages(self) -> int:
        return self.end - self.start + 1


def safe_filename(title: str, maxlen: int = 80) -> str:
    t = unicodedata.normalize("NFKC", title or "").replace(" & ", " and ")
    t = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", t)
    t = re.sub(r"\s+", "_", t.strip())
    t = re.sub(r"_+", "_", t).strip("._ ")
    return t[:maxlen] or "Document"


def _pdfium_split(data: bytes, start: int, end: int) -> bytes:
    with _PDFIUM_LOCK:
        src = pdfium.PdfDocument(data)
        try:
            dst = pdfium.PdfDocument.new()
            try:
                dst.import_pages(src, list(range(start, end + 1)))
                buf = io.BytesIO()
                dst.save(buf)
                return buf.getvalue()
            finally:
                dst.close()
        finally:
            src.close()


def split_pdf(
    data: bytes,
    segments: list[Segment],
    number_prefix: bool = True,
    progress: Optional[ProgressCB] = None,
) -> list[OutDoc]:
    """Write one PDF per segment (segments with include=False are skipped)."""
    segs = [s for s in segments if s.include]
    reader = None
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            reader.decrypt("")
        _ = len(reader.pages)
    except Exception:
        reader = None

    used: set[str] = set()
    outs: list[OutDoc] = []
    for k, s in enumerate(segs, 1):
        blob: Optional[bytes] = None
        if reader is not None:
            try:
                w = PdfWriter()
                for i in range(s.start, s.end + 1):
                    w.add_page(reader.pages[i])
                w.add_metadata({"/Title": s.title})
                buf = io.BytesIO()
                w.write(buf)
                blob = buf.getvalue()
            except Exception:
                blob = None
        if blob is None:                      # fallback for damaged / unusual PDFs
            blob = _pdfium_split(data, s.start, s.end)

        base = safe_filename(s.title)
        name = f"{k:02d}_{base}" if number_prefix else base
        cand, c = name, 2
        while cand.lower() in used:
            cand = f"{name}_{c}"
            c += 1
        used.add(cand.lower())
        outs.append(OutDoc(s.title, cand + ".pdf", s.start, s.end, blob, s.confidence, s.reason))
        if progress:
            progress(k / len(segs), f"Creating PDFs… {k}/{len(segs)}")
    return outs


# --------------------------------------------------------------------------- #
# packaging
# --------------------------------------------------------------------------- #

def index_dataframe(bidder: str, outs: list[OutDoc]):
    import pandas as pd
    return pd.DataFrame([
        {
            "Bidder": bidder,
            "S.No": k,
            "Document title": o.title,
            "File name": o.filename,
            "Start page": o.start + 1,
            "End page": o.end + 1,
            "Total pages": o.n_pages,
            "Size (KB)": round(len(o.data) / 1024, 1),
            "Detected by": o.reason,
            "Confidence %": round(o.confidence * 100),
        }
        for k, o in enumerate(outs, 1)
    ])


def build_index_xlsx(frames) -> bytes:
    import pandas as pd
    df = pd.concat(list(frames), ignore_index=True) if frames else pd.DataFrame()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="Index")
        ws = xw.sheets["Index"]
        from openpyxl.styles import Font
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for col in ws.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 8), 60)
        ws.freeze_panes = "A2"
    return buf.getvalue()


def build_zip(entries: list[tuple[str, bytes]]) -> bytes:
    """entries = [(path_inside_zip, bytes)] - PDFs are already compressed, so just store."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for path, blob in entries:
            z.writestr(path, blob)
    return buf.getvalue()


def safe_folder(name: str) -> str:
    return safe_filename(name, 60)


# --------------------------------------------------------------------------- #
# rendering (preview images)
# --------------------------------------------------------------------------- #

def page_count(data: bytes) -> int:
    with _PDFIUM_LOCK:
        pdf = pdfium.PdfDocument(data)
        try:
            return len(pdf)
        finally:
            pdf.close()


def render_pages(data: bytes, indices: list[int], scale: float = 1.2, quality: int = 78) -> list[bytes]:
    """JPEG bytes of the requested pages (0-based)."""
    out: list[bytes] = []
    with _PDFIUM_LOCK:
        pdf = pdfium.PdfDocument(data)
        try:
            n = len(pdf)
            for i in indices:
                if not 0 <= i < n:
                    out.append(b"")
                    continue
                page = pdf[i]
                try:
                    img = page.render(scale=scale).to_pil().convert("RGB")
                finally:
                    page.close()
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=quality)
                out.append(buf.getvalue())
        finally:
            pdf.close()
    return out
