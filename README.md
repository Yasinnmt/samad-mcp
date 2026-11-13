# Samad MCP — منوی غذای دانشگاه برای ایجنت‌های هوش مصنوعی

یک MCP Server محلی و فقط-خواندنی که منوی غذای دانشگاه گیلان را از سامانه سماد
(`food.guilan.ac.ir`) می‌گیرد و در اختیار هر کلاینت MCP (Claude Desktop، Claude Code،
Cursor و…) می‌گذارد. بدون دیتابیس، بدون Docker، بدون Playwright.

## قابلیت‌ها

- ابزار `get_weekly_menu` با پارامتر `week`:
  - `"current"` → منوی این هفته (شنبه تا جمعه)
  - `"next"` → منوی هفته آینده
- خروجی فارسی: همه سلف‌ها به تفکیک روز و وعده (ناهار/شام) با نام غذا و مخلفات
- ورود خودکار OAuth2 + تمدید خودکار Session (توکن فقط در حافظه)
- فقط خواندن منو — هیچ رزرو، سفارش یا پرداختی انجام نمی‌شود

## نصب و راه‌اندازی (Windows)

کد را از GitHub کلون کن (یا ZIP دانلود کن) و وارد پوشهٔ پروژه شو:

```bash
cd samad-mcp
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

اگر PyPI مسدود/کند بود، از mirror داخلی استفاده کن:

```bash
.venv\Scripts\python.exe -m pip install -i https://mirror-pypi.runflare.com/simple -e ".[dev]"
```

سپس فایل `.env` را پر کن (از روی `.env.example` ساخته شده):

```
SAMAD_USERNAME=شماره دانشجویی
SAMAD_PASSWORD=رمز عبور سماد
SAMAD_BASE_URL=https://food.guilan.ac.ir
```

**امنیت:** `.env` در `.gitignore` است و هرگز وارد Git نمی‌شود. رمز در تنظیمات
کلاینت‌ها نوشته نمی‌شود؛ سرور خودش آن را از `.env` می‌خواند.

## اتصال به Claude Desktop

فایل `%APPDATA%\Claude\claude_desktop_config.json` را باز کن (یا بساز) و اضافه کن:

```json
{
  "mcpServers": {
    "samad-food": {
      "command": "C:\\path\\to\\samad-mcp\\.venv\\Scripts\\samad-mcp.exe"
    }
  }
}
```

مسیر `command` را با مسیر واقعی پروژه در سیستم خودت جایگزین کن.
اگر فایل از قبل `mcpServers` دارد، فقط ورودی `samad-food` را داخل آن اضافه کن.
بعد Claude Desktop را کامل ببند و دوباره باز کن.

## اتصال به Claude Code

```bash
claude mcp add samad-food "C:\path\to\samad-mcp\.venv\Scripts\samad-mcp.exe"
```

## سایر کلاینت‌های MCP (Cursor و…)

قالب عمومی STDIO — همان `command` بالا در تنظیمات MCP کلاینت:

```json
{
  "mcpServers": {
    "samad-food": {
      "command": "C:\\path\\to\\samad-mcp\\.venv\\Scripts\\samad-mcp.exe",
      "args": []
    }
  }
}
```

## نمونه سؤال‌ها بعد از اتصال

- «منوی این هفته چیه؟»
- «هفته آینده چه غذاهایی داریم؟»
- «غذای روز شنبه چیه؟» (ایجنت از منوی هفتگی، شنبه را جدا می‌کند)

## تست‌ها

```bash
# تست‌های واحد (۱۹ تست — بدون نیاز به اینترنت)
.venv\Scripts\python.exe -m pytest -q

# تست کامل پروتکل MCP روی STDIO با داده واقعی (نیاز به .env و اینترنت)
.venv\Scripts\python.exe scripts\smoke_stdio.py

# تست با MCP Inspector (نیاز به Node.js)
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\samad-mcp.exe" --method tools/list
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\samad-mcp.exe" --method tools/call --tool-name get_weekly_menu --tool-arg week=current
```

## ساختار پروژه

```
src/samad_mcp/
├── config.py        ← خواندن .env
├── dates.py         ← محاسبه شروع هفته (شنبه) + فرمت تاریخ API
├── samad_client.py  ← ورود OAuth2، توکن، تمدید Session، دریافت منو
└── server.py        ← MCP Server (STDIO) + ابزار get_weekly_menu
tests/               ← تست‌های واحد (pytest + respx)
scripts/smoke_stdio.py ← تست end-to-end پروتکل MCP
```

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| نصب pip شکست خورد | از mirror RunFlare استفاده کن (بالا) |
| «نام کاربری یا رمز عبور تنظیم نشده» | `.env` را پر و ذخیره کن |
| «ورود به سامانه سماد ناموفق بود» | شماره دانشجویی/رمز را در `.env` بررسی کن |
| «اتصال به سایت تغذیه برقرار نشد» | اینترنت یا وضعیت سایت را بررسی کن |
| خروجی فارسی به‌هم‌ریخته در ترمینال | `PYTHONUTF8=1` را قبل از دستور بگذار |
| سلفی «برنامه‌ای ثبت نشده» نشان می‌دهد | طبیعی است؛ سایت برای آن سلف/روز برنامه ندارد |