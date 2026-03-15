from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    notes: str = Field(..., min_length=1)
    work_item_type: str = "Product Backlog Item"
    title_hint: Optional[str] = None
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    create_in_ado: bool = False


class GeneratedWorkItem(BaseModel):
    title: str
    description: str
    acceptanceCriteria: List[str] = Field(default_factory=list)
    tasks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    extraFields: Dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    work_item_type: str
    generated: GeneratedWorkItem
    fields: Dict[str, Any]
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    ado_result: Optional[Dict[str, Any]] = None
