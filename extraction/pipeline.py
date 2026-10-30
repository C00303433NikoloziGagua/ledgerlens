import logging
import time

from django.conf import settings

from documents.models import Document

from .errors import ExtractionError
from .llm import extract_fields
from .models import Extraction
from .normalise import normalise_invoice
from .schema import validate_fields
from .text import get_text

logger = logging.getLogger(__name__)

Status = Document.Status


# upload -> text -> fields -> normalise -> check -> save
def run_pipeline(document):
    # only invoices for now, classification comes in iteration 2
    doc_type = Document.DocumentType.INVOICE
    document.document_type = doc_type
    document.save(update_fields=['document_type', 'updated'])

    document.change_status(Status.PROCESSING)
    extraction = Extraction.objects.create(document=document)
    started = time.monotonic()

    try:
        extraction.raw_text = get_text(document.file.path, document.file_type)
        extraction.save(update_fields=['raw_text'])

        fields = normalise_invoice(extract_fields(extraction.raw_text, doc_type))
        validate_fields(fields, doc_type)
    except ExtractionError as error:
        document.change_status(Status.FAILED, error_message=str(error))
        return
    except Exception:
        logger.exception('Processing failed for document %s', document.pk)
        document.change_status(
            Status.FAILED,
            error_message='Something went wrong while reading this file.',
        )
        return

    extraction.fields = fields
    extraction.model_name = settings.OPENAI_MODEL
    extraction.duration_ms = int((time.monotonic() - started) * 1000)
    extraction.save(update_fields=['fields', 'model_name', 'duration_ms'])

    document.change_status(Status.NEEDS_REVIEW)
