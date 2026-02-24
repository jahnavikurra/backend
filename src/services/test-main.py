# src/main.py

import logging
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.services.llm import generate_work_item_draft
from src.utils.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workitems-backend")

app = FastAPI(
    title="AI Work Items Backend",
    version="1.0.0",
    description="FastAPI backend to generate Scrum work items using Azure OpenAI (Entra ID).",
)


# -----------------------------
# Schemas
# -----------------------------
class GenerateRequest(BaseModel):
    notesText: str = Field(..., min_length=1, description="Meeting notes / requirement text")
    workItemType: str = Field("PBI", description="PBI | Bug | Task")
    process: str = Field("Scrum", description="Scrum | Agile | CMMI")
    extraContext: str | None = Field(None, description="Optional additional context")


class ValidateRequest(BaseModel):
    notesText: str = Field(..., min_length=1, description="Meeting notes / requirement text")


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "workitems-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/debug/settings")
def debug_settings():
    """
    Shows whether required settings are present (values masked).
    Do NOT expose real secrets in production.
    """
    def mask(v: str | None) -> str | None:
        if not v:
            return None
        return v[:6] + "..." + v[-4:] if len(v) > 12 else "***"

    return {
        "AZURE_OPENAI_ENDPOINT": mask(getattr(settings, "AZURE_OPENAI_ENDPOINT", None)),
        "AZURE_OPENAI_DEPLOYMENT": mask(getattr(settings, "AZURE_OPENAI_DEPLOYMENT", None)),
        "AZURE_OPENAI_API_VERSION": getattr(settings, "AZURE_OPENAI_API_VERSION", None),
        "ENVIRONMENT": getattr(settings, "ENVIRONMENT", None),
    }


@app.post("/api/validate")
def validate(req: ValidateRequest):
    """
    Simple validation endpoint.
    """
    text = (req.notesText or "").strip()
    if len(text) < 10:
        return {"ok": False, "reason": "Please provide at least 10 characters of notes."}
    return {"ok": True}


@app.get("/api/test-llm")
def test_llm():
    """
    Smoke test to verify Entra auth + deployment + endpoint works.
    If this fails, /api/generate will also fail.
    """
    try:
        draft = generate_work_item_draft(
            notes_text="Create a PBI to update Black Duck version to latest and validate pipelines.",
            work_item_type="PBI",
            process="Scrum",
        )
        return {"ok": True, "sample": draft.get("title")}
    except Exception as e:
        logger.exception("LLM smoke test failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
def generate(req: GenerateRequest):
    """
    Generates a structured Scrum work item draft (JSON) from notes using Azure OpenAI.
    """
    try:
        draft = generate_work_item_draft(
            notes_text=req.notesText,
            work_item_type=req.workItemType,
            process=req.process,
            extra_context=req.extraContext,
        )
        return {"ok": True, "draft": draft}
    except Exception as e:
        # Print full traceback in console logs
        traceback.print_exc()
        logger.exception("Generate failed")
        # Return readable error to Swagger/client (helpful while debugging)
        raise HTTPException(status_code=500, detail=str(e))
