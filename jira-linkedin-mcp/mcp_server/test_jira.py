
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_path = Path(__file__).with_name("server.py")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Discovered MCP tools:")

            for tool in tools.tools:
                print(f"- {tool.name}")

            result = await session.call_tool(
                "jira_search_issues",
                arguments={
                    "jql": "project IS NOT EMPTY ORDER BY updated DESC",
                    "max_results": 5,
                },
            )

            print("\nJira search result:")

            for item in result.content:
                if hasattr(item, "text"):
                    try:
                        print(json.dumps(
                            json.loads(item.text),
                            indent=2,
                        ))
                    except json.JSONDecodeError:
                        print(item.text)

            if result.isError:
                raise RuntimeError(
                    "Jira tool failed. Check the error above."
                )


if __name__ == "__main__":
    asyncio.run(main())
