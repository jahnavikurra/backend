import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.models.schemas import AdoResult, GenerateRequest, GenerateResponse, GeneratedContent
from src.services.ado import create_work_item
from src.services.llm import generate_work_item_content
from src.utils.config import settings
from src.utils.validator import validate_notes_text

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Work Item Assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
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
        generated_raw = generate_work_item_content(
            notes=request.notes,
            work_item_type=request.work_item_type,
        )
        generated = GeneratedContent(**generated_raw)

    except Exception as exc:
        logger.exception("LLM generation failed")
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(exc)}") from exc

    ado_result = None

    if request.create_in_ado:
        if not request.project_name or not request.project_name.strip():
            raise HTTPException(
                status_code=400,
                detail="project_name is required when create_in_ado=true",
            )

        try:
            ado_raw = create_work_item(
                project=request.project_name.strip(),
                work_item_type=request.work_item_type,
                title=generated.title,
                description=generated.description,
                acceptance_criteria=generated.acceptanceCriteria,
            )
            ado_result = AdoResult(**ado_raw)

        except Exception as exc:
            logger.exception("ADO creation failed")
            raise HTTPException(status_code=500, detail=f"ADO creation failed: {str(exc)}") from exc

    return GenerateResponse(
        work_item_type=request.work_item_type,
        project_name=request.project_name,
        generated=generated,
        ado_result=ado_result,
    )
