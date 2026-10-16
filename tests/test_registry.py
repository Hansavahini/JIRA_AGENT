
import asyncio
from contextlib import AsyncExitStack

from mcp_server.tool_registry import discover_tools


async def main():
    async with AsyncExitStack() as stack:
        sessions, tool_map, ollama_tools = await discover_tools(stack)

        print("\nConnected servers:")
        for name in sessions:
            print(f"- {name}")

        print("\nDiscovered tools:")
        for tool in ollama_tools:
            print(f"- {tool['function']['name']}")

        print(f"\nTotal tools: {len(tool_map)}")


if __name__ == "__main__":
    asyncio.run(main())
