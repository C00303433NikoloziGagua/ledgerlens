import pytest


# uploads go to a temp folder during tests
@pytest.fixture(autouse=True)
def temp_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


# a browser logged in as alice
@pytest.fixture
def alice_client(client, django_user_model):
    alice = django_user_model.objects.create_user(
        username='alice',
        password='a-strong-pass-123',
    )

    client.force_login(alice)
    client.user = alice
    return client
