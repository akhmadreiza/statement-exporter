# statement-exporter

Parses bank e-statement PDFs and writes the data to Google Sheets. Currently supports Jenius. Designed to be extended for other banks.

## Requirements

- Python 3.9+
- A Google Cloud service account with Sheets and Drive APIs enabled

## Setup

### 1. Install dependencies

```
pip3 install -r requirements.txt
```

### 2. Google Sheets API

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project
2. Enable **Google Sheets API** and **Google Drive API**
3. Go to **IAM & Admin → Service Accounts → Create Service Account**
4. Under the service account, go to **Keys → Add Key → Create new key → JSON**
5. Save the downloaded file as `credentials.json` in the project root
6. Share your target Google Sheet with the service account email (Editor access)

## Usage

Rename your PDF with the bank prefix, place it in the `files/` directory, then run:

```
python3 main.py --spreadsheet-id YOUR_SPREADSHEET_ID
```

Each PDF creates a tab in the spreadsheet named after the PDF file. Re-running with the same PDF overwrites the existing tab.

### Supported banks and filename prefixes

| Prefix | Bank |
|--------|------|
| `jenius_` | Jenius (PT Bank SMBC Indonesia) |

Example: `jenius_may2026.pdf`

PDFs with an unrecognised prefix are skipped with a warning.

## Output columns

| Column | Description |
|--------|-------------|
| Date | Transaction date (e.g. `01 May 2026`) |
| Time | Transaction time (e.g. `11:56`) |
| Name | Sender or recipient name |
| Bank | Bank or account number |
| Notes | Transfer notes/description |
| Transaction Type | `Incoming Transfer`, `Outgoing Transfer`, `Bank Charge` |
| Transaction ID | Unique transaction ID |
| Category | `Incoming`, `Transfer to Other Account`, `Cost & Taxes` |
| Amount | Integer amount (negative for outgoing) |
| Amount (Raw) | Original amount string from PDF (e.g. `+ 550,000`) |

## Adding a new bank

1. Create `parsers/<bank>.py` with a class that extends `BankParser`:

```python
from .base import BankParser

class BCAParser(BankParser):
    def parse(self, pdf_path: str) -> list[dict]:
        # extract transactions from pdf_path
        # return list of dicts with keys:
        # date, time, name, bank, notes, transaction_type,
        # transaction_id, category, amount, amount_raw
        ...
```

2. Register it in `parsers/__init__.py`:

```python
from .bca import BCAParser

REGISTRY: dict[str, type] = {
    'jenius': JeniusParser,
    'bca': BCAParser,
}
```

Files named `bca_*.pdf` will now be routed to `BCAParser` automatically.

## Notes

- `credentials.json` and the `files/` directory are excluded from git
- The script supports multiple PDFs in one run — each gets its own sheet tab
