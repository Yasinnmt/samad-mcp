from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .config import ConfigError, load_settings
from .dates import persian_weekday, week_start
from .samad_client import SamadClient, SamadError

mcp = MCPServer("samad-food", version="0.1.0")

_client: SamadClient | None = None


def _get_client() -> SamadClient:
    global _client
    if _client is None:
        _client = SamadClient(load_settings())
    return _client


def _food_line(item: dict) -> str:
    text = item.get("foodName") or "نامشخص"
    beside = " + ".join(
        ft["besideFoodNames"]
        for ft in item.get("programFoodTypes") or []
        if ft.get("besideFoodNames")
    )
    if beside:
        text = f"{text} + {beside}"
    food_type = item.get("foodTypeTitle")
    if food_type:
        text = f"{text} ({food_type})"
    return text


def format_weekly_menu(self_name: str, payload: dict, start: date) -> str:
    end = start + timedelta(days=6)
    header = f"منوی «{self_name}» — هفتهٔ {start.isoformat()} تا {end.isoformat()}"
    items = [
        item
        for day in payload.get("selfWeekPrograms") or []
        for item in day or []
    ]
    if not items:
        return f"{header}\nبرنامه‌ای برای این هفته ثبت نشده است."
    by_date: dict[str, list] = {}
    for item in items:
        by_date.setdefault(item.get("date", ""), []).append(item)
    lines = [header]
    for i in range(7):
        day = start + timedelta(days=i)
        day_items = by_date.get(day.isoformat(), [])
        lines.append(f"\n{persian_weekday(day)} ({day.isoformat()}):")
        if not day_items:
            lines.append("  برنامه‌ای ثبت نشده")
            continue
        meals: dict[str, list] = {}
        for item in day_items:
            meals.setdefault(item.get("mealTypeName") or "وعده نامشخص", []).append(item)
        for meal_name, meal_items in meals.items():
            lines.append(f"  {meal_name}:")
            for item in meal_items:
                lines.append(f"    - {_food_line(item)}")
    return "\n".join(lines)


def build_weekly_menu(week: str) -> str:
    start = week_start(date.today(), weeks_ahead=0 if week == "current" else 1)
    client = _get_client()
    sections = []
    for self_ in client.list_selfs():
        payload = client.get_programs(self_["id"], start)
        sections.append(format_weekly_menu(self_["name"], payload, start))
    return "\n\n".join(sections)


@mcp.tool()
def get_weekly_menu(week: Literal["current", "next"] = "current") -> str:
    """دریافت منوی غذای دانشگاه از سامانه سماد (فقط خواندنی).

    week="current": منوی این هفته، از شنبه تا جمعه.
    week="next": منوی هفته آینده.
    خروجی: منوی همه سلف‌ها به تفکیک روز و وعده (ناهار/شام) با نام غذاها.
    """
    try:
        return build_weekly_menu(week)
    except (SamadError, ConfigError) as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()