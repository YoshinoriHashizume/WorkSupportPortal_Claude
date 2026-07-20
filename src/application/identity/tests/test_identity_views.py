import pytest
from django.contrib.auth import get_user_model

from application.identity.domain.value_objects.errors import DesknetAuthError
from application.identity.domain.value_objects.user_info import DesknetUserInfo
from application.identity.infrastructure.desknet.client import desknet_login_api_url
from application.portal.models import UserAccessRequest


def test_desknet_login_api_url_uses_api_endpoint():
    assert (
        desknet_login_api_url("https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi")
        == "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneor.cgi"
    )


@pytest.mark.django_db
def test_desknet_login_creates_user_bound_by_employee_id(client, monkeypatch, settings):
    settings.DESKNETS_LOGIN_URL = "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi"

    def fake_authenticate(login_url, employee_id, password, timeout=10):
        assert login_url == settings.DESKNETS_LOGIN_URL
        assert employee_id == "10001"
        assert password == "secret"
        return DesknetUserInfo(
            employee_id="10001",
            user_id="U001",
            name="山田 太郎",
            default_group_id="G001",
            access_key="access-token",
        )

    monkeypatch.setattr("application.identity.infrastructure.desknet.client.authenticate_desknet_user", fake_authenticate)

    response = client.post("/auth/desknet-login", {"employee_id": "10001", "password": "secret"})

    assert response.status_code == 302
    assert response["Location"] == "/app/access-status"
    user = get_user_model().objects.get(username="10001")
    assert user.last_name == "山田"
    assert user.first_name == "太郎"
    access_request = UserAccessRequest.objects.get(user=user)
    assert access_request.status == UserAccessRequest.Status.PENDING

    session = client.session
    assert session["_auth_user_id"] == str(user.pk)
    assert session["desknet_user_id"] == "U001"
    assert session["desknet_default_group_id"] == "G001"
    assert session["desknet_access_key"] == "access-token"


@pytest.mark.django_db
def test_desknet_login_reuses_existing_employee_user(client, monkeypatch):
    User = get_user_model()
    existing_user = User.objects.create_user(username="10001", first_name="旧名称")

    def fake_authenticate(login_url, employee_id, password, timeout=10):
        return DesknetUserInfo(
            employee_id=employee_id,
            user_id="U001",
            name="山田 太郎",
            default_group_id="G001",
            access_key="access-token",
        )

    monkeypatch.setattr("application.identity.infrastructure.desknet.client.authenticate_desknet_user", fake_authenticate)

    response = client.post("/auth/desknet-login", {"employee_id": "10001", "password": "secret"})

    assert response.status_code == 302
    assert response["Location"] == "/app"
    existing_user.refresh_from_db()
    assert existing_user.last_name == "山田"
    assert existing_user.first_name == "太郎"
    assert User.objects.filter(username="10001").count() == 1


@pytest.mark.django_db
def test_desknet_login_rejects_invalid_credentials(client, monkeypatch):
    def fake_authenticate(login_url, employee_id, password, timeout=10):
        raise DesknetAuthError("社員番号またはパスワードが正しくありません。")

    monkeypatch.setattr("application.identity.infrastructure.desknet.client.authenticate_desknet_user", fake_authenticate)

    response = client.post("/auth/desknet-login", {"employee_id": "10001", "password": "wrong"})

    assert response.status_code == 302
    assert response["Location"] == "/login"
    assert not get_user_model().objects.filter(username="10001").exists()


def test_login_page_has_only_normal_login_form(client, settings):
    settings.AUTH_DEV_MODE = False
    response = client.get("/login")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'action="/auth/desknet-login"' in html
    assert "/auth/dev-login" not in html
    assert "ローカル開発ログイン" not in html


@pytest.mark.django_db
def test_login_page_shows_dev_login_when_auth_dev_mode(client, settings):
    settings.AUTH_DEV_MODE = True
    settings.AUTH_DEV_USERNAME = "10001"
    from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
    from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig

    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )
    response = client.get("/login")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'action="/auth/dev-login"' in html
    assert "ローカル開発ログイン" in html
    assert 'value="10001"' in html
    assert "ローカル開発では画面下部" in html


@pytest.mark.django_db
def test_login_page_hides_dev_login_when_non_bootstrap_admin_exists(client, settings):
    from django.contrib.auth.models import Group

    from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
    from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig
    from application.portal.interfaces.favorites import ADMIN_GROUP_NAME

    settings.AUTH_DEV_MODE = True
    settings.AUTH_DEV_USERNAME = "10001"
    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    User = get_user_model()
    admin_group = Group.objects.get(name=ADMIN_GROUP_NAME)
    other_admin = User.objects.create_user(username="20001", password="unused")
    other_admin.groups.add(admin_group)

    response = client.get("/login")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "/auth/dev-login" not in html
    assert "ローカル開発ログイン" not in html
    assert "desknet's NEO" in html


@pytest.mark.django_db
def test_login_uses_desknet_authentication(client, monkeypatch):
    called = {}

    def fake_authenticate(login_url, employee_id, password, timeout=10):
        called["employee_id"] = employee_id
        called["password"] = password
        return DesknetUserInfo(
            employee_id=employee_id,
            user_id="UDEV",
            name="通常認証ユーザー",
            default_group_id="G001",
            access_key="access-token",
        )

    monkeypatch.setattr("application.identity.infrastructure.desknet.client.authenticate_desknet_user", fake_authenticate)

    response = client.post("/auth/desknet-login", {"employee_id": "10002", "password": "secret"})

    assert response.status_code == 302
    assert response["Location"] == "/app/access-status"
    assert called == {"employee_id": "10002", "password": "secret"}
    user = get_user_model().objects.get(username="10002")
    assert user.last_name == ""
    assert user.first_name == "通常認証ユーザー"


@pytest.mark.django_db
def test_dev_login_endpoint_disabled_when_auth_dev_mode_false(client, settings):
    settings.AUTH_DEV_MODE = False
    response = client.post("/auth/dev-login")

    assert response.status_code == 404


@pytest.mark.django_db
def test_dev_login_endpoint_disabled_when_non_bootstrap_admin_exists(client, settings):
    from django.contrib.auth.models import Group

    from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
    from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig
    from application.portal.interfaces.favorites import ADMIN_GROUP_NAME

    settings.AUTH_DEV_MODE = True
    settings.AUTH_DEV_USERNAME = "10001"
    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    User = get_user_model()
    admin_group = Group.objects.get(name=ADMIN_GROUP_NAME)
    other_admin = User.objects.create_user(username="20001", password="unused")
    other_admin.groups.add(admin_group)

    response = client.post("/auth/dev-login", {"employee_id": "10001", "password": "dev"})

    assert response.status_code == 404


@pytest.mark.django_db
def test_dev_login_works_without_csrf_token_when_auth_dev_mode(client, settings):
    from django.test import Client

    from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
    from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig

    settings.AUTH_DEV_MODE = True
    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    bare_client = Client(enforce_csrf_checks=True)
    response = bare_client.post("/auth/dev-login", {"employee_id": "10001", "password": "dev"})

    assert response.status_code == 302
    assert response["Location"] == "/app"


@pytest.mark.django_db
def test_dev_login_authenticates_bootstrap_user(client, settings):
    from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
    from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig

    settings.AUTH_DEV_MODE = True
    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    response = client.post("/auth/dev-login", {"employee_id": "10001", "password": "dev"})

    assert response.status_code == 302
    assert response["Location"] == "/app"
    session = client.session
    user = get_user_model().objects.get(username="10001")
    assert session["_auth_user_id"] == str(user.pk)
