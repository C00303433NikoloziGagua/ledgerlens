import csv
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import jsonschema
import pdfplumber
import pytest

from extraction.schema import load_schema

ROOT = Path(__file__).resolve().parent.parent
LABELLED_DIR = ROOT / 'data' / 'labelled'


def load_manifest(folder):
    with (folder / 'manifest.csv').open(encoding='utf-8') as manifest:
        return list(csv.DictReader(manifest))


# scripts/ isn't a package, so load the generator from its path
def load_generator():
    path = ROOT / 'scripts' / 'generate_invoices.py'
    spec = importlib.util.spec_from_file_location('generate_invoices', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


# the set is big enough and every file exists
def test_labelled_set_is_complete():
    rows = load_manifest(LABELLED_DIR)

    assert 15 <= len(rows) <= 20

    for row in rows:
        assert (LABELLED_DIR / row['file']).exists()
        assert (LABELLED_DIR / row['labels']).exists()
        assert row['source']


# every label matches the schema
@pytest.mark.parametrize(
    'row',
    load_manifest(LABELLED_DIR),
    ids=lambda row: row['file'],
)
def test_labels_match_schema(row):
    labels = json.loads((LABELLED_DIR / row['labels']).read_text(encoding='utf-8'))

    jsonschema.validate(labels, load_schema(row['document_type']))


# the numbers on every label add up
@pytest.mark.parametrize(
    'row',
    load_manifest(LABELLED_DIR),
    ids=lambda row: row['file'],
)
def test_labels_add_up(row):
    labels = json.loads((LABELLED_DIR / row['labels']).read_text(encoding='utf-8'))

    total = Decimal(labels['net_amount']) + Decimal(labels['vat_amount'])
    assert total == Decimal(labels['total_amount'])


# the generator prints what its answers say
def test_generator_writes_matching_pdf_and_labels(tmp_path):
    generator = load_generator()

    rows = generator.generate(2, tmp_path, seed=1)

    labels = json.loads((tmp_path / rows[0]['labels']).read_text(encoding='utf-8'))

    with pdfplumber.open(tmp_path / rows[0]['file']) as pdf:
        text = pdf.pages[0].extract_text()

    assert labels['invoice_number'] in text
    assert labels['supplier_name'] in text
    assert f'€{Decimal(labels["total_amount"]):,.2f}' in text


# the same seed gives the same documents
def test_generator_is_repeatable(tmp_path):
    generator = load_generator()

    first = tmp_path / 'first'
    second = tmp_path / 'second'
    generator.generate(2, first, seed=1)
    generator.generate(2, second, seed=1)

    first_labels = (first / 'invoice_0001.json').read_text(encoding='utf-8')
    second_labels = (second / 'invoice_0001.json').read_text(encoding='utf-8')

    assert first_labels == second_labels
