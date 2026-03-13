from typing import Optional, Literal, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.services.llm import generate_work_item_draft
from src.services.llm_gate import soft_gate
from src.services.ado import create_work_item
from src.utils.config import settings


app = FastAPI(title="ADO Work Item Assistant", version="1.0")


WorkItemType = Literal["PBI", "Bug", "Task"]


class CreateRequest(BaseModel):

    notes: str = Field(..., min_length=1)

    workItemType: WorkItemType = "PBI"

    extraContext: Optional[str] = None


@app.get("/health")
def health() -> Dict[str, Any]:

    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


@app.post("/api/work-items/create")
def create_endpoint(req: CreateRequest):

    gate = soft_gate(req.notes, req.workItemType)

    if gate["action"] == "ask_questions_only":

        return {
            "created": False,
            "gate": gate,
        }

    draft = generate_work_item_draft(
        notes_text=req.notes,
        work_item_type=req.workItemType,
        extra_context=req.extraContext,
    )

    ado = create_work_item(
        title=draft["title"],
        description_md=draft["description"],
        acceptance_criteria=draft.get("acceptanceCriteria", []),
        work_item_type=req.workItemType,
    )

    return {
        "created": True,
        "workItemId": ado["id"],
        "workItemUrl": ado["url"],
        "draft": draft,
    }
