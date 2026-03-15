from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from src.models.schemas import GenerateRequest, GenerateResponse
from src.services.ado import build_patch_document, create_work_item
from src.services.llm import generate_work_item_content
from src.utils.config import settings
from src.utils.validator import validate_notes_text

app = FastAPI(
    title="AI Work Item Assistant",
    version="1.0.0",
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    is_valid, message = validate_notes_text(request.notes)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    try:
        generated = generate_work_item_content(
            notes=request.notes,
            work_item_type=request.work_item_type,
            title_hint=request.title_hint,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    area_path = request.area_path or settings.ADO_DEFAULT_AREA_PATH
    iteration_path = request.iteration_path or settings.ADO_DEFAULT_ITERATION_PATH

    fields = {
        "System.AreaPath": area_path,
        "System.IterationPath": iteration_path,
    }

    response_payload = {
        "work_item_type": request.work_item_type,
        "generated": generated,
        "fields": fields,
        "relations": [],
        "ado_result": None,
    }

    if request.create_in_ado:
        if not area_path:
            raise HTTPException(
                status_code=400,
                detail="area_path is required when create_in_ado is true.",
            )

        if not iteration_path:
            raise HTTPException(
                status_code=400,
                detail="iteration_path is required when create_in_ado is true.",
            )

        try:
            patch_document = build_patch_document(
                title=generated["title"],
                description=generated["description"],
                acceptance_criteria=generated.get("acceptanceCriteria", []),
                area_path=area_path,
                iteration_path=iteration_path,
                extra_fields=generated.get("extraFields", {}),
            )

            ado_result = create_work_item(
                work_item_type=request.work_item_type,
                patch_document=patch_document,
            )
            response_payload["ado_result"] = ado_result

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create work item in Azure DevOps: {str(exc)}",
            ) from exc

    return GenerateResponse(**response_payload)
