
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

mcp = FastMCP("jira-linkedin-tools")


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b


@mcp.tool()
async def jira_search_issues(
    jql: str,
    max_results: int = 5,
) -> str:
    """Search Jira issues using valid Jira Query Language (JQL).

    IMPORTANT: Always use valid JQL syntax.

    Examples:
    - Recent updates:
      updated >= -30d ORDER BY updated DESC
    - Recently created:
      created >= -30d ORDER BY created DESC
    - All issues in a project:
      project = "PROJECTKEY" ORDER BY updated DESC
    - Unassigned issues:
      assignee IS EMPTY ORDER BY created DESC

    Args:
        jql: A complete, valid Jira Query Language expression.
        max_results: Maximum number of issues, from 1 to 20.
    """
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    if not all([base_url, email, token]):
        raise ValueError(
            "Configure JIRA_BASE_URL, JIRA_EMAIL and "
            "JIRA_API_TOKEN in the project .env file."
        )

    if not base_url.startswith("https://"):
        raise ValueError("JIRA_BASE_URL must use HTTPS.")

    if not 1 <= max_results <= 20:
        raise ValueError("max_results must be between 1 and 20.")

    url = f"{base_url}/rest/api/3/search/jql"

    params = [
        ("jql", jql),
        ("maxResults", max_results),
        ("fields", "summary"),
        ("fields", "status"),
        ("fields", "assignee"),
        ("fields", "issuetype"),
    ]

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            url,
            params=params,
            auth=(email, token),
            headers={"Accept": "application/json"},
        )

    if response.is_error:
        raise ValueError(
            f"Jira API returned HTTP {response.status_code}: "
            f"{response.text[:1500]}"
        )

    data = response.json()
    issues = []

    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        status = fields.get("status")
        issue_type = fields.get("issuetype")

        issues.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "status": status.get("name") if status else None,
            "assignee": (
                assignee.get("displayName") if assignee else "Unassigned"
            ),
            "issue_type": (
                issue_type.get("name") if issue_type else None
            ),
        })

    return json.dumps({
        "total_returned": len(issues),
        "issues": issues,
    })


@mcp.tool()
async def jira_create_project(
    name: str,
    key: str,
    description: str = "",
) -> str:
    """Create a real Jira Software project.

    Args:
        name: Human-readable project name.
        key: Unique project key, such as AIRESEARCH.
        description: Optional project description.
    """
    import re

    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    if not all([base_url, email, token]):
        raise ValueError("Jira credentials are not configured.")

    key = key.upper().strip()

    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", key):
        raise ValueError(
            "Project key must start with a letter and contain "
            "2 to 10 uppercase letters or digits."
        )

    payload = {
        "name": name.strip(),
        "key": key,
        "description": description,
        "projectTypeKey": "software",
        "projectTemplateKey": (
            "com.pyxis.greenhopper.jira:gh-scrum-template"
        ),
    }

    url = f"{base_url}/rest/api/3/project"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            auth=(email, token),
            headers={"Accept": "application/json"},
            json=payload,
        )

    if response.is_error:
        raise ValueError(
            f"Jira project creation failed "
            f"(HTTP {response.status_code}): "
            f"{response.text[:1500]}"
        )

    data = response.json()

    return json.dumps({
        "success": True,
        "id": data.get("id"),
        "key": data.get("key"),
        "name": name,
        "message": "Project created in Jira.",
    })


@mcp.tool()
async def jira_create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str = "",
) -> str:
    """Create a real Jira issue in an existing project.

    Args:
        project_key: Existing Jira project key, such as AIRESEARCH.
        summary: Short title of the issue.
        issue_type: Task, Bug, or Story, if supported by the project.
        description: Optional plain-text description.
    """
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    if not all([base_url, email, token]):
        raise ValueError("Jira credentials are not configured.")

    if not summary.strip():
        raise ValueError("Issue summary cannot be empty.")

    allowed_types = {"task", "bug", "story"}
    if issue_type.strip().lower() not in allowed_types:
        raise ValueError(
            "issue_type must be Task, Bug, or Story."
        )

    # Jira REST API v3 uses Atlassian Document Format for descriptions.
    description_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": description}],
            }
        ],
    } if description.strip() else None

    fields = {
        "project": {"key": project_key.strip().upper()},
        "summary": summary.strip(),
        "issuetype": {"name": issue_type.strip().title()},
    }

    if description_adf:
        fields["description"] = description_adf

    url = f"{base_url}/rest/api/3/issue"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            auth=(email, token),
            headers={"Accept": "application/json"},
            json={"fields": fields},
        )

    if response.is_error:
        raise ValueError(
            f"Jira issue creation failed "
            f"(HTTP {response.status_code}): "
            f"{response.text[:1500]}"
        )

    data = response.json()

    return json.dumps({
        "success": True,
        "id": data.get("id"),
        "key": data.get("key"),
        "url": f"{base_url}/browse/{data.get('key')}",
        "message": "Issue created in Jira.",
    })



if __name__ == "__main__":
    mcp.run(transport="stdio")
