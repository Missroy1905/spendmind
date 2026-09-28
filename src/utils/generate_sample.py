"""
generate_sample.py - builds a synthetic bank statement PDF for Spendmind.

Produces ~60 transactions over one month, covering several spending
categories, recurring items, credits and mixed narration styles, spread
across multiple pages (the column headings repeat on every page, like a
real statement). Output is seeded, so every run gives the same PDF.

Run from the project root:  python <path-to-this-file>
Output:                     sample_data/sample_bank_statement.pdf
"""

import os
import random
from datetime import date, datetime, timedelta

from fpdf import FPDF

SEED = 42
NUM_RANDOM_DEBITS = 50
NUM_RANDOM_CREDITS = 4
STATEMENT_START = date(2025, 6, 1)
STATEMENT_DAYS = 30

HEADERS = ["Date", "Narration", "Amount", "Type"]
COL_WIDTHS = [30, 90, 30, 20]

# Fixed rows: the original six sample rows (kept so earlier examples still
# match) plus recurring monthly items.
FIXED_TRANSACTIONS = [
    (date(2025, 6, 3), "UPI-ZOMATO-9876543210", 420.00, "Dr"),
    (date(2025, 6, 4), "UPI-UBER-1234567890", 285.00, "Dr"),
    (date(2025, 6, 5), "AMAZON-ONLINE-PURCHASE", 1299.00, "Dr"),
    (date(2025, 6, 6), "SALARY-ABC-LTD", 65000.00, "Cr"),
    (date(2025, 6, 7), "NETFLIX.COM", 649.00, "Dr"),
    (date(2025, 6, 8), "NEFT-FRIEND-TRANSFER", 2000.00, "Dr"),
    (date(2025, 6, 5), "NEFT-RENT-PAYMENT", 9000.00, "Dr"),
    (date(2025, 6, 10), "SPOTIFY-INDIA", 119.00, "Dr"),
    (date(2025, 6, 12), "UPI-AIRTEL-RECHARGE-9812345670", 299.00, "Dr"),
    (date(2025, 6, 20), "ELECTRICITY-BILL-PAYMENT", 1340.00, "Dr"),
    (date(2025, 6, 30), "INT-PD-SAVINGS-ACCOUNT", 112.50, "Cr"),
]

# Random debits: (category, narration, min amount, max amount, add reference no.)
# The category is NOT printed in the PDF (real statements don't carry one);
# it is kept here so a labels file for ML training can be produced later.
DEBIT_CATALOG = [
    ("Food", "UPI-ZOMATO", 150, 900, True),
    ("Food", "UPI-SWIGGY", 150, 950, True),
    ("Food", "UPI-DOMINOS-PIZZA", 250, 750, True),
    ("Food", "POS-STARBUCKS-COFFEE", 200, 700, False),
    ("Food", "UPI-CHAI-POINT", 60, 300, True),
    ("Groceries", "UPI-BIGBASKET", 300, 2200, True),
    ("Groceries", "UPI-BLINKIT", 120, 1000, True),
    ("Groceries", "POS-RELIANCE-FRESH", 250, 2000, False),
    ("Transport", "UPI-UBER", 80, 500, True),
    ("Transport", "UPI-OLA-CABS", 80, 450, True),
    ("Transport", "UPI-IRCTC-TICKET", 300, 2500, True),
    ("Transport", "UPI-INDIAN-OIL-FUEL", 400, 2000, True),
    ("Shopping", "AMAZON-ONLINE-PURCHASE", 300, 5000, False),
    ("Shopping", "FLIPKART-ONLINE-ORDER", 300, 4000, False),
    ("Shopping", "POS-MYNTRA-FASHION", 500, 3500, False),
    ("Entertainment", "UPI-BOOKMYSHOW", 250, 1000, True),
    ("Entertainment", "UPI-PVR-CINEMAS", 200, 900, True),
    ("Health", "UPI-APOLLO-PHARMACY", 100, 1500, True),
    ("Health", "UPI-PRACTO-CONSULT", 300, 900, True),
    ("Education", "UPI-UDEMY-COURSE", 450, 3000, True),
    ("Cash", "ATM-WDL-CASH", 500, 5000, False),
    ("Transfers", "IMPS-FRIEND-TRANSFER", 200, 3000, True),
    ("Transfers", "NEFT-FAMILY-TRANSFER", 1000, 8000, False),
]

# Random credits: (narration, min amount, max amount, add reference no.)
CREDIT_CATALOG = [
    ("UPI-AMAZON-REFUND", 200, 2500, True),
    ("UPI-FRIEND-REPAYMENT", 300, 3000, True),
    ("NEFT-FREELANCE-PAYMENT", 3000, 12000, False),
    ("UPI-PHONEPE-CASHBACK", 10, 150, True),
]


class BankStatementPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        # Explicit warning that this is not real data
        self.cell(0, 10, "SAMPLE / SYNTHETIC DATA - NOT A REAL BANK STATEMENT",
                  align="C", border=0)
        self.ln(20)

        # Column headings repeat on every page, like a real statement
        self.set_font("helvetica", "B", 10)
        for width, title in zip(COL_WIDTHS, HEADERS):
            self.cell(width, 10, title, border=1, align="C")
        self.ln()
        self.set_font("helvetica", size=10)


def random_amount(rng, low, high):
    """Mostly whole rupees, occasionally with paise."""
    return rng.randint(low, high) + rng.choice([0.00, 0.00, 0.00, 0.50])


def random_date(rng):
    return STATEMENT_START + timedelta(days=rng.randint(0, STATEMENT_DAYS - 1))


def make_narration(rng, name, add_ref):
    """UPI/IMPS-style narrations carry a 10-digit reference number."""
    if add_ref:
        return f"{name}-{rng.randint(10**9, 10**10 - 1)}"
    return name


def build_transactions(rng):
    """Return (date, narration, amount, type) tuples sorted by date."""
    rows = list(FIXED_TRANSACTIONS)

    for _ in range(NUM_RANDOM_DEBITS):
        category, name, low, high, add_ref = rng.choice(DEBIT_CATALOG)
        amount = random_amount(rng, low, high)
        if category == "Cash":
            amount = float(round(amount / 500) * 500)  # ATM cash comes in round notes
        rows.append((random_date(rng), make_narration(rng, name, add_ref), amount, "Dr"))

    for _ in range(NUM_RANDOM_CREDITS):
        name, low, high, add_ref = rng.choice(CREDIT_CATALOG)
        amount = random_amount(rng, low, high)
        rows.append((random_date(rng), make_narration(rng, name, add_ref), amount, "Cr"))

    rows.sort(key=lambda row: row[0])
    return rows


def generate_pdf(output_path="sample_data/sample_bank_statement.pdf"):
    rng = random.Random(SEED)
    transactions = build_transactions(rng)

    pdf = BankStatementPDF()
    # Fixed timestamp: without it fpdf2 stamps the current time, so every run
    # would produce different bytes and Git would show the PDF as modified.
    pdf.set_creation_date(datetime(2025, 6, 30))
    pdf.add_page()
    pdf.set_font("helvetica", size=10)

    for txn_date, narration, amount, txn_type in transactions:
        row = [txn_date.strftime("%d/%m/%Y"), narration, f"{amount:,.2f}", txn_type]
        for i, item in enumerate(row):
            align = "R" if i == 2 else "L"  # Amount right-aligned
            pdf.cell(COL_WIDTHS[i], 10, item, border=1, align=align)
        pdf.ln()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)

    total_dr = sum(amount for _, _, amount, t in transactions if t == "Dr")
    total_cr = sum(amount for _, _, amount, t in transactions if t == "Cr")
    print(f"Success! Synthetic statement generated at: {output_path}")
    print(f"  {len(transactions)} transactions across {pdf.page_no()} pages")
    print(f"  Total debits:  {total_dr:,.2f}")
    print(f"  Total credits: {total_cr:,.2f}")


if __name__ == "__main__":
    generate_pdf()