
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_path = Path(__file__).with_name("server.py")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("MCP connection initialized.")

            tools = await session.list_tools()
            print("Discovered tools:")

            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            result = await session.call_tool(
                "multiply",
                arguments={"a": 12, "b": 8},
            )

            print("Tool result:")
            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)

            if result.isError:
                raise RuntimeError("MCP tool call failed")


if __name__ == "__main__":
    asyncio.run(main())
