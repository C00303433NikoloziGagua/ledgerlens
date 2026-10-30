import json  # turns JSON text into Python dicts
from pathlib import Path  # builds file paths that work on Windows and Linux

import jsonschema  # checks data against a JSON Schema
import pytest  # the test framework

# the schemas folder sits next to this file, inside the extraction app
SCHEMA_DIR = Path(__file__).parent / 'schemas'

# the example files live in schemas/examples
EXAMPLES_DIR = SCHEMA_DIR / 'examples'


def load_json(path):
    text = path.read_text(encoding='utf-8')  
    return json.loads(text)  


# finds the right schema for an example from the start of its file name
def schema_for(example):
    doc_type = example.name.split('_')[0]  

    return load_json(SCHEMA_DIR / f'{doc_type}.schema.json')


# every schema file must itself be a correctly written JSON Schema
@pytest.mark.parametrize(
    'schema_file',  
    sorted(SCHEMA_DIR.glob('*.schema.json')),  
    ids=lambda path: path.name,  
)
def test_schema_files_are_valid(schema_file):
    schema = load_json(schema_file) 

    # raises SchemaError if the schema itself is written wrong
    jsonschema.Draft202012Validator.check_schema(schema)


# every example must match the schema for its document type
@pytest.mark.parametrize(
    'example',  
    sorted(EXAMPLES_DIR.glob('*.json')), 
    ids=lambda path: path.name,  
)
def test_examples_match_their_schema(example):
    data = load_json(example)  
    schema = schema_for(example)  

    # raises ValidationError (which fails the test) if any rule is broken
    jsonschema.validate(data, schema)


# reject bad data
def test_invoice_schema_rejects_day_first_date():
    schema = load_json(SCHEMA_DIR / 'invoice.schema.json')  
    invoice = load_json(EXAMPLES_DIR / 'invoice_acme.json')  

    # Irish day-first date instead of ISO 8601
    invoice['invoice_date'] = '03/09/2026'

    # the test only passes if validate() raises 
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invoice, schema)


# payment method can only be one of the allowed values
def test_receipt_schema_rejects_unknown_payment_method():
    schema = load_json(SCHEMA_DIR / 'receipt.schema.json')  
    receipt = load_json(EXAMPLES_DIR / 'receipt_fuel.json') 

    # break it on purpose
    receipt['payment_method'] = 'cheque'

    # the test only passes if validate() raises 
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(receipt, schema)



# only the last 4 digits of an account number may ever be stored
def test_statement_schema_rejects_full_account_number():
    schema = load_json(SCHEMA_DIR / 'statement.schema.json') 
    statement = load_json(EXAMPLES_DIR / 'statement_sept.json')  

    # break it on purpose
    statement['account_last4'] = 'IE29AIBK93115212345678'

    # the test only passes if validate() raises a ValidationError here
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(statement, schema)