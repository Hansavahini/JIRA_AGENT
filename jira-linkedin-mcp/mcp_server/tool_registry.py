
import json
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "tools.json"


def load_server_config():
    """Load enabled MCP server configurations."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    servers = config.get("servers", [])
    names = [server["name"] for server in servers]

    if len(names) != len(set(names)):
        raise ValueError("MCP server names must be unique.")

    return [server for server in servers if server.get("enabled", False)]


async def discover_tools(exit_stack):
    """Connect to configured servers and discover their tools."""
    sessions = {}
    tool_map = {}
    ollama_tools = []

    for server in load_server_config():
        name = server["name"]

        if server.get("transport") != "stdio":
            raise ValueError(
                f"Unsupported transport for server '{name}'."
            )

        params = StdioServerParameters(
            command=server["command"],
            args=server.get("args", []),
            cwd=str(PROJECT_ROOT),
        )

        read, write = await exit_stack.enter_async_context(
            stdio_client(params)
        )

        session = await exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await session.initialize()

        sessions[name] = session
        result = await session.list_tools()

        for tool in result.tools:
            # Namespace tool names to prevent collisions between servers.
            public_name = f"{name}__{tool.name}"

            if public_name in tool_map:
                raise ValueError(f"Duplicate tool name: {public_name}")

            tool_map[public_name] = {
                "server_name": name,
                "original_name": tool.name,
                "session": session,
            }

            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": public_name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            })

    return sessions, tool_map, ollama_tools
