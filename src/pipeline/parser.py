"""
parser.py - turns extracted PDF content into structured transactions.

Touchpoint 3 of the Financial Data Pipeline & NLP-Based Transaction
Categorization Engine.

Input:  the dict returned by extractor.extract_pdf()  ({"lines": ..., "tables": ...})
Output: a list of Transaction objects, ready for categorization (Touchpoint 4)
        and storage (Touchpoint 5).

Expected statement layout:  Date | Narration | Amount | Type
    - dates are day-first (DD/MM/YYYY)
    - amounts may contain thousands separators (65,000.00)
    - Type is Dr (money out) or Cr (money in)

Two independent paths read the same data: the structured tables, and the
plain text lines. If both find the same number of transactions we have a
built-in cross-check; if they disagree, the larger set is used and a warning
is logged.

Place at: src/pipeline/parser.py
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DATE_FORMAT = "%d/%m/%Y"  # Indian statements are day-first: 03/06/2025 is 3 June

# Payment-method prefixes seen at the start of narrations, e.g. "UPI-ZOMATO-98765..."
KNOWN_METHODS = {"UPI", "NEFT", "IMPS", "RTGS", "POS", "ATM", "ACH", "NACH", "ECS"}

_DATE_START_RE = re.compile(r"^\d{2}/\d{2}/\d{4}")
_LINE_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Dr|Cr)$",
    re.IGNORECASE,
)
_REFERENCE_RE = re.compile(r"^\d{6,}$")  # trailing all-digit token = reference number


@dataclass(frozen=True)
class Transaction:
    date: dt.date
    narration: str        # original narration, whitespace-normalised
    amount: float         # always positive; direction is in txn_type
    txn_type: str         # "Dr" (money out) or "Cr" (money in)
    method: str           # UPI, NEFT, IMPS, POS, ATM, ... or "OTHER"
    merchant: str         # narration with method prefix and reference number removed
    reference: str | None

    @property
    def signed_amount(self) -> float:
        """Negative for debits, positive for credits."""
        return -self.amount if self.txn_type == "Dr" else self.amount


# ---------------------------------------------------------------------------
# Field parsers (each raises ValueError on bad input)
# ---------------------------------------------------------------------------

def parse_date(text: str) -> dt.date:
    return dt.datetime.strptime(text.strip(), DATE_FORMAT).date()


def parse_amount(text: str) -> float:
    amount = float(text.replace(",", "").strip())
    if amount < 0:
        raise ValueError(f"Negative amount: {text!r}")
    return amount


def parse_type(text: str) -> str:
    cleaned = text.strip().lower()
    if cleaned == "dr":
        return "Dr"
    if cleaned == "cr":
        return "Cr"
    raise ValueError(f"Unknown transaction type: {text!r}")


def parse_narration(narration: str) -> tuple[str, str, str | None]:
    """
    Split a narration into (method, merchant, reference).

        "UPI-ZOMATO-9876543210"   -> ("UPI", "ZOMATO", "9876543210")
        "POS-STARBUCKS-COFFEE"    -> ("POS", "STARBUCKS COFFEE", None)
        "NETFLIX.COM"             -> ("OTHER", "NETFLIX.COM", None)
    """
    tokens = [t.strip() for t in narration.split("-") if t.strip()]

    method = "OTHER"
    if tokens and tokens[0].upper() in KNOWN_METHODS:
        method = tokens.pop(0).upper()

    reference = None
    if tokens and _REFERENCE_RE.match(tokens[-1]):
        reference = tokens.pop()

    merchant = " ".join(tokens) if tokens else narration.strip()
    return method, merchant, reference


def _build_transaction(date_text: str, narration: str, amount_text: str,
                       type_text: str) -> Transaction:
    narration = " ".join(narration.split())  # collapse wrapped lines / extra spaces
    method, merchant, reference = parse_narration(narration)
    return Transaction(
        date=parse_date(date_text),
        narration=narration,
        amount=parse_amount(amount_text),
        txn_type=parse_type(type_text),
        method=method,
        merchant=merchant,
        reference=reference,
    )


# ---------------------------------------------------------------------------
# The two parsing paths
# ---------------------------------------------------------------------------

def _parse_tables(tables: list[list[list[str]]]) -> list[Transaction]:
    """Structured path: rows are already split into Date | Narration | Amount | Type."""
    transactions = []
    for table in tables:
        for row in table:
            # Header rows (repeated on every page), blanks and anything that
            # doesn't start with a date are not transactions - skip silently.
            if len(row) < 4 or not _DATE_START_RE.match(row[0]):
                continue
            try:
                transactions.append(_build_transaction(row[0], row[1], row[2], row[3]))
            except ValueError as err:
                logger.warning("Skipping unparseable table row %s: %s", row, err)
    return transactions


def _parse_lines(lines: list[str]) -> list[Transaction]:
    """Text path: works even when the PDF has no table gridlines."""
    transactions = []
    for line in lines:
        match = _LINE_RE.match(line)
        if match:
            try:
                transactions.append(_build_transaction(*match.groups()))
            except ValueError as err:
                logger.warning("Skipping unparseable line %r: %s", line, err)
        elif _DATE_START_RE.match(line):
            # Starts with a date but isn't a full transaction - worth flagging.
            # (Titles and column headings don't start with a date, so stay quiet.)
            logger.warning("Line starts with a date but is not a transaction: %r", line)
    return transactions


def parse_transactions(extracted: dict) -> list[Transaction]:
    """
    Parse the output of extractor.extract_pdf() into Transaction objects.

    Runs both paths. Tables are preferred when both agree; if the paths
    disagree, the path that found more transactions wins.
    """
    from_tables = _parse_tables(extracted.get("tables", []))
    from_lines = _parse_lines(extracted.get("lines", []))

    if not from_tables:
        logger.info("No table rows found; using text lines (%d transactions)", len(from_lines))
    elif len(from_tables) != len(from_lines):
        logger.warning(
            "Table path found %d transactions but text path found %d; using the larger set",
            len(from_tables), len(from_lines),
        )

    return from_tables if len(from_tables) >= len(from_lines) else from_lines


def summarize(transactions: list[Transaction]) -> dict:
    """Counts and totals - handy for reconciling against the source statement."""
    total_debits = sum(t.amount for t in transactions if t.txn_type == "Dr")
    total_credits = sum(t.amount for t in transactions if t.txn_type == "Cr")
    return {
        "count": len(transactions),
        "total_debits": round(total_debits, 2),
        "total_credits": round(total_credits, 2),
        "net": round(total_credits - total_debits, 2),
    }


if __name__ == "__main__":
    import sys
    from collections import Counter
    from pathlib import Path

    # Let `python src/pipeline/parser.py` find the `src` package when run as a script.
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    from src.pipeline.extractor import extract_pdf

    logging.basicConfig(level=logging.INFO)

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        project_root / "sample_data" / "sample_bank_statement.pdf"
    )
    print(f"Parsing: {target}\n")

    transactions = parse_transactions(extract_pdf(target))
    summary = summarize(transactions)

    print(f"{'DATE':<12}{'METHOD':<8}{'MERCHANT':<30}{'REFERENCE':<13}{'AMOUNT':>12}")
    for t in transactions[:10]:
        print(f"{t.date.isoformat():<12}{t.method:<8}{t.merchant:<30}"
              f"{t.reference or '-':<13}{t.signed_amount:>12,.2f}")
    if len(transactions) > 10:
        print(f"... and {len(transactions) - 10} more")

    print(f"\nTransactions:  {summary['count']}")
    print(f"Total debits:  {summary['total_debits']:,.2f}")
    print(f"Total credits: {summary['total_credits']:,.2f}")
    print(f"Net:           {summary['net']:,.2f}")
    print(f"Methods:       {dict(Counter(t.method for t in transactions))}")