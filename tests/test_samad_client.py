from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from samad_mcp.config import Settings
from samad_mcp.samad_client import LoginError, SamadClient, SamadError

BASE = "https://food.example.test"
CAPTCHA_OK = {"payload": {"image": "fake-base64", "validation": "validation-1"}}
LOGIN_OK = {"access_token": "access-1", "refresh_token": "refresh-1"}
SELFS_OK = {"payload": [{"id": 7, "title": "سلف مرکزی"}]}
PROGRAMS_OK = {"payload": {"programs": []}}


@pytest.fixture
def settings():
    return Settings(username="40212345", password="test-password", base_url=BASE)


def test_menu_fetch_and_token_reuse(settings):
    with respx.mock(base_url=BASE) as mock:
        captcha = mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        token = mock.post("/oauth/token").respond(json=LOGIN_OK)
        selfs = mock.get(path="/rest/reservations/selfs").respond(json=SELFS_OK)
        programs = mock.get(path="/rest/reservations/programs/v2").respond(json=PROGRAMS_OK)

        with SamadClient(settings) as client:
            assert client.list_selfs() == SELFS_OK["payload"]
            assert client.get_programs(7, date(2026, 11, 14)) == PROGRAMS_OK["payload"]
            client.list_selfs()

        assert token.call_count == 1
        assert captcha.call_count == 1
        assert selfs.call_count == 2
        assert selfs.calls.last.request.headers["authorization"] == "Bearer access-1"

        params = programs.calls.last.request.url.params
        assert params["selfId"] == "7"
        assert params["weekStartDate"] == "2026-11-14 00:00:00"

        form = parse_qs(token.calls.last.request.content.decode())
        assert form["username"] == ["40212345"]
        assert form["password"] == ["test-password"]
        assert form["grant_type"] == ["password"]
        assert form["scope"] == ["read write"]
        assert form["validation"] == ["validation-1"]
        assert form["nonce"][0]


def test_expired_token_refresh_and_retry(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        token = mock.post("/oauth/token").mock(
            side_effect=[
                httpx.Response(200, json=LOGIN_OK),
                httpx.Response(
                    200,
                    json={"access_token": "access-2", "refresh_token": "refresh-2"},
                ),
            ]
        )
        selfs = mock.get(path="/rest/reservations/selfs").mock(
            side_effect=[
                httpx.Response(401),
                httpx.Response(200, json=SELFS_OK),
            ]
        )

        with SamadClient(settings) as client:
            assert client.list_selfs() == SELFS_OK["payload"]

        assert token.call_count == 2
        refresh_form = parse_qs(token.calls[1].request.content.decode())
        assert refresh_form["grant_type"] == ["refresh_token"]
        assert refresh_form["refresh_token"] == ["refresh-1"]
        assert selfs.calls.last.request.headers["authorization"] == "Bearer access-2"


def test_refresh_failure_falls_back_to_full_login(settings):
    with respx.mock(base_url=BASE) as mock:
        captcha = mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        token = mock.post("/oauth/token").mock(
            side_effect=[
                httpx.Response(200, json=LOGIN_OK),
                httpx.Response(400, json={"error": "invalid_grant"}),
                httpx.Response(200, json={"access_token": "access-3"}),
            ]
        )
        selfs = mock.get(path="/rest/reservations/selfs").mock(
            side_effect=[
                httpx.Response(401),
                httpx.Response(200, json=SELFS_OK),
            ]
        )

        with SamadClient(settings) as client:
            assert client.list_selfs() == SELFS_OK["payload"]

        assert token.call_count == 3
        assert captcha.call_count == 2
        assert selfs.calls.last.request.headers["authorization"] == "Bearer access-3"


def test_persistent_401_raises_login_error(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        mock.post("/oauth/token").respond(json=LOGIN_OK)
        mock.get(path="/rest/reservations/selfs").respond(status_code=401)

        with SamadClient(settings) as client:
            with pytest.raises(LoginError):
                client.list_selfs()


def test_wrong_credentials_raise_login_error(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        mock.post("/oauth/token").respond(
            status_code=400, json={"error": "invalid_grant"}
        )

        with SamadClient(settings) as client:
            with pytest.raises(LoginError):
                client.list_selfs()


def test_connection_error_is_wrapped(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with SamadClient(settings) as client:
            with pytest.raises(SamadError):
                client.list_selfs()


def test_timeout_error_is_wrapped(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        mock.post("/oauth/token").respond(json=LOGIN_OK)
        mock.get(path="/rest/reservations/selfs").mock(
            side_effect=httpx.ReadTimeout("too slow")
        )

        with SamadClient(settings) as client:
            with pytest.raises(SamadError):
                client.list_selfs()


def test_self_without_program_returns_empty_week(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        mock.post("/oauth/token").respond(json=LOGIN_OK)
        mock.get(path="/rest/reservations/programs/v2").respond(
            status_code=400,
            json={
                "type": "ERROR",
                "messageResource": "SELF_HAS_NO_PROGRAM",
                "messageFa": "هیچ برنامه ی غذایی ای تعریف نشده است.",
            },
        )

        with SamadClient(settings) as client:
            assert client.get_programs(14, date(2026, 11, 14)) == {
                "selfWeekPrograms": []
            }


def test_other_api_error_includes_persian_message(settings):
    with respx.mock(base_url=BASE) as mock:
        mock.post("/rest/captcha").respond(json=CAPTCHA_OK)
        mock.post("/oauth/token").respond(json=LOGIN_OK)
        mock.get(path="/rest/reservations/selfs").respond(
            status_code=500, json={"messageFa": "خطای داخلی سرور"}
        )

        with SamadClient(settings) as client:
            with pytest.raises(SamadError, match="خطای داخلی سرور"):
                client.list_selfs()