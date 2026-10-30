import pytest
from django.contrib.auth import get_user_model

from documents.models import Document, InvalidStatusChange

Status = Document.Status


# a saved document to test with
@pytest.fixture
def document(db):
    user = get_user_model().objects.create_user(
        username='nika',
        password='test-pass-123',
    )

    return Document.objects.create(
        owner=user,
        file='documents/test.pdf',
        original_name='test.pdf',
        file_type='pdf',
        size=1024,
        sha256='0' * 64,
    )


# allowed changes
@pytest.mark.parametrize(
    'path',
    [
        [Status.PROCESSING, Status.NEEDS_REVIEW],
        [Status.PROCESSING, Status.FAILED],
        [Status.PROCESSING, Status.NEEDS_REVIEW, Status.VALIDATED],
    ],
)
def test_allowed_status_changes(document, path):
    for status in path:
        document.change_status(status)

    document.refresh_from_db()
    assert document.status == path[-1]


# blocked changes
@pytest.mark.parametrize(
    'path',
    [
        [Status.NEEDS_REVIEW],  # skips processing
        [Status.VALIDATED],  # skips everything
        [Status.PROCESSING, Status.UPLOADED],  # goes backwards
        [Status.PROCESSING, Status.FAILED, Status.NEEDS_REVIEW],  # failed is final
    ],
)
def test_blocked_status_changes(document, path):
    *steps, last = path

    for status in steps:
        document.change_status(status)

    with pytest.raises(InvalidStatusChange):
        document.change_status(last)


# failure reason is saved
def test_failed_status_keeps_error_message(document):
    document.change_status(Status.PROCESSING)
    document.change_status(Status.FAILED, error_message='Could not read the file')

    document.refresh_from_db()
    assert document.status == Status.FAILED
    assert document.error_message == 'Could not read the file'
    

# admin pages load
@pytest.mark.parametrize(
    'url',
    [
        '/admin/documents/document/',
        '/admin/extraction/extraction/',
    ],
)
def test_admin_list_pages_load(admin_client, url):
    response = admin_client.get(url)

    assert response.status_code == 200