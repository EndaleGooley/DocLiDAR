from __future__ import annotations
import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import shutil
import subprocess

SUPPORTED_EXTS = {".pdf", ".docx"}

def collect_inputs(inputs: List[str], in_dir: Optional[str]) -> List[Path]:
    items: List[Path] = []

    if in_dir:
        d = Path(in_dir).expanduser().resolve()
        if not d.exists() or not d.is_dir():
            raise FileNotFoundError(f"--in-dir not found or not a directory: {d}")
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                items.append(p)

    for s in inputs:
        p = Path(s).expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Input file not found: {p}")
        if p.suffix.lower() not in SUPPORTED_EXTS:
            raise ValueError(f"Unsupported input type: {p.suffix} (only .pdf, .docx)")
        items.append(p)

    # de-duplicate preserving order
    seen = set()
    uniq: List[Path] = []
    for p in items:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq

def is_pdf(p: Path) -> bool:
    return p.suffix.lower() == ".pdf"

def is_docx(p: Path) -> bool:
    return p.suffix.lower() == ".docx"

def convert_docx_to_pdf(docx_path: Path, out_pdf_path: Path) -> Path:
    """
    Try docx2pdf (Windows/macOS) first; fall back to LibreOffice (soffice) if available.
    """
    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) docx2pdf
    try:
        import docx2pdf  # type: ignore
        docx2pdf.convert(str(docx_path), str(out_pdf_path))
        if out_pdf_path.exists():
            return out_pdf_path
    except Exception:
        pass

    # 2) LibreOffice (cross-platform if installed)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        outdir = out_pdf_path.parent
        cmd = [
            soffice,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(docx_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        produced = outdir / (docx_path.stem + ".pdf")
        if produced.exists():
            if produced != out_pdf_path:
                produced.replace(out_pdf_path)
            return out_pdf_path

    raise RuntimeError(
        "DOCX->PDF conversion failed. Install either:\n"
        "  - docx2pdf (Windows/macOS), or\n"
        "  - LibreOffice (soffice) for headless conversion.\n"
        "Then retry."
    )