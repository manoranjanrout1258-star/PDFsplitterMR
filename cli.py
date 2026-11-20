"""Command-line version (no browser needed) - handy for many bidders at once.

    python cli.py bidder1.pdf bidder2.pdf -o output
    python cli.py big.pdf -o output --ocr always --sens 3
    python cli.py big.pdf --dry-run          # only print what would be created
"""
from __future__ import annotations

import argparse
import os
import sys

import splitter as sp
from doctypes import DEFAULT_DOC_TYPES, parse_custom_doc_types


def main() -> int:
    ap = argparse.ArgumentParser(description="Split merged tender PDFs into one PDF per document.")
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("-o", "--out", default="output")
    ap.add_argument("--ocr", choices=["auto", "always", "off"], default="auto")
    ap.add_argument("--ocr-lang", default="eng")
    ap.add_argument("--ocr-scope", choices=["header", "full"], default="header")
    ap.add_argument("--sens", type=int, choices=[1, 2, 3], default=2, help="1 low, 2 medium, 3 high")
    ap.add_argument("--no-bookmarks", action="store_true")
    ap.add_argument("--no-prefix", action="store_true")
    ap.add_argument("--custom", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_doctypes.txt"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    custom = parse_custom_doc_types(open(a.custom, encoding="utf-8").read()) if os.path.exists(a.custom) else []
    types = custom + DEFAULT_DOC_TYPES
    frames = []
    for path in a.pdfs:
        name = os.path.splitext(os.path.basename(path))[0]
        data = open(path, "rb").read()
        print(f"\n=== {name}  ({sp.page_count(data)} pages)")
        pages = sp.extract_pages(
            data, a.ocr, a.ocr_lang, a.ocr_scope,
            progress=lambda f, m: print(f"\r{m:<60}", end="", file=sys.stderr),
        )
        print(file=sys.stderr)
        segs = sp.detect_segments(pages, types, sp.read_bookmarks(data), not a.no_bookmarks, a.sens)
        for k, s in enumerate(segs, 1):
            flag = "  <-- check" if s.confidence < 0.5 else ""
            print(f"{k:>3}. p.{s.start + 1:>4}-{s.end + 1:<4} {s.title:<45} {s.confidence * 100:3.0f}%  [{s.reason}]{flag}")
        if a.dry_run:
            continue
        outs = sp.split_pdf(data, segs, number_prefix=not a.no_prefix)
        folder = os.path.join(a.out, sp.safe_folder(name))
        os.makedirs(folder, exist_ok=True)
        for o in outs:
            with open(os.path.join(folder, o.filename), "wb") as fh:
                fh.write(o.data)
        frames.append(sp.index_dataframe(name, outs))
        with open(os.path.join(folder, "Index.xlsx"), "wb") as fh:
            fh.write(sp.build_index_xlsx([frames[-1]]))
        print(f"-> {len(outs)} PDFs written to {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
