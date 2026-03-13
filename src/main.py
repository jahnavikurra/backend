import logging
from typing import Optional, Literal, Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.utils.config import settings
from src.services.llm import generate_work_item_draft
from src.services.llm_gate import soft_gate
from src.services.ado import create_work_item

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Azure DevOps Work Item Assistant", version="1.3.0")

WorkItemType = Literal["PBI", "Bug", "Task", "Feature", "Epic", "User Story"]


# -------------------------
# Models
# -------------------------

class DraftRequest(BaseModel):
    notes: str = Field(..., min_length=1)
    project: str = Field(..., min_length=1)
    team: Optional[str] = None
    workItemType: WorkItemType = Field("PBI")
    extraContext: Optional[str] = None


class GateResponse(BaseModel):
    action: Literal["create_draft", "ask_questions_only"]
    messageToUser: str
    questions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    confidence: float


class DraftResponse(BaseModel):
    title: str
    description: str
    valueStatement: str = ""
    acceptanceCriteria: List[str] = Field(default_factory=list)
    tasks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    confidence: float


class DraftWithGateResponse(BaseModel):
    gate: GateResponse
    draft: Optional[DraftResponse] = None


class CreateRequest(BaseModel):
    notes: str = Field(..., min_length=1)
    project: str = Field(..., min_length=1)
    team: Optional[str] = None
    workItemType: WorkItemType = Field("PBI")
    extraContext: Optional[str] = None


class CreateResponse(BaseModel):
    created: bool
    workItemId: Optional[int] = None
    workItemUrl: Optional[str] = None
    project: Optional[str] = None
    team: Optional[str] = None
    draft: Optional[DraftResponse] = None
    gate: GateResponse


# -------------------------
# Error Handling
# -------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error (check logs)"},
    )


# -------------------------
# Health
# -------------------------

@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/llm")
def health_llm() -> Dict[str, Any]:
    try:
        draft = generate_work_item_draft(
            notes_text="Add logging improvements",
            work_item_type="Task",
        )
        return {
            "status": "ok",
            "sample_title": draft.get("title"),
            "confidence": draft.get("confidence"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# Helpers
# -------------------------

def build_merged_context(
    extra_context: Optional[str],
    team: Optional[str],
    gate: Dict[str, Any],
) -> Optional[str]:
    parts: List[str] = []

    if extra_context and extra_context.strip():
        parts.append(extra_context.strip())

    if team and team.strip():
        parts.append(f"Current Azure DevOps team context: {team.strip()}")

    assumptions = gate.get("assumptions", []) or []
    if assumptions:
        assumptions_block = "\n".join(
            [f"- {item}" for item in assumptions if str(item).strip()]
        )
        if assumptions_block:
            parts.append(f"Assumptions:\n{assumptions_block}")

    if not parts:
        return None

    return "\n\n".join(parts)


# -------------------------
# Draft Endpoint
# -------------------------

@app.post("/api/work-items/draft", response_model=DraftWithGateResponse)
def draft_work_item(req: DraftRequest) -> DraftWithGateResponse:
    gate = soft_gate(req.notes, req.workItemType)

    if gate["action"] == "ask_questions_only":
        return DraftWithGateResponse(
            gate=GateResponse(**gate),
            draft=None,
        )

    merged_context = build_merged_context(
        extra_context=req.extraContext,
        team=req.team,
        gate=gate,
    )

    draft = generate_work_item_draft(
        notes_text=req.notes,
        work_item_type=req.workItemType,
        extra_context=merged_context,
    )

    if not draft.get("questions") and gate.get("questions"):
        draft["questions"] = gate["questions"]

    return DraftWithGateResponse(
        gate=GateResponse(**gate),
        draft=DraftResponse(**draft),
    )


# -------------------------
# Create Work Item Endpoint
# -------------------------

@app.post("/api/work-items/create", response_model=CreateResponse)
def create_work_item_endpoint(req: CreateRequest) -> CreateResponse:
    gate = soft_gate(req.notes, req.workItemType)

    if gate["action"] == "ask_questions_only":
        return CreateResponse(
            created=False,
            project=req.project,
            team=req.team,
            gate=GateResponse(**gate),
            draft=None,
        )

    merged_context = build_merged_context(
        extra_context=req.extraContext,
        team=req.team,
        gate=gate,
    )

    draft = generate_work_item_draft(
        notes_text=req.notes,
        work_item_type=req.workItemType,
        extra_context=merged_context,
    )

    if not draft.get("questions") and gate.get("questions"):
        draft["questions"] = gate["questions"]

    ado = create_work_item(
        project=req.project,
        title=draft["title"],
        description_md=draft["description"],
        acceptance_criteria=draft.get("acceptanceCriteria", []),
        work_item_type=req.workItemType,
    )

    return CreateResponse(
        created=True,
        workItemId=ado.get("id"),
        workItemUrl=ado.get("url"),
        project=req.project,
        team=req.team,
        draft=DraftResponse(**draft),
        gate=GateResponse(**gate),
    )
