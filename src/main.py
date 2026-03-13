from fastapi import FastAPI, HTTPException

from src.models.schemas import GenerateRequest, GenerateResponse
from src.services.ado import build_patch_document, create_work_item
from src.services.llm import generate_work_item_content
from src.services.llm_gate import gate_notes
from src.utils.config import settings
from src.utils.validator import validate_notes

app = FastAPI(
    title="AI Work Item Assistant",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    is_valid, message = validate_notes(request.notes)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    gate_result = gate_notes(request.notes)
    if gate_result.get("action") == "ask_questions_only":
        raise HTTPException(
            status_code=400,
            detail={
                "message": gate_result.get("messageToUser", "Need more details."),
                "questions": gate_result.get("questions", []),
                "assumptions": gate_result.get("assumptions", []),
                "confidence": gate_result.get("confidence", 0.0),
            },
        )

    generated = generate_work_item_content(
        notes=request.notes,
        work_item_type=request.work_item_type,
    )

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
        patch_document = build_patch_document(
            title=generated["title"],
            description=generated["description"],
            acceptance_criteria=generated.get("acceptanceCriteria", []),
            area_path=area_path,
            iteration_path=iteration_path,
            extra_fields=generated.get("extraFields", {}),
        )
        ado_result = create_work_item(request.work_item_type, patch_document)
        response_payload["ado_result"] = ado_result

    return GenerateResponse(**response_payload)
