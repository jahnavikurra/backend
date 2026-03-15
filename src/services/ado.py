import base64
from typing import Any

import requests

from src.services.keyvault import get_secret
from src.utils.config import settings


def _build_auth_header(pat: str) -> str:
    token = f":{pat}".encode("utf-8")
    return base64.b64encode(token).decode("utf-8")


def build_patch_document(
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
) -> list[dict[str, Any]]:
    patch_document: list[dict[str, Any]] = [
        {
            "op": "add",
            "path": "/fields/System.Title",
            "value": title,
        },
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": description,
        },
    ]

    if acceptance_criteria:
        ac_text = "<br/>".join(f"- {item}" for item in acceptance_criteria if item.strip())
        if ac_text:
            patch_document.append(
                {
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                    "value": ac_text,
                }
            )

    return patch_document


def create_work_item(
    project: str,
    work_item_type: str,
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    if not project or not project.strip():
        raise ValueError("Project name is required for ADO creation.")

    pat = get_secret(settings.ADO_PAT_SECRET_NAME)
    auth_header = _build_auth_header(pat)

    url = (
        f"{settings.ADO_ORG_URL}/{project}"
        f"/_apis/wit/workitems/${work_item_type}?api-version=7.1"
    )

    headers = {
        "Content-Type": "application/json-patch+json",
        "Authorization": f"Basic {auth_header}",
    }

    patch_document = build_patch_document(
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria or [],
    )

    response = requests.post(url, headers=headers, json=patch_document, timeout=30)

    if response.status_code >= 400:
        raise ValueError(
            f"ADO create failed with {response.status_code}: {response.text}"
        )

    data = response.json()
    return {
        "id": data.get("id"),
        "url": data.get("url"),
    }
