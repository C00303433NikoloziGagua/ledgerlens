"""Generates synthetic invoices with their correct answers as JSON.

Usage: python scripts/generate_invoices.py --count 18 --output data/labelled
"""

import argparse
import csv
import json
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pypdfium2
from faker import Faker
from PIL import Image, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DEFAULT_SEED = 2026
VAT_RATES = [Decimal('0.23'), Decimal('0.135')]
DATE_FORMATS = ['%d/%m/%Y', '%d-%m-%Y', '%d %B %Y']

# what a supplier might sell
CATEGORIES = {
    'Office supplies': ['Printer paper', 'Toner cartridge', 'Desk chair', 'Notebooks'],
    'Software': ['Accounting licence', 'Cloud hosting', 'Support plan'],
    'Utilities': ['Electricity', 'Broadband', 'Water charges'],
    'Professional services': ['Consulting', 'Bookkeeping', 'Legal advice'],
    'Maintenance': ['Boiler service', 'Window cleaning', 'Van repairs'],
}

# each layout words things differently
LAYOUTS = [
    {
        'title': 'INVOICE',
        'number': 'Invoice No.',
        'date': 'Invoice Date',
        'due': 'Due Date',
        'bill_to': 'Bill To',
        'net': 'Net',
        'vat': 'VAT',
        'total': 'Total',
        'header_colour': colors.HexColor('#1f3a5f'),
    },
    {
        'title': 'Tax Invoice',
        'number': 'Invoice Number',
        'date': 'Date',
        'due': 'Payment Due',
        'bill_to': 'Customer',
        'net': 'Subtotal',
        'vat': 'VAT @ {rate}%',
        'total': 'Amount Due',
        'header_colour': colors.HexColor('#2e6b4f'),
    },
    {
        'title': 'Invoice',
        'number': 'Ref',
        'date': 'Issued',
        'due': 'Pay By',
        'bill_to': 'Invoiced To',
        'net': 'Total excl. VAT',
        'vat': 'VAT',
        'total': 'Total incl. VAT',
        'header_colour': colors.HexColor('#5a5a5a'),
    },
]


def money(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# euro amount as printed, e.g. €1,234.56
def printed_amount(value):
    return f'€{value:,.2f}'


# a made-up invoice, returns what gets printed and the correct answers
def build_invoice(rng, fake, number):
    category = rng.choice(list(CATEGORIES))
    rate = rng.choice(VAT_RATES)

    lines = []
    for item in rng.sample(CATEGORIES[category], k=rng.randint(1, 3)):
        quantity = rng.randint(1, 5)
        price = money(Decimal(rng.randint(500, 40000)) / 100)
        lines.append((item, quantity, price, money(price * quantity)))

    net = sum(line[3] for line in lines)
    vat = money(net * rate)
    total = net + vat

    invoice_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))
    has_due_date = rng.random() < 0.8
    has_vat_number = rng.random() < 0.8

    supplier = fake.company()
    customer = fake.company()
    vat_number = f'IE{rng.randint(1000000, 9999999)}{rng.choice("ABCDEFGHKLMNPT")}'
    invoice_number = f'{rng.choice(["INV", "SI", "A"])}-{2026}-{number:04d}'
    due_date = invoice_date + timedelta(days=30)

    printed = {
        'layout': rng.choice(LAYOUTS),
        'date_format': rng.choice(DATE_FORMATS),
        'address': fake.address().replace('\n', ', '),
        'rate': rate,
        'lines': lines,
        'invoice_date': invoice_date,
        'due_date': due_date if has_due_date else None,
    }

    answers = {
        'supplier_name': supplier,
        'supplier_vat_number': vat_number if has_vat_number else None,
        'customer_name': customer,
        'invoice_number': invoice_number,
        'invoice_date': invoice_date.isoformat(),
        'due_date': due_date.isoformat() if has_due_date else None,
        'currency': 'EUR',
        'net_amount': str(net),
        'vat_amount': str(vat),
        'total_amount': str(total),
        'category': category,
    }

    return printed, answers


# draw the invoice as a PDF
def write_pdf(path, printed, answers):
    layout = printed['layout']
    date_format = printed['date_format']
    styles = getSampleStyleSheet()
    story = []

    # supplier and title
    story.append(Paragraph(answers['supplier_name'], styles['Title']))
    story.append(Paragraph(printed['address'], styles['Normal']))

    if answers['supplier_vat_number']:
        vat_line = f'VAT No: {answers["supplier_vat_number"]}'
        story.append(Paragraph(vat_line, styles['Normal']))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(layout['title'], styles['Heading1']))

    # invoice details
    details = [
        [layout['number'], answers['invoice_number']],
        [layout['date'], printed['invoice_date'].strftime(date_format)],
    ]

    if printed['due_date']:
        details.append([layout['due'], printed['due_date'].strftime(date_format)])

    details.append([layout['bill_to'], answers['customer_name']])
    story.append(Table(details, hAlign='LEFT', colWidths=[45 * mm, 90 * mm]))
    story.append(Spacer(1, 8 * mm))

    # line items
    rows = [['Description', 'Qty', 'Unit price', 'Amount']]

    for item, quantity, price, amount in printed['lines']:
        rows.append([item, quantity, printed_amount(price), printed_amount(amount)])

    table = Table(rows, colWidths=[80 * mm, 15 * mm, 35 * mm, 35 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), layout['header_colour']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    # totals
    rate_label = f'{printed["rate"] * 100:g}'
    totals = [
        [layout['net'], printed_amount(Decimal(answers['net_amount']))],
        [
            layout['vat'].format(rate=rate_label),
            printed_amount(Decimal(answers['vat_amount'])),
        ],
        [layout['total'], printed_amount(Decimal(answers['total_amount']))],
    ]

    totals_table = Table(totals, hAlign='RIGHT', colWidths=[45 * mm, 35 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(totals_table)

    SimpleDocTemplate(str(path), pagesize=A4).build(story)


# turn the PDF into a slightly crooked, blurry photo
def write_photo(pdf_path, photo_path, rng):
    pdf = pypdfium2.PdfDocument(pdf_path)
    page = pdf[0].render(scale=2).to_pil().convert('RGB')
    pdf.close()

    page = page.rotate(
        rng.uniform(-1.5, 1.5),
        resample=Image.Resampling.BICUBIC,
        fillcolor=(235, 235, 230),
    )
    page = page.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.8)))
    page.save(photo_path)


# one labelled document, returns its row for the manifest
def generate_one(rng, fake, number, output):
    printed, answers = build_invoice(rng, fake, number)
    stem = f'invoice_{number:04d}'
    pdf_path = output / f'{stem}.pdf'
    write_pdf(pdf_path, printed, answers)

    # every third document is a photo instead of a PDF
    file_name = pdf_path.name
    kind = 'text PDF'

    if number % 3 == 0:
        extension = 'jpg' if number % 2 == 0 else 'png'
        file_name = f'{stem}.{extension}'
        kind = 'photo'
        write_photo(pdf_path, output / file_name, rng)
        pdf_path.unlink()

    labels_path = output / f'{stem}.json'
    labels_path.write_text(json.dumps(answers, indent=2) + '\n', encoding='utf-8')

    return {
        'file': file_name,
        'labels': labels_path.name,
        'document_type': 'invoice',
        'kind': kind,
        'source': 'synthetic (scripts/generate_invoices.py)',
    }


def generate(count, output, seed=DEFAULT_SEED):
    output.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    fake = Faker('en_IE')
    fake.seed_instance(seed)

    rows = [generate_one(rng, fake, number, output) for number in range(1, count + 1)]

    with (output / 'manifest.csv').open('w', newline='', encoding='utf-8') as manifest:
        writer = csv.DictWriter(manifest, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=18)
    parser.add_argument('--output', type=Path, default=Path('data/labelled'))
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    rows = generate(args.count, args.output, args.seed)
    print(f'Wrote {len(rows)} documents to {args.output}')


if __name__ == '__main__':
    main()
