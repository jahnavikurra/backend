# main.py

from typing import Optional, Literal, Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.utils.config import settings
from src.services.llm import generate_work_item_draft


app = FastAPI(
    title="Azure DevOps Work Item Assistant",
    version="1.0.0",
)


# -------------------------
# Request / Response models
# -------------------------

WorkItemType = Literal["PBI", "Bug", "Task", "Feature", "Epic", "User Story"]


class DraftRequest(BaseModel):
    notes: str = Field(..., min_length=1, description="Meeting notes / requirements text")
    workItemType: WorkItemType = Field("PBI", description="Desired Azure DevOps work item type")
    process: str = Field("Scrum", description="Process name (Scrum / Agile / CMMI etc.)")
    extraContext: Optional[str] = Field(None, description="Optional extra context")


class DraftResponse(BaseModel):
    title: str
    description: str
    acceptanceCriteria: list[str]
    tasks: list[str]
    assumptions: list[str]
    confidence: float


# -------------------------
# Routes
# -------------------------

@app.get("/health")
def health() -> Dict[str, Any]:
    # Keep it simple: just show app is running + environment
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


@app.post("/api/work-items/draft", response_model=DraftResponse)
def draft_work_item(req: DraftRequest) -> DraftResponse:
    try:
        data = generate_work_item_draft(
            notes_text=req.notes,
            work_item_type=req.workItemType,
            process=req.process,
            extra_context=req.extraContext,
        )
        return DraftResponse(**data)
    except ValueError as e:
        # Bad input
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # LLM/auth/runtime issues
        raise HTTPException(status_code=500, detail=str(e))


# Optional: if you later add Azure DevOps creation logic, wire it here.
class CreateRequest(BaseModel):
    # If you want, you can pass draft JSON directly to creation
    draft: DraftResponse


@app.post("/api/work-items/create")
def create_work_item(req: CreateRequest) -> Dict[str, Any]:
    # Placeholder so your API surface is ready
    raise HTTPException(
        status_code=501,
        detail="Not implemented. Add Azure DevOps create logic in src/services/ado.py and call it here.",
    )
