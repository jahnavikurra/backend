import base64
from typing import Any, Dict, List

import requests

from src.utils.config import settings
from src.utils.keyvault import get_secret_from_key_vault


def _get_ado_pat() -> str:
    if not settings.ADO_PAT_SECRET_NAME:
        raise ValueError("ADO_PAT_SECRET_NAME is not configured.")
    return get_secret_from_key_vault(settings.ADO_PAT_SECRET_NAME)


def _get_auth_headers() -> Dict[str, str]:
    pat = _get_ado_pat()
    encoded_pat = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")

    return {
        "Content-Type": "application/json-patch+json",
        "Authorization": f"Basic {encoded_pat}",
    }


def build_patch_document(
    title: str,
    description: str,
    acceptance_criteria: List[str],
    area_path: str | None = None,
    iteration_path: str | None = None,
    extra_fields: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    patch_document: List[Dict[str, Any]] = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description},
    ]

    if acceptance_criteria:
        ac_text = "<br/>".join([f"- {item}" for item in acceptance_criteria])
        patch_document.append(
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                "value": ac_text,
            }
        )

    if area_path:
        patch_document.append(
            {"op": "add", "path": "/fields/System.AreaPath", "value": area_path}
        )

    if iteration_path:
        patch_document.append(
            {
                "op": "add",
                "path": "/fields/System.IterationPath",
                "value": iteration_path,
            }
        )

    if extra_fields:
        for field_name, field_value in extra_fields.items():
            patch_document.append(
                {"op": "add", "path": f"/fields/{field_name}", "value": field_value}
            )

    return patch_document


def create_work_item(work_item_type: str, patch_document: List[Dict[str, Any]]) -> Dict[str, Any]:
    url = (
        f"https://dev.azure.com/{settings.ADO_ORGANIZATION}/"
        f"{settings.ADO_PROJECT}/_apis/wit/workitems/"
        f"${work_item_type}?api-version=7.1"
    )

    response = requests.post(
        url,
        headers=_get_auth_headers(),
        json=patch_document,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()
