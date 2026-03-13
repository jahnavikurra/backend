from typing import Any, Dict, List

import requests
from azure.identity import ClientSecretCredential

from src.utils.config import settings


ADO_SCOPE = "499b84ac-1321-427f-aa17-267ca6975798/.default"


def get_ado_access_token() -> str:
    """
    Fetch Azure DevOps token using Service Principal
    """

    credential = ClientSecretCredential(
        tenant_id=settings.AZURE_TENANT_ID,
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET,
    )

    token = credential.get_token(ADO_SCOPE)

    return token.token


def render_description_html(description_md: str) -> str:

    if not description_md:
        return ""

    return f"<div>{description_md}</div>"


def create_work_item(
    *,
    title: str,
    description_md: str,
    acceptance_criteria: List[str],
    work_item_type: str,
) -> Dict[str, Any]:

    if not settings.ADO_ORG_URL:
        raise RuntimeError("ADO_ORG_URL missing")

    if not settings.ADO_PROJECT:
        raise RuntimeError("ADO_PROJECT missing")

    wit = work_item_type.strip()

    if wit.upper() == "PBI":
        wit = "Product Backlog Item"

    url = (
        f"{settings.ADO_ORG_URL}/{settings.ADO_PROJECT}"
        f"/_apis/wit/workitems/${wit}?api-version=7.1"
    )

    ac_text = ""

    if acceptance_criteria:
        ac_text = "\n".join([f"- {x}" for x in acceptance_criteria])

    patch_ops: List[Dict[str, Any]] = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": render_description_html(description_md),
        },
    ]

    if ac_text:
        patch_ops.append(
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                "value": ac_text,
            }
        )

    headers = {
        "Authorization": f"Bearer {get_ado_access_token()}",
        "Content-Type": "application/json-patch+json",
    }

    resp = requests.post(url, headers=headers, json=patch_ops)

    if not resp.ok:
        raise RuntimeError(resp.text)

    data = resp.json()

    work_item_id = data.get("id")

    browser_url = (
        f"{settings.ADO_ORG_URL}/{settings.ADO_PROJECT}"
        f"/_workitems/edit/{work_item_id}"
    )

    return {
        "id": work_item_id,
        "url": browser_url,
        "raw": data,
    }
