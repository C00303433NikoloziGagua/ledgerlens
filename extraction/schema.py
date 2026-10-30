import json
from pathlib import Path

import jsonschema

from .errors import ExtractionError

SCHEMA_DIR = Path(__file__).parent / 'schemas'

# schema keywords not sent to OpenAI
OPENAI_SKIPPED_KEYS = {'$schema', 'title', 'description', 'pattern'}


def load_schema(doc_type):
    path = SCHEMA_DIR / f'{doc_type}.schema.json'

    return json.loads(path.read_text(encoding='utf-8'))


# the schema without format rules, so OpenAI copies values as printed
def schema_for_openai(schema):
    cleaned = {
        key: value
        for key, value in schema.items()
        if key not in OPENAI_SKIPPED_KEYS
    }

    if 'properties' in cleaned:
        cleaned['properties'] = {
            name: schema_for_openai(field)
            for name, field in cleaned['properties'].items()
        }

    if 'items' in cleaned:
        cleaned['items'] = schema_for_openai(cleaned['items'])

    return cleaned


# final check before saving
def validate_fields(fields, doc_type):
    try:
        jsonschema.validate(fields, load_schema(doc_type))
    except jsonschema.ValidationError as error:
        message = f'Extracted fields are not valid: {error.message}'
        raise ExtractionError(message) from error


# (label, value) pairs in schema order for the document page
def field_rows(doc_type, fields):
    rows = []

    for name in load_schema(doc_type)['properties']:
        label = name.replace('_', ' ').capitalize()
        label = label.replace('vat', 'VAT').replace('Vat', 'VAT')
        rows.append((label, fields.get(name)))

    return rows
