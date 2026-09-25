# Spendmind 💸
### Financial Data Pipeline & NLP-Based Transaction Categorization Engine

> *"Your bank shows you transactions. Spendmind shows you patterns."*

---

## 📌 Project Overview

**Spendmind** is an end-to-end financial data pipeline that ingests raw PDF bank statements, extracts and normalizes unstructured transaction data, classifies each transaction into a spending category using an NLP-based classifier, and exposes the structured output through a clean REST API — backed by a persistent SQLite store.

Unlike consumer apps that read SMS alerts (requiring invasive permissions and missing cash, NEFT, and EMI transactions), Spendmind works directly from bank PDF statements — **no account linking, no SMS permissions, and no user credentials required**.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **PDF Extraction** | `pdfplumber` | Extracts structured tables & raw text from multi-page PDFs |
| **Data Processing** | `pandas` | Regex parsing, column normalization, and type casting |
| **NLP / ML Classifier** | `scikit-learn` | TF-IDF + Logistic Regression pipeline trained on transaction narrations |
| **API Layer** | `FastAPI` + `Uvicorn` | Async, type-safe REST API with auto-generated OpenAPI (`/docs`) |
| **Database** | `SQLite` via `SQLAlchemy` | Zero-setup persistent relational storage |
| **Frontend** | Vanilla HTML / CSS / JS | Lightweight Single Page Application (SPA) |
| **Runtime** | Python 3.11+ | End-to-end pipeline in a single language |

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                     USER BROWSER                        │
│         Drag & drop PDF → fetch() → display table       │
└───────────────────┬─────────────────────────────────────┘
                    │ POST /api/upload  (multipart PDF)
                    ▼
┌─────────────────────────────────────────────────────────┐
│                  FASTAPI APPLICATION                     │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  Extraction │ → │    Parser    │ → │ Categorizer │  │
│  │  pdfplumber │   │    pandas    │   │  TF-IDF +   │  │
│  │             │   │    + regex   │   │  LogReg     │  │
│  └─────────────┘   └──────────────┘   └──────┬──────┘  │
│                                              │          │
│  ┌───────────────────────────────────────────▼──────┐   │
│  │              SQLite (via SQLAlchemy)              │   │
│  │      sessions │ transactions │ category_overrides │   │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Pipeline, Step by Step

**Step 1 — PDF Extraction**
`pdfplumber` opens the uploaded PDF and extracts text page by page. For statements with embedded tables (HDFC, Axis), `.extract_table()` returns structured rows directly. For raw text-block statements (SBI, Kotak), `.extract_text()` is used with line-by-line regex fallback.

**Step 2 — Parsing & Normalization**
Raw rows enter a Pandas pipeline. Regex patterns extract date, narration, amount, and transaction type. Amounts are cast to `float`, dates parsed to `datetime`, and narration strings lowercased and stripped of noise characters before classification.

**Step 3 — NLP Categorization**
A `scikit-learn` Pipeline of `TfidfVectorizer` → `LogisticRegression` is trained on labelled Indian transaction narrations across 10 categories. The model is serialized with `joblib` and loaded at startup. Inference on a 100-transaction statement runs in under 50ms.

**Step 4 — Storage**
Parsed and categorized transactions are written to SQLite via SQLAlchemy ORM. Each upload creates a `session` row; each transaction links by `session_id`. Category overrides from the UI are written back as `UPDATE` queries.

**Step 5 — API**
FastAPI exposes typed, documented endpoints. All responses use Pydantic models. Full OpenAPI docs available at `/docs`.

```
POST /api/upload                →  accepts PDF, runs pipeline, returns JSON
POST /api/transactions/update   →  updates a transaction's category
GET  /api/transactions          →  returns all transactions for a session
```

---

## 🗄️ Database Schema

```sql
-- One row per uploaded statement
CREATE TABLE sessions (
    id           TEXT PRIMARY KEY,   -- UUID
    filename     TEXT,
    uploaded_at  DATETIME,
    bank_name    TEXT
);

-- One row per parsed transaction line
CREATE TABLE transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT REFERENCES sessions(id),
    date         DATE,
    description  TEXT,
    amount       REAL,
    type         TEXT,               -- 'debit' | 'credit'
    category     TEXT,
    raw_line     TEXT
);
```

---

## 📂 Project Structure

spendmind/
├── main.py                        # FastAPI app entry point
├── requirements.txt               # App runtime dependencies
├── requirements-dev.txt           # Dev dependencies (e.g., fpdf2)
├── README.md                      # Project documentation
├── .gitignore                     # Git ignore rules
├── spendmind.db                   # SQLite database (auto-created on first run)
│
├── sample_data/
│   └── sample_bank_statement.pdf  # Synthetic PDF for instant recruiter testing
│
├── src/
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── extractor.py           # pdfplumber PDF text & table extraction
│   │   ├── parser.py              # pandas regex parsing & normalization
│   │   └── categorizer.py         # TF-IDF + LogReg classifier
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # FastAPI route handlers
│   │   └── schemas.py             # Pydantic request/response models
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLAlchemy engine & session setup
│   │   └── models.py              # ORM table definitions
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── train.py               # Classifier training script
│   │   ├── predict.py             # Inference wrapper
│   │   └── model.joblib           # Serialized trained model
│   │
│   └── utils/
│       ├── __init__.py
│       └── generate_sample_pdf.py # Dev-only script to generate synthetic PDFs
│
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js

```

## 🚀 Getting Started

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/Missroy1905/spendmind.git
cd spendmind

# Create and activate virtual environment
python -m venv spenvenv

# Windows (PowerShell)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\spenvenv\Scripts\Activate.ps1

# Linux / macOS
source spenvenv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Train the Classifier

```bash
python src/ml/train.py
```

### 4. Start the Server

```bash
uvicorn main:app --reload --port 8080
```

### 5. Open in Browser

```
http://localhost:8080
```

Upload `tests/sample_statement.pdf` to see the full pipeline in action.
API documentation is available at `http://localhost:8080/docs`.

---

## 🔒 Privacy & Data Handling

Uploaded PDFs are processed in-memory and never persisted to disk. Only the extracted transaction records are written to the local SQLite database, which lives entirely on the user's own machine. No data is transmitted to any external server.

For testing, use the sample statement provided in `tests/sample_statement.pdf`.

---

## 📊 Supported Bank Formats

| Bank | Format Type | Parser Method |
|---|---|---|
| HDFC Bank | Embedded table | `extract_table()` |
| Axis Bank | Embedded table | `extract_table()` |
| SBI | Raw text block | `extract_text()` + regex |
| ICICI Bank | Raw text block | `extract_text()` + regex |
| Kotak Mahindra | Raw text block | `extract_text()` + regex |

---

## 🗺️ Roadmap

| Version | Feature |
|---|---|
| `v1.0` | PDF extraction + keyword categorizer + FastAPI + SQLite |
| `v1.1` | TF-IDF + Logistic Regression classifier replaces keyword rules |
| `v1.2` | Multi-month comparison — track category spend across statements |
| `v1.3` | LLM-generated plain-English spending summary per upload |
| `v2.0` | Multi-bank normalization layer + ITR-ready export |

---

## 👩‍💻 Built By

**Somya Roy** · B.Tech CSE (IoT), SKIT Jaipur
[GitHub](https://github.com/Missroy1905) · [LinkedIn](https://www.linkedin.com/in/somya-roy-69bb262aa/) · somyaroy1905@gmail.com

---

*Spendmind v1.0 · Python · FastAPI · SQLite · scikit-learn · pdfplumber*