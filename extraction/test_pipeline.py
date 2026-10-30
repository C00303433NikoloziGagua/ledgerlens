from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from documents.models import Document
from extraction.errors import ExtractionError
from extraction.pipeline import run_pipeline

Status = Document.Status

# the Acme invoice as OpenAI would copy it
OPENAI_REPLY = {
    'supplier_name': 'Acme Office Supplies Ltd',
    'supplier_vat_number': 'IE1234567T',
    'customer_name': 'Example Customer Ltd',
    'invoice_number': 'INV-2026-0412',
    'invoice_date': '03/09/2026',
    'due_date': '03/10/2026',
    'currency': '€',
    'net_amount': '€120.00',
    'vat_amount': '€27.60',
    'total_amount': '€147.60',
    'category': 'Office supplies',
}


# a freshly uploaded document
@pytest.fixture
def document(db):
    user = get_user_model().objects.create_user(
        username='alice',
        password='a-strong-pass-123',
    )

    return Document.objects.create(
        owner=user,
        file='documents/invoice.pdf',
        original_name='invoice.pdf',
        file_type='pdf',
        size=1024,
        sha256='0' * 64,
    )


# fake text reading and fake OpenAI
@pytest.fixture
def get_text():
    with patch('extraction.pipeline.get_text', return_value='Invoice text') as mock:
        yield mock


@pytest.fixture
def extract_fields():
    with patch('extraction.pipeline.extract_fields') as mock:
        mock.return_value = OPENAI_REPLY
        yield mock


# the whole path
def test_pipeline_saves_fields_and_stops_at_needs_review(
    document, get_text, extract_fields, settings,
):
    settings.OPENAI_MODEL = 'test-model'

    run_pipeline(document)

    document.refresh_from_db()
    extraction = document.extractions.get()

    assert document.status == Status.NEEDS_REVIEW
    assert document.document_type == Document.DocumentType.INVOICE
    assert extraction.raw_text == 'Invoice text'
    assert extraction.fields['invoice_date'] == '2026-09-03'
    assert extraction.fields['total_amount'] == '147.60'
    assert extraction.fields['currency'] == 'EUR'
    assert extraction.model_name == 'test-model'
    assert extraction.duration_ms is not None


# OpenAI failing keeps the text and records why
def test_pipeline_fails_when_extraction_fails(document, get_text, extract_fields):
    extract_fields.side_effect = ExtractionError('The request to OpenAI failed.')

    run_pipeline(document)

    document.refresh_from_db()
    extraction = document.extractions.get()

    assert document.status == Status.FAILED
    assert document.error_message == 'The request to OpenAI failed.'
    assert extraction.raw_text == 'Invoice text'
    assert extraction.fields == {}


# no readable text
def test_pipeline_fails_when_no_text(document, get_text, extract_fields):
    get_text.side_effect = ExtractionError('No text could be read from this file.')

    run_pipeline(document)

    document.refresh_from_db()

    assert document.status == Status.FAILED
    assert document.error_message == 'No text could be read from this file.'
    extract_fields.assert_not_called()


# bad fields are never saved
def test_pipeline_fails_when_fields_are_invalid(document, get_text, extract_fields):
    bad_fields = {'supplier_name': 'Missing everything else'}

    with patch('extraction.pipeline.normalise_invoice', return_value=bad_fields):
        run_pipeline(document)

    document.refresh_from_db()

    assert document.status == Status.FAILED
    assert 'not valid' in document.error_message
    assert document.extractions.get().fields == {}


# surprises don't crash the page or leak details
def test_pipeline_hides_unexpected_errors(document, get_text, extract_fields):
    get_text.side_effect = RuntimeError('secret internal detail')

    run_pipeline(document)

    document.refresh_from_db()

    assert document.status == Status.FAILED
    assert 'secret internal detail' not in document.error_message
