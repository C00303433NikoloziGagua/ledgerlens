import hashlib
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from documents.models import Document
from documents.uploads import MAX_UPLOAD_SIZE
from extraction.models import Extraction

PDF_BYTES = b'%PDF-1.7 fake invoice'
PNG_BYTES = b'\x89PNG\r\n\x1a\n fake image'


# skip the real pipeline in these tests
@pytest.fixture
def pipeline():
    with patch('documents.views.run_pipeline') as mock_pipeline:
        yield mock_pipeline


# a document owned by bob
@pytest.fixture
def bobs_document(django_user_model):
    bob = django_user_model.objects.create_user(
        username='bob',
        password='a-strong-pass-123',
    )

    return Document.objects.create(
        owner=bob,
        file=SimpleUploadedFile('bob.pdf', PDF_BYTES),
        original_name='bob.pdf',
        file_type='pdf',
        size=len(PDF_BYTES),
        sha256=hashlib.sha256(PDF_BYTES).hexdigest(),
    )


def post_file(client, name, contents):
    return client.post(
        reverse('upload'),
        {'file': SimpleUploadedFile(name, contents)},
    )


# valid uploads
@pytest.mark.parametrize(
    ('name', 'contents', 'file_type'),
    [
        ('invoice.pdf', PDF_BYTES, 'pdf'),
        ('invoice.PNG', PNG_BYTES, 'png'),
        ('photo.jpeg', b'\xff\xd8\xff fake photo', 'jpg'),
    ],
)
def test_valid_upload_is_saved_and_processed(
    alice_client, pipeline, name, contents, file_type,
):
    response = post_file(alice_client, name, contents)

    document = Document.objects.get()
    assert response.status_code == 302
    assert response.url == reverse('document_detail', args=[document.pk])
    assert document.owner == alice_client.user
    assert document.original_name == name
    assert document.file_type == file_type
    assert document.size == len(contents)
    assert document.sha256 == hashlib.sha256(contents).hexdigest()
    pipeline.assert_called_once_with(document)


# rejected uploads
@pytest.mark.parametrize(
    ('name', 'contents', 'message'),
    [
        ('notes.txt', b'hello', 'Only PDF, PNG and JPG'),  # wrong type
        ('fake.pdf', b'just some text', 'match its type'),  # renamed file
        ('fake.png', PDF_BYTES, 'match its type'),  # wrong extension
        ('big.pdf', b'%PDF-' + b'0' * MAX_UPLOAD_SIZE, 'bigger than 10 MB'),
    ],
    ids=['wrong-type', 'renamed-file', 'wrong-extension', 'too-big'],
)
def test_bad_upload_is_rejected(alice_client, pipeline, name, contents, message):
    response = post_file(alice_client, name, contents)

    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Document.objects.exists()
    pipeline.assert_not_called()


# pages need login
@pytest.mark.django_db
@pytest.mark.parametrize('url_name', ['home', 'upload'])
def test_pages_redirect_when_logged_out(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code == 302
    assert response.url.startswith(reverse('login'))


# the list only shows your own documents
def test_home_lists_only_own_documents(alice_client, pipeline, bobs_document):
    post_file(alice_client, 'mine.pdf', PDF_BYTES)

    page = alice_client.get(reverse('home')).content.decode()

    assert 'mine.pdf' in page
    assert 'bob.pdf' not in page


# other people's documents look like they don't exist
@pytest.mark.parametrize('url_name', ['document_detail', 'document_file'])
def test_other_users_document_returns_404(alice_client, bobs_document, url_name):
    response = alice_client.get(reverse(url_name, args=[bobs_document.pk]))

    assert response.status_code == 404


# the owner can open the original file
def test_owner_can_open_file(client, bobs_document):
    client.force_login(bobs_document.owner)

    response = client.get(reverse('document_file', args=[bobs_document.pk]))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert b''.join(response.streaming_content) == PDF_BYTES


# extracted fields and raw text on the page
def test_detail_shows_extracted_fields(client, bobs_document):
    bobs_document.document_type = Document.DocumentType.INVOICE
    bobs_document.save()

    Extraction.objects.create(
        document=bobs_document,
        raw_text='Invoice text',
        fields={'supplier_name': 'Acme Office Supplies Ltd', 'net_amount': '120.00'},
        model_name='test-model',
    )

    client.force_login(bobs_document.owner)
    page = client.get(reverse('document_detail', args=[bobs_document.pk]))

    assert page.status_code == 200
    assert 'Supplier name' in page.content.decode()
    assert 'Acme Office Supplies Ltd' in page.content.decode()
    assert 'Invoice text' in page.content.decode()


# failed documents show the reason
def test_detail_shows_error_message(client, bobs_document):
    bobs_document.change_status(Document.Status.PROCESSING)
    bobs_document.change_status(
        Document.Status.FAILED,
        error_message='No text could be read from this file.',
    )

    client.force_login(bobs_document.owner)
    page = client.get(reverse('document_detail', args=[bobs_document.pk]))

    assert 'No text could be read from this file.' in page.content.decode()
