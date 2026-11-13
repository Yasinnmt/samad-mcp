from datetime import date, timedelta

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from samad_mcp import server
from samad_mcp.dates import week_start
from samad_mcp.samad_client import SamadError


def make_payload(start: date) -> dict:
    return {
        "selfWeekPrograms": [
            [
                {
                    "date": start.isoformat(),
                    "mealTypeName": "ناهار",
                    "foodName": "چلو خورشت قرمه سبزی",
                    "foodTypeTitle": "پرهزینه 1",
                    "programFoodTypes": [{"besideFoodNames": ""}],
                },
                {
                    "date": start.isoformat(),
                    "mealTypeName": "ناهار",
                    "foodName": "عدس پلو با کشمش",
                    "foodTypeTitle": "پرهزینه 2",
                    "programFoodTypes": [{"besideFoodNames": "ماست"}],
                },
            ],
            [],
            [],
            [],
            [],
            [],
            [
                {
                    "date": (start + timedelta(days=6)).isoformat(),
                    "mealTypeName": "شام",
                    "foodName": "کتلت",
                    "foodTypeTitle": "کم‌هزینه",
                    "programFoodTypes": [],
                }
            ],
        ]
    }


def test_format_weekly_menu():
    start = date(2026, 11, 7)
    text = server.format_weekly_menu("سلف مرکزی", make_payload(start), start)
    assert "سلف مرکزی" in text
    assert "شنبه (2026-11-07)" in text
    assert "ناهار:" in text
    assert "چلو خورشت قرمه سبزی (پرهزینه 1)" in text
    assert "عدس پلو با کشمش + ماست (پرهزینه 2)" in text
    assert "جمعه (2026-11-13)" in text
    assert "کتلت" in text
    assert text.count("برنامه‌ای ثبت نشده") == 5


def test_format_empty_week():
    start = date(2026, 11, 7)
    text = server.format_weekly_menu("سلف مرکزی", {"selfWeekPrograms": []}, start)
    assert "برنامه‌ای برای این هفته ثبت نشده است." in text


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def list_selfs(self):
        return [{"id": 1, "name": "سلف مرکزی"}]

    def get_programs(self, self_id, start):
        self.calls.append((self_id, start))
        return self.payload


@pytest.mark.anyio
async def test_get_weekly_menu_tool_current(monkeypatch):
    start = week_start(date.today())
    fake = FakeClient(make_payload(start))
    monkeypatch.setattr(server, "_get_client", lambda: fake)

    result = await server.mcp.call_tool("get_weekly_menu", {"week": "current"})

    assert not result.is_error
    assert "چلو خورشت قرمه سبزی" in result.content[0].text
    assert fake.calls == [(1, start)]


@pytest.mark.anyio
async def test_get_weekly_menu_tool_next(monkeypatch):
    start = week_start(date.today(), weeks_ahead=1)
    fake = FakeClient(make_payload(start))
    monkeypatch.setattr(server, "_get_client", lambda: fake)

    result = await server.mcp.call_tool("get_weekly_menu", {"week": "next"})

    assert not result.is_error
    assert fake.calls == [(1, start)]


@pytest.mark.anyio
async def test_tool_reports_connection_error(monkeypatch):
    class BrokenClient:
        def list_selfs(self):
            raise SamadError("اتصال به سایت تغذیه دانشگاه برقرار نشد.")

    monkeypatch.setattr(server, "_get_client", lambda: BrokenClient())

    with pytest.raises(ToolError, match="اتصال"):
        await server.mcp.call_tool("get_weekly_menu", {"week": "current"})