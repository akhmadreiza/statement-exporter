import re
from collections import defaultdict

import pdfplumber

from .base import BankParser

COL_DETAILS_START = 130
COL_NOTES_START = 325
COL_AMOUNT_START = 525  # slightly left of AMOUNT header to catch +/- signs for large numbers
Y_TOLERANCE = 3

DATE_RE = re.compile(r'^\d{1,2}\s+\w{3,}\s+\d{4}$')
TIME_RE = re.compile(r'^\d{2}:\d{2}$')


def _group_words_into_rows(words):
    rows = defaultdict(list)
    for word in words:
        y_key = round(word['top'] / Y_TOLERANCE) * Y_TOLERANCE
        rows[y_key].append(word)
    return sorted(rows.items())


def _assign_column(x0):
    if x0 >= COL_AMOUNT_START:
        return 'amount'
    if x0 >= COL_NOTES_START:
        return 'notes'
    if x0 >= COL_DETAILS_START:
        return 'details'
    return 'date_time'


def _row_to_cols(row_words):
    cols = {'date_time': [], 'details': [], 'notes': [], 'amount': []}
    for word in sorted(row_words, key=lambda w: w['x0']):
        cols[_assign_column(word['x0'])].append(word['text'])
    return {k: ' '.join(v) for k, v in cols.items()}


def _parse_amount(raw):
    if not raw:
        return None
    cleaned = raw.replace(',', '').replace(' ', '')
    sign = -1 if '-' in cleaned else 1
    digits = re.sub(r'[^\d]', '', cleaned)
    return sign * int(digits) if digits else None


def _parse_block(block):
    row0 = block[0]
    date = row0['date_time'].strip()
    name = row0['details'].strip()
    notes = row0['notes'].strip()
    amount_raw = row0['amount'].strip()

    time = bank = txn_type = txn_id = category = ''

    for row in block[1:]:
        dt = row['date_time'].strip()
        det = row['details'].strip()
        nte = row['notes'].strip()
        if TIME_RE.match(dt):
            time = dt
            bank = det
            if nte:
                txn_type = nte
        elif '|' in det:
            parts = det.split('|', 1)
            txn_id = parts[0].strip()
            category = parts[1].strip()
        elif nte and not txn_type:
            txn_type = nte

    # A lone sign (+/-) can land in the notes column when the amount is large
    if notes in ('+', '-'):
        amount_raw = f'{notes} {amount_raw}'
        notes = ''

    return {
        'date': date,
        'time': time,
        'name': name,
        'bank': bank,
        'notes': notes,
        'transaction_type': txn_type,
        'transaction_id': txn_id,
        'category': category,
        'amount': _parse_amount(amount_raw),
        'amount_raw': amount_raw,
    }


def _parse_page(page):
    words = page.extract_words()
    sorted_rows = _group_words_into_rows(words)

    # Find sub-header row ("Transaction ID | Category") to skip page headers
    header_y = None
    for y, row_words in sorted_rows:
        if any(w['text'] == 'Category' for w in row_words):
            header_y = y
            break
    if header_y is None:
        return []

    content_rows = [
        (y, _row_to_cols(row_words))
        for y, row_words in sorted_rows
        if y > header_y + 5
    ]
    # Drop footer row
    content_rows = [
        (y, cols) for y, cols in content_rows
        if not cols['details'].startswith('PT Bank SMBC')
    ]

    transactions = []
    current_block = []

    for _, cols in content_rows:
        if DATE_RE.match(cols['date_time'].strip()):
            if current_block:
                transactions.append(_parse_block(current_block))
            current_block = [cols]
        elif current_block:
            current_block.append(cols)

    if current_block:
        transactions.append(_parse_block(current_block))

    return transactions


class JeniusParser(BankParser):
    def parse(self, pdf_path: str) -> list[dict]:
        transactions = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                transactions.extend(_parse_page(page))
        return transactions
