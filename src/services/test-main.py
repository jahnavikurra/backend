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

WorkItemType = Literal["PBI", "Bug", "Task", "Feature", "Epic", "User Story"]


class DraftRequest(BaseModel):
    notes: str = Field(..., min_length=1)
    workItemType: WorkItemType = Field("PBI")
    process: str = Field("Scrum")
    extraContext: Optional[str] = None


class DraftResponse(BaseModel):
    title: str
    description: str
    acceptanceCriteria: list[str]
    tasks: list[str]
    assumptions: list[str]
    confidence: float


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "azure_openai_endpoint_set": bool(getattr(settings, "AZURE_OPENAI_ENDPOINT", "")),
        "azure_openai_deployment_set": bool(getattr(settings, "AZURE_OPENAI_DEPLOYMENT", "")),
    }


@app.get("/health/llm")
def health_llm() -> Dict[str, Any]:
    """
    Real end-to-end check: confirms Managed Identity auth + deployment works.
    """
    try:
        draft = generate_work_item_draft(
            notes_text="Create a work item for adding a /health endpoint to our API.",
            work_item_type="PBI",
            process="Scrum",
        )
        return {
            "status": "ok",
            "model_call": "success",
            "sample_title": draft.get("title"),
            "confidence": draft.get("confidence"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM health check failed: {e}")


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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
