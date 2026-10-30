from unittest.mock import patch

import pypdfium2
import pytest
from PIL import Image
from reportlab.pdfgen import canvas

from extraction.errors import ExtractionError
from extraction.text import get_text


# a real PDF with a text layer
def make_text_pdf(path):
    pdf = canvas.Canvas(str(path))
    pdf.setFont('Helvetica', 18)
    pdf.drawString(72, 700, 'Invoice number INV-2026-0412')
    pdf.drawString(72, 660, 'Total amount 147.60')
    pdf.save()


# a picture of a page
def make_page_image(tmp_path):
    source = tmp_path / 'source.pdf'
    make_text_pdf(source)

    pdf = pypdfium2.PdfDocument(source)
    image = pdf[0].render(scale=3).to_pil().convert('RGB')
    pdf.close()

    return image


# text PDFs don't need OCR
def test_text_pdf_is_read_without_ocr(tmp_path):
    path = tmp_path / 'invoice.pdf'
    make_text_pdf(path)

    with patch('extraction.text.read_image') as ocr:
        text = get_text(path, 'pdf')

    assert 'INV-2026-0412' in text
    ocr.assert_not_called()


# scanned PDFs go through OCR
def test_scanned_pdf_is_read_with_ocr(tmp_path):
    path = tmp_path / 'scan.pdf'
    make_page_image(tmp_path).save(path)

    assert 'INV-2026-0412' in get_text(path, 'pdf')


# photos go through OCR
@pytest.mark.parametrize(('name', 'file_type'), [('a.png', 'png'), ('a.jpg', 'jpg')])
def test_image_is_read_with_ocr(tmp_path, name, file_type):
    path = tmp_path / name
    make_page_image(tmp_path).save(path)

    assert 'INV-2026-0412' in get_text(path, file_type)


# a blank page has nothing to read
def test_blank_image_raises_error(tmp_path):
    path = tmp_path / 'blank.png'
    Image.new('RGB', (600, 800), 'white').save(path)

    with pytest.raises(ExtractionError, match='No text'):
        get_text(path, 'png')
