import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from openai import OpenAIError

from extraction.errors import ExtractionError
from extraction.llm import MAX_TEXT_LENGTH, extract_fields


# what the OpenAI client returns
def fake_response(content, refusal=None):
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


# a fake client, so tests cost nothing and need no key
@pytest.fixture
def create(settings):
    settings.OPENAI_API_KEY = 'test-key'
    settings.OPENAI_MODEL = 'test-model'

    with patch('extraction.llm.OpenAI') as client:
        yield client.return_value.chat.completions.create


# the reply comes back as a dict
def test_extract_fields_returns_parsed_reply(create):
    create.return_value = fake_response(json.dumps({'supplier_name': 'Acme'}))

    assert extract_fields('some text', 'invoice') == {'supplier_name': 'Acme'}


# the request uses strict structured outputs
def test_extract_fields_sends_strict_schema(create):
    create.return_value = fake_response('{}')

    extract_fields('some text', 'invoice')

    request = create.call_args.kwargs
    response_format = request['response_format']['json_schema']

    assert request['model'] == 'test-model'
    assert response_format['strict'] is True
    assert 'pattern' not in response_format['schema']['properties']['invoice_date']


# very long text is cut down
def test_extract_fields_limits_text_length(create):
    create.return_value = fake_response('{}')

    extract_fields('x' * (MAX_TEXT_LENGTH + 100), 'invoice')

    user_message = create.call_args.kwargs['messages'][1]
    assert len(user_message['content']) == MAX_TEXT_LENGTH


# problems become errors the user can read
def test_extract_fields_handles_api_error(create):
    create.side_effect = OpenAIError('rate limited')

    with pytest.raises(ExtractionError, match='request to OpenAI failed'):
        extract_fields('some text', 'invoice')


def test_extract_fields_handles_refusal(create):
    create.return_value = fake_response(None, refusal='No.')

    with pytest.raises(ExtractionError, match='did not return'):
        extract_fields('some text', 'invoice')


def test_extract_fields_needs_api_key(settings):
    settings.OPENAI_API_KEY = ''

    with pytest.raises(ExtractionError, match='OPENAI_API_KEY'):
        extract_fields('some text', 'invoice')
