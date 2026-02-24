# main.py

import logging
from typing import Optional, Literal, Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.utils.config import settings
from src.services.llm import generate_work_item_draft

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Azure DevOps Work Item Assistant", version="1.0.0")

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Logs full stack trace in Container App logs
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error (check logs for details)"},
    )


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "azure_openai_endpoint_set": bool(settings.AZURE_OPENAI_ENDPOINT),
        "azure_openai_deployment_set": bool(settings.AZURE_OPENAI_DEPLOYMENT),
    }


@app.get("/health/llm")
def health_llm() -> Dict[str, Any]:
    """
    End-to-end check: if this fails, the issue is almost certainly
    Managed Identity/RBAC, env vars, deployment name, or networking.
    """
    try:
        draft = generate_work_item_draft(
            notes_text="Create a work item to add a /health endpoint.",
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
        logger.exception("LLM health check failed: %s", e)
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
        logger.exception("Draft generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
