from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    notes: str = Field(..., min_length=1, description="User notes or meeting text")
    work_item_type: str = Field(
        default="Product Backlog Item",
        description="Azure DevOps work item type",
    )
    title_hint: Optional[str] = None
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    create_in_ado: bool = False


class GeneratedWorkItem(BaseModel):
    title: str
    description: str
    acceptanceCriteria: List[str]
    tasks: List[str]
    assumptions: List[str]
    confidence: float
    extraFields: Dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    work_item_type: str
    generated: GeneratedWorkItem
    fields: Dict[str, Any]
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    ado_result: Optional[Dict[str, Any]] = None


class GateResult(BaseModel):
    action: str
    messageToUser: str
    questions: List[str]
    assumptions: List[str]
    confidence: float
