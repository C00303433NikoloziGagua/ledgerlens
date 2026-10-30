import pdfplumber
import pypdfium2
import pytesseract
from django.conf import settings
from PIL import Image, ImageOps

from .errors import ExtractionError

# fewer characters than this means a scanned PDF
MIN_PDF_TEXT_LENGTH = 20

# OCR limits
MAX_OCR_PAGES = 10
OCR_SCALE = 300 / 72


# text from a PDF or an image
def get_text(path, file_type):
    if file_type == 'pdf':
        text = read_pdf_text(path)

        if len(text) < MIN_PDF_TEXT_LENGTH:
            text = read_scanned_pdf(path)
    else:
        with Image.open(path) as image:
            text = read_image(ImageOps.exif_transpose(image))

    text = text.strip()

    if not text:
        raise ExtractionError('No text could be read from this file.')

    return text


# PDFs that contain real text
def read_pdf_text(path):
    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text() or '' for page in pdf.pages]

    return '\n'.join(pages).strip()


# PDFs that are just pictures of pages
def read_scanned_pdf(path):
    pdf = pypdfium2.PdfDocument(path)

    try:
        pages = []

        for index in range(min(len(pdf), MAX_OCR_PAGES)):
            image = pdf[index].render(scale=OCR_SCALE).to_pil()
            pages.append(read_image(image))
    finally:
        pdf.close()

    return '\n'.join(pages)


# the OCR engine, swap it here
def read_image(image):
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    return pytesseract.image_to_string(image.convert('L'), lang='eng')
