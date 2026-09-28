"""
extractor.py — PDF text/table extraction for Spendmind bank statements.

Touchpoint 2 of the Financial Data Pipeline & NLP-Based Transaction
Categorization Engine.

Responsibility: turn a PDF bank statement into raw, cleaned text lines
(plus any tables pdfplumber detects). Turning those lines into structured
transactions is parser.py's job (Touchpoint 3), so this module stays
deliberately simple and makes no assumptions about statement layout.

Place at: src/pipeline/extractor.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def _validate_pdf_path(pdf_path: str | Path) -> Path:
    """Fail early, with a clear message, on a missing or non-PDF input."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Input file must be a PDF, got: {path.name}")
    return path


def _clean_table(table: list[list[str | None]]) -> list[list[str]]:
    """Replace None cells with '' and strip whitespace; drop fully empty rows."""
    cleaned = []
    for row in table:
        cells = [(cell or "").strip() for cell in row]
        if any(cells):
            cleaned.append(cells)
    return cleaned


def extract_pdf(pdf_path: str | Path) -> dict:
    """
    Extract everything parser.py might need from one PDF, opening it once.

    Returns:
        {
            "file_name": str,
            "num_pages": int,
            "lines":  list[str],               # flat, cleaned text lines (primary output)
            "tables": list[list[list[str]]],   # every table found, cleaned (may be empty)
        }
    """
    path = _validate_pdf_path(pdf_path)

    lines: list[str] = []
    tables: list[list[list[str]]] = []

    with pdfplumber.open(path) as pdf:
        num_pages = len(pdf.pages)

        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            page_lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            lines.extend(page_lines)

            page_tables = [_clean_table(t) for t in page.extract_tables()]
            page_tables = [t for t in page_tables if t]
            tables.extend(page_tables)

            logger.debug(
                "Page %d: %d line(s), %d table(s)",
                page_number, len(page_lines), len(page_tables),
            )

    logger.info("Extracted %s: %d pages, %d lines, %d tables",
                path.name, num_pages, len(lines), len(tables))

    return {
        "file_name": path.name,
        "num_pages": num_pages,
        "lines": lines,
        "tables": tables,
    }


def extract_lines(pdf_path: str | Path) -> list[str]:
    """Convenience wrapper: just the flat list of cleaned text lines."""
    return extract_pdf(pdf_path)["lines"]


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    # Resolve the sample PDF relative to this file, so the test works
    # no matter which directory it is launched from.
    project_root = Path(__file__).resolve().parent.parent.parent
    default_pdf = project_root / "sample_data" / "sample_bank_statement.pdf"
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else default_pdf

    print(f"Testing extraction on: {target}\n")

    try:
        result = extract_pdf(target)
    except (FileNotFoundError, ValueError) as err:
        print(f"Error: {err}")
        sys.exit(1)

    print(f"File: {result['file_name']}  |  Pages: {result['num_pages']}  |  "
          f"Lines: {len(result['lines'])}  |  Tables: {len(result['tables'])}\n")

    print("--- First 15 lines ---")
    for i, line in enumerate(result["lines"][:15]):
        print(f"{i:>3}: {line}")

    if result["tables"]:
        print("\n--- First table, first 3 rows ---")
        for row in result["tables"][0][:3]:
            print(row)
    else:
        print("\nNo tables detected — parser.py will work from text lines.")