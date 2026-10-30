import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# date formats, always day first
DATE_FORMATS = [
    '%Y-%m-%d',
    '%d/%m/%Y',
    '%d/%m/%y',
    '%d-%m-%Y',
    '%d-%m-%y',
    '%d.%m.%Y',
    '%d.%m.%y',
    '%d %B %Y',
    '%d %b %Y',
    '%B %d %Y',
    '%b %d %Y',
]

# currency symbols and names
CURRENCY_CODES = {
    '€': 'EUR',
    'EURO': 'EUR',
    'EUROS': 'EUR',
    '£': 'GBP',
    '$': 'USD',
}


# any printed date to ISO 8601, None if it can't be read
def normalise_date(value):
    if not value:
        return None

    # 3rd September, 2026 -> 3 September 2026
    text = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', str(value).strip())
    text = text.replace(',', ' ')
    text = ' '.join(text.split())

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue

    return None


# any printed amount to a 2 decimal string, None if it can't be read
def normalise_amount(value):
    if value is None:
        return None

    text = re.sub(r'[^\d,.()-]', '', str(value))
    digits = text.strip('()-')

    if not digits:
        return None

    negative = text.startswith(('(', '-')) or text.endswith('-')

    # the last separator is the decimal point if 1 or 2 digits follow it
    last_separator = max(digits.rfind('.'), digits.rfind(','))
    decimals = len(digits) - last_separator - 1

    if last_separator != -1 and decimals in (1, 2):
        whole = digits[:last_separator]
        fraction = digits[last_separator + 1:]
    else:
        whole = digits
        fraction = '0'

    whole = re.sub(r'[.,]', '', whole) or '0'

    try:
        amount = Decimal(f'{whole}.{fraction}')
    except InvalidOperation:
        return None

    amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return str(-amount if negative else amount)


# symbol or name to an ISO 4217 code
def normalise_currency(value):
    if not value:
        return None

    text = str(value).strip().upper()
    code = CURRENCY_CODES.get(text, text)

    return code if re.fullmatch(r'[A-Z]{3}', code) else None


# empty text becomes None
def clean_text(value):
    if value is None:
        return None

    return str(value).strip() or None


# one invoice from OpenAI to the schema format
def normalise_invoice(fields):
    return {
        'supplier_name': clean_text(fields.get('supplier_name')),
        'supplier_vat_number': clean_text(fields.get('supplier_vat_number')),
        'customer_name': clean_text(fields.get('customer_name')),
        'invoice_number': clean_text(fields.get('invoice_number')),
        'invoice_date': normalise_date(fields.get('invoice_date')),
        'due_date': normalise_date(fields.get('due_date')),
        'currency': normalise_currency(fields.get('currency')),
        'net_amount': normalise_amount(fields.get('net_amount')),
        'vat_amount': normalise_amount(fields.get('vat_amount')),
        'total_amount': normalise_amount(fields.get('total_amount')),
        'category': clean_text(fields.get('category')),
    }
