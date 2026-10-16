
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_server.jira.tools.projects import (
    jira_list_projects,
    jira_create_project,
)
from mcp_server.jira.tools.issues import jira_create_issue
from mcp_server.jira.tools.search import jira_search_issues

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

mcp = FastMCP("jira-linkedin-tools")


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b


mcp.tool()(jira_list_projects)
mcp.tool()(jira_search_issues)
mcp.tool()(jira_create_project)
mcp.tool()(jira_create_issue)


if __name__ == "__main__":
    mcp.run(transport="stdio")
