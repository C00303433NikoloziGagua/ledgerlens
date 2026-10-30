import pytest

from extraction.errors import ExtractionError
from extraction.schema import (
    field_rows,
    load_schema,
    schema_for_openai,
    validate_fields,
)


# format rules are removed, the structure stays
def test_schema_for_openai_removes_format_rules():
    schema = schema_for_openai(load_schema('invoice'))

    assert 'title' not in schema
    assert 'pattern' not in schema['properties']['invoice_date']
    assert schema['properties']['invoice_date']['type'] == ['string', 'null']
    assert schema['additionalProperties'] is False
    assert 'invoice_date' in schema['required']


# a field called description has to survive
def test_schema_for_openai_keeps_fields_named_description():
    schema = schema_for_openai(load_schema('statement'))
    transaction = schema['properties']['transactions']['items']

    assert 'description' in transaction['properties']
    assert 'pattern' not in transaction['properties']['amount']


# fields that break the schema are refused
def test_validate_fields_rejects_bad_fields():
    with pytest.raises(ExtractionError, match='not valid'):
        validate_fields({'supplier_name': 'Missing everything else'}, 'invoice')


# rows follow the schema order
def test_field_rows_follow_schema_order():
    rows = field_rows('invoice', {'total_amount': '147.60'})

    assert rows[0] == ('Supplier name', None)
    assert ('Total amount', '147.60') in rows
    assert len(rows) == 11
