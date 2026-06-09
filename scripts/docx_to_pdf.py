# -*- coding: utf-8 -*-
"""
docx → PDF (使用本地 Word via win32com)
用法: python docx_to_pdf.py <src.docx> [dst.pdf]
"""
import os
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python docx_to_pdf.py <src.docx> [dst.pdf]")
        sys.exit(1)
    src = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        dst = Path(sys.argv[2])
    else:
        dst = src.with_suffix('.pdf')

    if not src.exists():
        print(f"ERR: source not found: {src}")
        sys.exit(1)
    if not dst.parent.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)

    import win32com.client
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0

    try:
        abs_src = os.path.abspath(str(src))
        doc = word.Documents.Open(abs_src)
        try:
            abs_dst = os.path.abspath(str(dst))
            # 17 = wdFormatPDF
            doc.SaveAs2(abs_dst, FileFormat=17)
            print(f"OK: {dst}")
            print(f"Size: {dst.stat().st_size} bytes")
        finally:
            doc.Close(False)
    finally:
        word.Quit()

if __name__ == "__main__":
    main()
