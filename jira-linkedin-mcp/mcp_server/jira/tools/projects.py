
import json
import re

from mcp_server.jira.services.jira_client import jira_request


async def jira_list_projects(max_results: int = 50) -> str:
    """List Jira projects accessible to the current account.

    Use this tool to find project names and keys.
    This operation is read-only.
    """
    if not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100.")

    data = await jira_request(
        "GET",
        "project/search",
        params={"maxResults": max_results, "startAt": 0},
    )

    projects = [
        {
            "id": project.get("id"),
            "key": project.get("key"),
            "name": project.get("name"),
        }
        for project in data.get("values", [])
    ]

    return json.dumps({
        "count": len(projects),
        "projects": projects,
        "has_more": data.get("isLast", True) is False,
    })


async def jira_create_project(
    name: str,
    key: str,
    description: str = "",
) -> str:
    """Create a Jira Software project.

    Requires administrator permissions.
    The caller must obtain user approval before execution.
    """
    if not name.strip():
        raise ValueError("Project name cannot be empty.")

    key = key.strip().upper()

    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", key):
        raise ValueError(
            "Project key must contain 2-10 letters or digits "
            "and start with a letter."
        )

    data = await jira_request(
        "POST",
        "project",
        json={
            "name": name.strip(),
            "key": key,
            "description": description,
            "projectTypeKey": "software",
            "projectTemplateKey": (
                "com.pyxis.greenhopper.jira:gh-scrum-template"
            ),
        },
    )

    return json.dumps({
        "success": True,
        "id": data.get("id"),
        "key": data.get("key"),
        "name": data.get("name", name.strip()),
        "message": "Project created in Jira.",
    })
