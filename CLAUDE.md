# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip3 install -r requirements.txt
```

`credentials.json` (Google service account key) must be present in the project root and is excluded from git.

## Running the script

```bash
python3 main.py --spreadsheet-id YOUR_SPREADSHEET_ID
```

Optional flags:
- `--credentials` — path to service account JSON (default: `credentials.json`)
- `--files-dir` — directory containing PDFs (default: `files/`)

## Architecture

`main.py` handles CLI, bank detection, and Google Sheets upload. PDF parsing is delegated to bank-specific parsers in `parsers/`.

**Adding a new bank parser:**
1. Create `parsers/<bank>.py` implementing `BankParser.parse(pdf_path) -> list[dict]`
2. Register it in `parsers/__init__.py` under `REGISTRY` with the filename prefix as the key

**Parser routing** is filename-prefix based — a PDF named `bca_may2026.pdf` maps to the `bca` key in `REGISTRY`. Matching is case-insensitive, so `Jenius_*.pdf` and `jenius_*.pdf` both work. PDFs with no matching prefix are skipped with a warning.

**Sheet tab naming** — each PDF produces a tab named after the PDF filename without the extension (max 100 chars). Re-running with the same PDF clears and overwrites the existing tab.

**Parser output contract** — every parser must return a list of dicts with these keys: `date`, `time`, `name`, `bank`, `notes`, `transaction_type`, `transaction_id`, `category`, `amount` (int, negative for outgoing), `amount_raw` (original string).

Each bank parser is intentionally self-contained with its own parsing logic. Do not attempt to share or generalise parsing code across parsers — PDF layouts differ per bank and any shared abstraction will break under the next bank's format.

## Jenius parser notes

The Jenius PDF has embedded text (Qt-generated, not scanned), parsed via `pdfplumber` using word x-coordinates to assign words to columns: `date_time` (x < 130), `details` (130–325), `notes` (325–525), `amount` (≥ 525). The threshold is 525 (not 530) to catch `+`/`-` signs that shift left for large amounts. A lone `+` or `-` in the notes column is merged into `amount_raw` in `parse_block`.
