import re

import pdfplumber

from .base import BankParser

Y_TOLERANCE = 3  # tight scan tolerance: within-row words are ~2.5px apart, rows are ~5px apart

COL_DETAILS_START = 140
COL_AMOUNT_START = 405
COL_BALANCE_START = 500

DATE_RE = re.compile(r'^\d{1,2}\s+\w+\s+\d{4}$')
TIME_RE = re.compile(r'^\d{2}:\d{2}$')

FOOTER_MARKERS = frozenset({'berizin', 'blubybcadigital', 'haloblu', 'Simpanan', 'licensed'})


def _group_words_into_rows(words):
    """Group PDF words into visual rows using a scan approach with Y_TOLERANCE."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
    rows = []
    current_words = [sorted_words[0]]
    current_y = sorted_words[0]['top']
    for word in sorted_words[1:]:
        if abs(word['top'] - current_y) <= Y_TOLERANCE:
            current_words.append(word)
        else:
            rows.append((current_y, current_words))
            current_words = [word]
            current_y = word['top']
    rows.append((current_y, current_words))
    return rows


def _assign_column(x0):
    if x0 >= COL_BALANCE_START:
        return 'balance'
    if x0 >= COL_AMOUNT_START:
        return 'amount'
    if x0 >= COL_DETAILS_START:
        return 'details'
    return 'date_time'


def _row_to_cols(row_words):
    cols = {'date_time': [], 'details': [], 'amount': [], 'balance': []}
    for word in sorted(row_words, key=lambda w: w['x0']):
        cols[_assign_column(word['x0'])].append(word['text'])
    return {k: ' '.join(v) for k, v in cols.items()}


def _is_footer(row_words):
    return any(w['text'] in FOOTER_MARKERS or 'blubybcadigital' in w['text'] for w in row_words)


def _parse_amount(raw):
    """Parse Indonesian-format amount string (e.g. '- 2.777.778,00') to int."""
    if not raw:
        return None
    s = raw.replace(' ', '')
    sign = -1 if '-' in s else 1
    s = s.replace('-', '')
    integer_part = s.split(',')[0] if ',' in s else s
    integer_part = integer_part.replace('.', '')
    return sign * int(integer_part) if integer_part.isdigit() else None


def _derive_txn_type(name):
    n = name.lower()
    if n.startswith('dana masuk'):
        return 'Dana Masuk'
    if n.startswith('transfer ke'):
        return 'Transfer ke'
    if n.startswith('autodebit'):
        return 'Autodebit'
    if n.startswith('bunga dari'):
        return 'Bunga dari'
    if n.startswith('bunga'):
        return 'Bunga'
    if n.startswith('pajak'):
        return 'Pajak'
    parts = name.split()
    return ' '.join(parts[:2]) if len(parts) >= 2 else name


def _parse_bank_notes(detail_rows):
    """Extract bank, notes, transaction_id from combined detail rows.

    Blu format: '<bank> - <notes> | <txn_id>' (any part may be absent).
    """
    combined = ' '.join(r for r in detail_rows if r)
    txn_id = ''

    if ' | ' in combined:
        left, txn_id_raw = combined.split(' | ', 1)
        txn_id = txn_id_raw.strip().split()[0] if txn_id_raw.strip() else ''
    else:
        left = combined

    if ' - ' in left:
        bank, notes = left.split(' - ', 1)
        return bank.strip(), notes.strip(), txn_id

    return left.strip(), '', txn_id


def _parse_block(block):
    """Parse one transaction block (list of col-dicts) into a transaction dict."""
    name_parts = [block[0]['details'].strip()]
    amount_raw = ''
    time = ''
    time_found = False
    detail_rows = []

    for row in block:
        if row['amount']:
            amount_raw = row['amount'].strip()
            break

    for row in block[1:]:
        dt = row['date_time'].strip()
        if TIME_RE.match(dt):
            time = dt
            time_found = True
            if row['details']:
                detail_rows.append(row['details'].strip())
        elif time_found:
            if row['details']:
                detail_rows.append(row['details'].strip())
        elif row['details']:
            # Pre-time details: description continuation (e.g. wrapped long name)
            name_parts.append(row['details'].strip())

    name = ' '.join(p for p in name_parts if p)
    bank, notes, txn_id = _parse_bank_notes(detail_rows)

    return {
        'date': block[0]['date_time'].strip(),
        'time': time,
        'name': name,
        'bank': bank,
        'notes': notes,
        'transaction_type': _derive_txn_type(name),
        'transaction_id': txn_id,
        'category': '',
        'amount': _parse_amount(amount_raw),
        'amount_raw': amount_raw,
    }


def _parse_page(page):
    words = page.extract_words()
    sorted_rows = _group_words_into_rows(words)

    content_rows = []
    for _, row_words in sorted_rows:
        if _is_footer(row_words):
            break  # footer always ends the page content
        cols = _row_to_cols(row_words)
        if 'Disclaimer' in cols['date_time']:
            break  # last page has a disclaimer section after transactions
        content_rows.append(cols)

    transactions = []
    current_block = []

    for cols in content_rows:
        dt = cols['date_time'].strip()
        if DATE_RE.match(dt):
            if current_block:
                transactions.append(_parse_block(current_block))
            current_block = [cols]
        elif current_block:
            current_block.append(cols)

    if current_block:
        transactions.append(_parse_block(current_block))

    return transactions


class BluParser(BankParser):
    def parse(self, pdf_path: str) -> list[dict]:
        transactions = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                transactions.extend(_parse_page(page))
        return transactions
