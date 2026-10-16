
import json

from mcp_server.jira.services.jira_client import jira_request


async def jira_create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str = "",
) -> str:
    """Create an issue in an existing Jira project.

    Supported issue types: Task, Bug, Story.
    Requires approval before execution.
    """
    if not project_key.strip():
        raise ValueError("Project key cannot be empty.")

    if not summary.strip():
        raise ValueError("Issue summary cannot be empty.")

    allowed_types = {"task": "Task", "bug": "Bug", "story": "Story"}
    normalized_type = allowed_types.get(issue_type.strip().lower())

    if normalized_type is None:
        raise ValueError("issue_type must be Task, Bug, or Story.")

    fields = {
        "project": {"key": project_key.strip().upper()},
        "summary": summary.strip(),
        "issuetype": {"name": normalized_type},
    }

    if description.strip():
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": description.strip(),
                }],
            }],
        }

    data = await jira_request(
        "POST",
        "issue",
        json={"fields": fields},
    )

    base_url, _, _ = __import__(
        "mcp_server.jira.services.jira_client",
        fromlist=["get_jira_config"],
    ).get_jira_config()

    issue_key = data.get("key")

    return json.dumps({
        "success": True,
        "id": data.get("id"),
        "key": issue_key,
        "url": f"{base_url}/browse/{issue_key}",
        "message": "Issue created in Jira.",
    })
