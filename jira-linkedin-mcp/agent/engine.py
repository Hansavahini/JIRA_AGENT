
import asyncio
from contextlib import AsyncExitStack

import ollama

from agent.tool_registry import discover_tools

MODEL = "qwen2.5:0.5b"
MAX_TOOL_ROUNDS = 5

WRITE_TOOLS = {
    "jira__jira_create_project",
    "jira__jira_create_issue",
}


async def main():
    async with AsyncExitStack() as stack:
        sessions, tool_map, ollama_tools = await discover_tools(stack)

        print("Agent ready.")
        print(f"Model: {MODEL}")
        print(f"Available tools: {len(tool_map)}")
        print("Type 'exit' to quit.")

        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in {"exit", "quit"}:
                break

            if not user_input:
                continue

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a Jira assistant. Use available tools when needed. "
                        "Never invent tool results. "
                        "For Jira searches, generate valid JQL. "
                        "For issues updated in the last 30 days, use exactly: "
                        "updated >= -30d ORDER BY updated DESC. "
                        "Never use phrases such as 'updated_after:30' or 'updated after:30'. "
                        "Keep max_results between 1 and 20. "
                        "For project creation, obtain a project name and unique key. "
                        "For issue creation, obtain an existing project key and summary. "
                        "Require approval before every Jira write action. "
                        "Never claim success unless the tool confirms it."
                    ),
                },
                {"role": "user", "content": user_input},
            ]

            for round_number in range(MAX_TOOL_ROUNDS):
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
                if not tool_calls:
                    final_answer = (assistant_message.content or "").strip()

                    if final_answer:
                        print("\nAgent:", final_answer)
                    else:
                        print("\nAgent: The model returned an empty response.")

                    break

                for call in tool_calls:
                    tool_name = call.function.name
                    arguments = call.function.arguments

                    print(f"\nSelected tool: {tool_name}")
                    print("Arguments:", arguments)

                    if tool_name not in tool_map:
                        result_text = "Rejected: unknown tool."
                    elif tool_name in WRITE_TOOLS:
                        print("\nThis action changes real Jira data.")
                        approval = input(
                            "Type YES to approve this action: "
                        ).strip()

                        if approval != "YES":
                            result_text = "Action cancelled by user."
                        else:
                            result_text = await execute_tool(
                                tool_map, tool_name, arguments
                            )
                    else:
                        result_text = await execute_tool(
                            tool_map, tool_name, arguments
                        )

                    print("Tool result:", result_text)
                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": result_text,
                    })
            else:
                print("Stopped: maximum tool-call rounds reached.")


async def execute_tool(tool_map, tool_name, arguments):
    """Execute a discovered MCP tool on its owning server."""
    entry = tool_map[tool_name]

    try:
        result = await entry["session"].call_tool(
            entry["original_name"],
            arguments=arguments,
        )

        text_parts = [
            item.text
            for item in result.content
            if hasattr(item, "text")
        ]
        result_text = "\n".join(text_parts) or "(No text result)"

        if result.isError:
            return f"Tool execution failed: {result_text}"

        return result_text

    except Exception as exc:
        return f"Tool call error: {type(exc).__name__}: {exc}"


if __name__ == "__main__":
    asyncio.run(main())
