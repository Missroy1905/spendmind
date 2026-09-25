import os
from fpdf import FPDF

class BankStatementPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        # Replaced the unicode em-dash with a standard ASCII hyphen
        self.cell(0, 10, "SAMPLE / SYNTHETIC DATA - NOT A REAL BANK STATEMENT", align="C", border=0)
        self.ln(20)

def generate_pdf():
    pdf = BankStatementPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)

    # Table Header
    headers = ["Date", "Narration", "Amount", "Type"]
    col_widths = [30, 90, 30, 20]
    
    pdf.set_font("helvetica", "B", 10)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align="C")
    pdf.ln()

    # Synthetic Test Transactions
    transactions = [
        ["03/06/2025", "UPI-ZOMATO-9876543210", "420.00", "Dr"],
        ["04/06/2025", "UPI-UBER-1234567890", "285.00", "Dr"],
        ["05/06/2025", "AMAZON-ONLINE-PURCHASE", "1299.00", "Dr"],
        ["06/06/2025", "SALARY-ABC-LTD", "65000.00", "Cr"],
        ["07/06/2025", "NETFLIX.COM", "649.00", "Dr"],
        ["08/06/2025", "NEFT-FRIEND-TRANSFER", "2000.00", "Dr"]
    ]

    pdf.set_font("helvetica", size=10)
    for row in transactions:
        for i, item in enumerate(row):
            align = "R" if i == 2 else "L" # Align amount to right
            pdf.cell(col_widths[i], 10, item, border=1, align=align)
        pdf.ln()

    # Ensure the sample_data directory exists
    os.makedirs("sample_data", exist_ok=True)
    
    # Save the PDF to the sample_data folder
    output_path = "sample_data/sample_bank_statement.pdf"
    pdf.output(output_path)
    print(f"✅ Success! Synthetic statement generated at: {output_path}")

if __name__ == "__main__":
    generate_pdf()