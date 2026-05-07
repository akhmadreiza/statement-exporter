#!/usr/bin/env python3
import argparse
import glob
import os
import sys

import gspread

from parsers import get_parser, REGISTRY

HEADERS = [
    'Date', 'Time', 'Name', 'Bank', 'Notes',
    'Transaction Type', 'Transaction ID', 'Category',
    'Amount', 'Amount (Raw)',
]


def upload_to_sheets(transactions, spreadsheet_id, sheet_name, creds_path):
    gc = gspread.service_account(filename=creds_path)
    spreadsheet = gc.open_by_key(spreadsheet_id)

    try:
        ws = spreadsheet.worksheet(sheet_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=len(transactions) + 10, cols=len(HEADERS))

    rows = [HEADERS] + [
        [
            tx['date'], tx['time'], tx['name'], tx['bank'],
            tx['notes'], tx['transaction_type'], tx['transaction_id'],
            tx['category'], tx['amount'], tx['amount_raw'],
        ]
        for tx in transactions
    ]
    ws.update(values=rows, range_name='A1')
    return f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}'


def main():
    parser = argparse.ArgumentParser(
        description='Parse bank PDF statements and export to Google Sheets'
    )
    parser.add_argument('--spreadsheet-id', required=True, help='Google Spreadsheet ID')
    parser.add_argument(
        '--credentials', default='credentials.json',
        help='Path to service account JSON (default: credentials.json)',
    )
    parser.add_argument(
        '--files-dir', default='files',
        help='Directory containing PDF files (default: files)',
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(script_dir, args.files_dir)
    creds_path = os.path.join(script_dir, args.credentials)

    if not os.path.isdir(files_dir):
        print(f'Directory not found: {files_dir}')
        sys.exit(1)

    pdf_files = sorted(glob.glob(os.path.join(files_dir, '*.pdf')))
    if not pdf_files:
        print(f'No PDF files found in {files_dir}')
        sys.exit(0)

    if not os.path.exists(creds_path):
        print(f'Credentials file not found: {creds_path}')
        print('See README for Google Sheets API setup instructions.')
        sys.exit(1)

    supported = ', '.join(REGISTRY.keys())

    for pdf_path in pdf_files:
        pdf_name = os.path.basename(pdf_path)
        bank_parser = get_parser(pdf_path)

        if bank_parser is None:
            print(f'Skipping: {pdf_name} (no matching parser — supported prefixes: {supported})')
            continue

        print(f'Processing: {pdf_name}')
        transactions = bank_parser.parse(pdf_path)
        print(f'  Found {len(transactions)} transactions')

        sheet_name = os.path.splitext(pdf_name)[0][:100]
        url = upload_to_sheets(transactions, args.spreadsheet_id, sheet_name, creds_path)
        print(f'  Sheet tab: {sheet_name}')
        print(f'  Spreadsheet: {url}')


if __name__ == '__main__':
    main()
