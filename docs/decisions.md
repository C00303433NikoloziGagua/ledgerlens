# Technology decisions

## Django
- Built-in user accounts: hashed passwords and protection against forged form submissions
- Database models with migrations, plus an admin site for inspecting data
- Python, the same language as the OCR and AI libraries
- Considered: Flask/FastAPI , a separate React front end (possible later)

## PostgreSQL
- Relational database, which the spec requires
- JSON column type for the extracted fields; an exact decimal type for money
- Same database locally and in CI, using Docker
- Considered: SQLite (fine for development, but weaker JSON support and handling of many users at once)

## pdfplumber
- Reads the text already inside digital PDFs, so no OCR is needed and the text is exact
- Keeps each word's position on the page, which helps later with highlighting values on the review screen
- Scanned PDFs: pages turned into images with pypdfium2, then read with Tesseract
- Considered: PyMuPDF (AGPL licence), pypdf (less information about positions)

## Tesseract
- Free and runs locally, so documents don't leave the machine
- Gives a confidence score for each word, which feeds the field confidence scores
- Weak on photographed receipts
- Planned: compare with AWS Textract and the OpenAI vision model in iteration 2

## OpenAI
- Structured outputs make the reply match the JSON Schema
- Handles invoice layouts that vary too much for fixed rules
- A small model during development keeps costs low
- The AI step is kept in its own module, so the provider can be swapped (e.g. AWS Bedrock)

## JSON Schema
- One definition used three ways: to constrain the OpenAI reply, to check it, and to document the record format
- A standard format that doesn't depend on any one language, with a Python library for tests

## Normalising in our own code
- OpenAI is asked to copy dates and amounts exactly as printed, and our code turns them into the schema format
- The schema's format rules are removed from what OpenAI receives, then applied to the final result
- Day-first dates are handled by tested code instead of relying on the model to get them right every time
- Considered: having OpenAI return ISO dates directly (less code, but a wrong day/month swap would be hard to spot)

## gpt-4o-mini
- Cheap and fast, and it handled the labelled set well
- The model is a setting (`OPENAI_MODEL`), so it can be changed without touching the code

## Running extraction straight after upload
- Simple to build and test for iteration 1, at the cost of the page waiting a few seconds
- Moves to a background worker (Celery or RQ) in iteration 2, when batch upload arrives