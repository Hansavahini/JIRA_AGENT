
import asyncio
import sys
from pathlib import Path
from contextlib import AsyncExitStack

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.tool_registry import discover_tools
async def main():
    async with AsyncExitStack() as stack:
        sessions, tool_map, ollama_tools = await discover_tools(stack)

        print("Connected servers:", list(sessions.keys()))
        print("\nDiscovered tools:")

        for tool in ollama_tools:
            print("-", tool["function"]["name"])

        print("\nTotal tools:", len(tool_map))


if __name__ == "__main__":
    asyncio.run(main())
