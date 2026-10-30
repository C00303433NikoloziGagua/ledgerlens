import uuid

from django.conf import settings
from django.db import models


# raised for a blocked status change
class InvalidStatusChange(Exception):
    pass


class Document(models.Model):
    # processing states
    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        PROCESSING = 'processing', 'Processing'
        NEEDS_REVIEW = 'needs_review', 'Needs review'
        VALIDATED = 'validated', 'Validated'
        FAILED = 'failed', 'Failed'

    # document types
    class DocumentType(models.TextChoices):
        INVOICE = 'invoice', 'Invoice'
        RECEIPT = 'receipt', 'Receipt'
        STATEMENT = 'statement', 'Bank statement'
        UNSUPPORTED = 'unsupported', 'Unsupported'

    # allowed status changes
    ALLOWED_TRANSITIONS = {
        Status.UPLOADED: [Status.PROCESSING],
        Status.PROCESSING: [Status.NEEDS_REVIEW, Status.FAILED],
        Status.NEEDS_REVIEW: [Status.VALIDATED],
        Status.VALIDATED: [],
        Status.FAILED: [],
    }

    # random id, hard to guess
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # who uploaded it
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )

    # the file and its details
    file = models.FileField(upload_to='documents/%Y/%m/')
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)

    # pipeline progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    # blank until classified
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        blank=True,
    )

    # errors and timestamps
    error_message = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.original_name

    # move to a new status, block anything not allowed
    def change_status(self, new_status, error_message=''):
        allowed = self.ALLOWED_TRANSITIONS[self.status]

        if new_status not in allowed:
            raise InvalidStatusChange(
                f'Cannot change status from {self.status} to {new_status}'
            )

        self.status = new_status
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated'])