# LedgerLens

A web app that extracts and validates data from invoices, receipts and bank statements.

Iteration 1 (v0.1.0) builds the foundations and one working path: log in, upload an invoice, and see its fields extracted and saved.

## What works so far

- Sign up, log in and log out
- Upload one PDF, PNG or JPG at a time, up to 10 MB, with the file's real contents checked
- Document statuses: uploaded, processing, needs review, failed
- Text from PDFs (pdfplumber), and from photos and scans (Tesseract)
- Invoice fields extracted with OpenAI structured outputs
- Dates, amounts and currency normalised in our own code, then checked against the schema
- JSON Schemas for invoices, receipts and bank statements
- Users only ever see their own documents and files
- A labelled set of 18 synthetic invoices and the generator that made them

Not built yet: classification, receipt and statement extraction, batch upload, confidence scores, validation rules, the review screen and CSV export. Every upload is treated as an invoice for now.

## What you need

- Python 3.12
- Docker Desktop, for PostgreSQL
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) on your PATH
- An OpenAI API key

## Setup

Run these from the project folder. The commands are for PowerShell on Windows.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Then fill in `.env`:

- `DJANGO_SECRET_KEY`: any long random string. This command makes one:
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `OPENAI_API_KEY`: your OpenAI key

`.env` is ignored by Git, so your secrets never reach GitHub.

Start the database and create the tables:

```powershell
docker compose up -d
python manage.py migrate
```

## Running the app

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000, sign up and upload an invoice. Sample invoices are in `data/labelled`. An upload can take a few seconds, because extraction runs straight after the upload for now.

To use the admin site, run `python manage.py createsuperuser` and open http://127.0.0.1:8000/admin/.

If the site or the tests hang, the database has probably stopped. Run `docker compose up -d` again.

## Running the tests

```powershell
ruff check .
pytest
```

The tests use a separate test database and never call OpenAI, so they need no API key and cost nothing. Tesseract has to be installed, because the OCR tests read real images. GitHub Actions runs both commands on every push.

## How it works

```
upload -> file checks -> save Document -> read text -> OpenAI -> normalise -> check schema -> save Extraction
```

Any error sends the document to `failed` with the reason shown on its page.

| Folder | What it holds |
|---|---|
| `config/` | Django settings and main URLs |
| `accounts/` | Sign up |
| `documents/` | Upload, document pages, the Document model and its status rules |
| `extraction/` | The pipeline, the Extraction model and the schemas |
| `extraction/schemas/` | JSON Schemas and example records |
| `data/labelled/` | Labelled test documents and `manifest.csv` |
| `scripts/` | Synthetic invoice generator |
| `docs/` | Technology decisions and the dataset review |

## The record format

Records follow the JSON Schemas in `extraction/schemas/`:

- Dates use ISO 8601, e.g. `2026-09-03`
- Amounts are decimal strings, e.g. `"147.60"`, never floats
- Currency is an ISO 4217 code, e.g. `"EUR"`
- Every field is always present, and is `null` when it can't be found
- Account numbers keep only the last 4 digits

## Regenerating the labelled set

```powershell
python scripts/generate_invoices.py --count 18 --output data/labelled
```

The same seed always produces the same documents.
