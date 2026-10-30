import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_admin_login_page_loads(client):
    response = client.get('/admin/login/')
    assert response.status_code == 200


# sign up logs straight in
@pytest.mark.django_db
def test_signup_creates_user_and_logs_in(client, django_user_model):
    response = client.post(
        reverse('signup'),
        {
            'username': 'alice',
            'password1': 'a-strong-pass-123',
            'password2': 'a-strong-pass-123',
        },
    )

    assert response.status_code == 302
    assert django_user_model.objects.filter(username='alice').exists()
    assert client.get(reverse('home')).status_code == 200


# weak passwords are refused
@pytest.mark.django_db
def test_signup_rejects_weak_password(client, django_user_model):
    response = client.post(
        reverse('signup'),
        {'username': 'alice', 'password1': '12345', 'password2': '12345'},
    )

    assert response.status_code == 200
    assert not django_user_model.objects.exists()


# passwords are stored hashed
@pytest.mark.django_db
def test_password_is_hashed(client, django_user_model):
    client.post(
        reverse('signup'),
        {
            'username': 'alice',
            'password1': 'a-strong-pass-123',
            'password2': 'a-strong-pass-123',
        },
    )

    user = django_user_model.objects.get(username='alice')
    assert 'a-strong-pass-123' not in user.password


# log in, then log out
@pytest.mark.django_db
def test_login_and_logout(client, django_user_model):
    django_user_model.objects.create_user(
        username='bob',
        password='a-strong-pass-123',
    )

    response = client.post(
        reverse('login'),
        {'username': 'bob', 'password': 'a-strong-pass-123'},
    )
    assert response.status_code == 302
    assert client.get(reverse('home')).status_code == 200

    client.post(reverse('logout'))
    assert client.get(reverse('home')).status_code == 302
