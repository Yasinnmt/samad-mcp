from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import httpx

from .config import Settings
from .dates import api_week_param

# Public OAuth client credentials embedded in the samad.app web frontend.
_PUBLIC_CLIENT_AUTH = "Basic c2FtYWQtbW9iaWxlOnNhbWFkLW1vYmlsZS1zZWNyZXQ="


class SamadError(Exception):
    pass


class LoginError(SamadError):
    pass


class NoProgramError(SamadError):
    pass


class SamadClient:
    def __init__(self, settings: Settings, timeout: float = 30.0):
        self._settings = settings
        self._http = httpx.Client(
            base_url=settings.base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
            # System proxy env (e.g. NO_PROXY with IPv6 entries) can break URL parsing.
            trust_env=False,
        )
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SamadClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def list_selfs(self) -> Any:
        return self._payload(self._request("GET", "/rest/reservations/selfs"))

    def get_programs(self, self_id: int, start: date) -> Any:
        try:
            resp = self._request(
                "GET",
                "/rest/reservations/programs/v2",
                params={"selfId": self_id, "weekStartDate": api_week_param(start)},
            )
        except NoProgramError:
            return {"selfWeekPrograms": []}
        return self._payload(resp)

    def _login(self) -> None:
        nonce = str(uuid.uuid4())
        captcha = self._send("POST", "/rest/captcha", json={"nonce": nonce}, auth=False)
        if captcha.status_code >= 400:
            raise SamadError(
                f"دریافت کد اعتبارسنجی ورود ناموفق بود (کد {captcha.status_code})."
            )
        validation = self._payload(captcha).get("validation", "")
        form = {
            "username": self._settings.username,
            "password": self._settings.password,
            "captchaText": "",
            "validation": validation,
            "nonce": nonce,
            "grant_type": "password",
            "scope": "read write",
        }
        resp = self._send(
            "POST",
            "/oauth/token",
            data=form,
            auth=False,
            headers={"Authorization": _PUBLIC_CLIENT_AUTH},
        )
        if resp.status_code != 200:
            raise LoginError(
                "ورود به سامانه سماد ناموفق بود؛ "
                "نام کاربری و رمز عبور را در فایل .env بررسی کن."
            )
        self._store_tokens(resp.json())

    def _refresh(self) -> bool:
        if not self._refresh_token:
            return False
        resp = self._send(
            "POST",
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
            auth=False,
            headers={"Authorization": _PUBLIC_CLIENT_AUTH},
        )
        if resp.status_code != 200:
            return False
        self._store_tokens(resp.json())
        return True

    def _store_tokens(self, payload: dict) -> None:
        self._access_token = payload["access_token"]
        if payload.get("refresh_token"):
            self._refresh_token = payload["refresh_token"]

    def _send(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        headers: dict | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        merged = dict(headers or {})
        if auth:
            merged["Authorization"] = f"Bearer {self._access_token}"
        try:
            return self._http.request(method, path, headers=merged, **kwargs)
        except httpx.HTTPError as exc:
            raise SamadError(
                "اتصال به سایت تغذیه دانشگاه برقرار نشد؛ "
                "اینترنت یا وضعیت سایت را بررسی کن."
            ) from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if self._access_token is None:
            self._login()
        resp = self._send(method, path, **kwargs)
        if resp.status_code == 401:
            if not self._refresh():
                self._login()
            resp = self._send(method, path, **kwargs)
            if resp.status_code == 401:
                raise LoginError(
                    "Session منقضی شد و ورود مجدد هم ناموفق بود؛ "
                    "اطلاعات ورود در فایل .env را بررسی کن."
                )
        if resp.status_code >= 400:
            raise self._api_error(resp)
        return resp

    def _api_error(self, resp: httpx.Response) -> SamadError:
        message = f"پاسخ نامعتبر از سایت تغذیه (کد {resp.status_code})."
        try:
            data = resp.json()
        except ValueError:
            return SamadError(message)
        if not isinstance(data, dict):
            return SamadError(message)
        if data.get("messageResource") == "SELF_HAS_NO_PROGRAM":
            return NoProgramError(data.get("messageFa") or message)
        detail = data.get("messageFa")
        return SamadError(f"{message} {detail}" if detail else message)

    def _payload(self, resp: httpx.Response) -> Any:
        try:
            data = resp.json()
        except ValueError as exc:
            raise SamadError("پاسخ سایت تغذیه قابل خواندن نیست (JSON نامعتبر).") from exc
        if not isinstance(data, dict) or "payload" not in data:
            raise SamadError("ساختار پاسخ سایت تغذیه تغییر کرده است.")
        return data["payload"]