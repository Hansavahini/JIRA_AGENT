
import asyncio
import json
import ollama
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MODEL = "qwen2.5:0.5b"
MAX_TOOL_ROUNDS = 5


async def main():
    server_path = Path(__file__).with_name("server.py")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover tools from the MCP server.
            mcp_result = await session.list_tools()

            # Convert MCP tool definitions into Ollama's format.
            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in mcp_result.tools
            ]

            print("Agent ready. Type 'exit' to quit.")

            while True:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in {"exit", "quit"}:
                    break

                if not user_input:
                    continue

                messages = [
                    {
                        "role": "user",
                        "content": user_input,
                    }
                ]

                for _ in range(MAX_TOOL_ROUNDS):
                    # Ask Ollama to answer or select a tool.
                    response = ollama.chat(
                        model=MODEL,
                        messages=messages,
                        tools=ollama_tools,
                    )

                    assistant_message = response.message
                    messages.append(
                        assistant_message.model_dump(exclude_none=True)
                    )

                    tool_calls = assistant_message.tool_calls or []

                    # No tool selected: show the final answer.
                    if not tool_calls:
                        print("\nAgent:", assistant_message.content)
                        break

                    # Execute the tools selected by the model.
                    for call in tool_calls:
                        tool_name = call.function.name
                        arguments = call.function.arguments

                        print(f"\nTool selected: {tool_name}")
                        print("Arguments:", arguments)

                        try:
                            result = await session.call_tool(
                                tool_name,
                                arguments=arguments,
                            )

                            result_text = "\n".join(
                                item.text
                                for item in result.content
                                if hasattr(item, "text")
                            )

                            if result.isError:
                                result_text = (
                                    "Tool execution failed: " + result_text
                                )

                        except Exception as exc:
                            result_text = (
                                f"Tool call error: {type(exc).__name__}: {exc}"
                            )

                        print("Tool result:", result_text)

                        # Give the result back to the model.
                        messages.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": result_text,
                            }
                        )
                else:
                    print(
                        "\nAgent stopped after reaching the tool-call "
                        "limit. Try a simpler request."
                    )


if __name__ == "__main__":
    asyncio.run(main())
