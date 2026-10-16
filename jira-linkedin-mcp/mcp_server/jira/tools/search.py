
import json

from mcp_server.jira.services.jira_client import jira_request


async def jira_search_issues(
    jql: str,
    max_results: int = 5,
) -> str:
    """Search Jira issues using valid Jira Query Language.

    Examples:
    - created >= -30d ORDER BY created DESC
    - project = SCRUM ORDER BY updated DESC
    - assignee IS EMPTY ORDER BY created DESC

    Use a bounded query. This operation is read-only.
    """
    if not jql.strip():
        raise ValueError("JQL cannot be empty.")

    if not 1 <= max_results <= 20:
        raise ValueError("max_results must be between 1 and 20.")

    data = await jira_request(
        "GET",
        "search/jql",
        params={
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,assignee,issuetype",
        },
    )

    issues = []

    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        status = fields.get("status")
        assignee = fields.get("assignee")
        issue_type = fields.get("issuetype")

        issues.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "status": status.get("name") if status else None,
            "assignee": (
                assignee.get("displayName")
                if assignee else "Unassigned"
            ),
            "issue_type": (
                issue_type.get("name") if issue_type else None
            ),
        })

    return json.dumps({
        "total_returned": len(issues),
        "issues": issues,
    })
