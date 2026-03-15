from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    notes: str = Field(..., min_length=5)
    work_item_type: str = "Product Backlog Item"
    create_in_ado: bool = False
    project_name: str | None = None


class GeneratedContent(BaseModel):
    title: str
    description: str
    valueStatement: str | None = None
    acceptanceCriteria: list[str] = []
    tasks: list[str] = []
    assumptions: list[str] = []
    dependencies: list[str] = []
    questions: list[str] = []
    confidence: float = 0.0


class AdoResult(BaseModel):
    id: int | None = None
    url: str | None = None


class GenerateResponse(BaseModel):
    work_item_type: str
    project_name: str | None = None
    generated: GeneratedContent
    ado_result: AdoResult | None = None
    error: str | None = None
    raw: dict[str, Any] | None = None
