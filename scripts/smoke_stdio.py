"""Full MCP round-trip over STDIO against the real server executable."""

import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

EXE = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "samad-mcp.exe"


async def main() -> None:
    params = StdioServerParameters(command=str(EXE), args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("server:", init.server_info.name, init.server_info.version)
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await session.call_tool("get_weekly_menu", {"week": "current"})
            print("is_error:", result.is_error)
            text = result.content[0].text
            print("menu chars:", len(text))
            print(text[:600])
            if result.is_error:
                sys.exit(1)
    print("STDIO ROUND-TRIP OK")


if __name__ == "__main__":
    anyio.run(main)