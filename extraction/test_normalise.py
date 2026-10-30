import pytest

from extraction.normalise import (
    normalise_amount,
    normalise_currency,
    normalise_date,
    normalise_invoice,
)


# printed dates to ISO, always day first
@pytest.mark.parametrize(
    ('printed', 'expected'),
    [
        ('03/09/2026', '2026-09-03'),
        ('3/9/2026', '2026-09-03'),
        ('03/09/26', '2026-09-03'),
        ('03-09-2026', '2026-09-03'),
        ('03.09.2026', '2026-09-03'),
        ('3 September 2026', '2026-09-03'),
        ('3rd September 2026', '2026-09-03'),
        ('3 Sep 2026', '2026-09-03'),
        ('September 3, 2026', '2026-09-03'),
        ('2026-09-03', '2026-09-03'),
        ('31/12/2026', '2026-12-31'),
    ],
)
def test_normalise_date(printed, expected):
    assert normalise_date(printed) == expected


# dates that can't be read
@pytest.mark.parametrize('printed', [None, '', 'unknown', '31/02/2026', '13/13/2026'])
def test_normalise_date_returns_none_when_unreadable(printed):
    assert normalise_date(printed) is None


# printed amounts to 2 decimal strings
@pytest.mark.parametrize(
    ('printed', 'expected'),
    [
        ('147.60', '147.60'),
        ('€147.60', '147.60'),
        ('€ 147.60', '147.60'),
        ('147.60 EUR', '147.60'),
        ('147.6', '147.60'),
        ('147', '147.00'),
        ('1,234.56', '1234.56'),
        ('1.234,56', '1234.56'),
        ('1,234', '1234.00'),
        ('1,234,567.89', '1234567.89'),
        ('-46.10', '-46.10'),
        ('(46.10)', '-46.10'),
        ('46.10-', '-46.10'),
        ('0.00', '0.00'),
        (120, '120.00'),
    ],
)
def test_normalise_amount(printed, expected):
    assert normalise_amount(printed) == expected


# amounts that can't be read
@pytest.mark.parametrize('printed', [None, '', 'n/a', '12-34'])
def test_normalise_amount_returns_none_when_unreadable(printed):
    assert normalise_amount(printed) is None


# symbols and names to ISO codes
@pytest.mark.parametrize(
    ('printed', 'expected'),
    [
        ('€', 'EUR'),
        ('EUR', 'EUR'),
        ('eur', 'EUR'),
        ('Euro', 'EUR'),
        ('£', 'GBP'),
        ('USD', 'USD'),
        (None, None),
        ('euros and cents', None),
    ],
)
def test_normalise_currency(printed, expected):
    assert normalise_currency(printed) == expected


# the spec's Acme invoice, as OpenAI would copy it
def test_normalise_invoice():
    fields = normalise_invoice({
        'supplier_name': '  Acme Office Supplies Ltd ',
        'supplier_vat_number': 'IE1234567T',
        'customer_name': '',
        'invoice_number': 'INV-2026-0412',
        'invoice_date': '03/09/2026',
        'due_date': None,
        'currency': '€',
        'net_amount': '€120.00',
        'vat_amount': '€27.60',
        'total_amount': '€147.60',
        'category': 'Office supplies',
    })

    assert fields == {
        'supplier_name': 'Acme Office Supplies Ltd',
        'supplier_vat_number': 'IE1234567T',
        'customer_name': None,
        'invoice_number': 'INV-2026-0412',
        'invoice_date': '2026-09-03',
        'due_date': None,
        'currency': 'EUR',
        'net_amount': '120.00',
        'vat_amount': '27.60',
        'total_amount': '147.60',
        'category': 'Office supplies',
    }
