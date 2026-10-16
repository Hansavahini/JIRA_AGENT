
import os

import httpx


def get_jira_config():
    """Read Jira credentials from environment variables."""
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    if not all([base_url, email, token]):
        raise ValueError(
            "Configure JIRA_BASE_URL, JIRA_EMAIL, "
            "and JIRA_API_TOKEN in .env."
        )

    if not base_url.startswith("https://"):
        raise ValueError("JIRA_BASE_URL must use HTTPS.")

    return base_url, email, token


async def jira_request(method, path, **kwargs):
    """Send an authenticated request to the Jira REST API."""
    base_url, email, token = get_jira_config()

    url = f"{base_url}/rest/api/3/{path.lstrip('/')}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=url,
            auth=(email, token),
            headers={"Accept": "application/json"},
            **kwargs,
        )

    if response.is_error:
        raise RuntimeError(
            f"Jira API request failed "
            f"(HTTP {response.status_code}): "
            f"{response.text[:1500]}"
        )

    return response.json()
