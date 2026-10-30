from django.db import models


class Extraction(models.Model):
    # the document it belongs to
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='extractions',
    )

    # text and extracted fields
    raw_text = models.TextField(blank=True)
    fields = models.JSONField(default=dict, blank=True)

    # model used and time taken
    model_name = models.CharField(max_length=100, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'Extraction of {self.document} at {self.created:%Y-%m-%d %H:%M}'