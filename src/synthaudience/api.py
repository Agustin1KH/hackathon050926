"""FastAPI surface. MVP: synchronous /evaluate, no auth, no rate limiting."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from synthaudience.db import (
    AudienceRow,
    PersonaRow,
    RunRow,
    get_session_factory,
    init_db,
)
from synthaudience.evaluation.runner import run_evaluation
from synthaudience.llm import get_llm_client
from synthaudience.models import (
    AudienceSpec,
    ContentPayload,
    EvaluationReport,
    Persona,
)
from synthaudience.personas.generator import generate_personas
from synthaudience.personas.text_to_spec import text_to_audience_spec

app = FastAPI(title="synthaudience", version="0.1.0")

_UI_PATH = Path(__file__).parent / "static" / "index.html"


class GenerateRequest(BaseModel):
    audience_id: str


class AudienceResponse(BaseModel):
    audience_id: str


class FromTextRequest(BaseModel):
    description: str
    total_agents: int = 12


class FromTextResponse(BaseModel):
    audience_id: str
    spec: AudienceSpec


class GenerateResponse(BaseModel):
    personas: list[Persona]
    count: int


class EvaluateResponse(BaseModel):
    run_id: uuid.UUID


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.post("/audience", response_model=AudienceResponse)
def post_audience(spec: AudienceSpec) -> AudienceResponse:
    factory = get_session_factory()
    with factory() as session:
        existing = session.query(AudienceRow).filter_by(name=spec.name).first()
        if existing:
            existing.spec_json = spec.model_dump_json()
        else:
            session.add(AudienceRow(name=spec.name, spec_json=spec.model_dump_json()))
        session.commit()
    return AudienceResponse(audience_id=spec.name)


@app.post("/audience/from-text", response_model=FromTextResponse)
async def post_audience_from_text(req: FromTextRequest) -> FromTextResponse:
    """Parse a free-form audience description into a validated AudienceSpec and persist it."""
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="description must not be empty")

    try:
        spec = await text_to_audience_spec(
            req.description,
            llm=get_llm_client(),
            total_agents=req.total_agents,
        )
    except Exception as e:
        raise _llm_error_to_http(e)

    if spec is None:
        raise HTTPException(
            status_code=502,
            detail="Could not parse description into a valid AudienceSpec; try giving the LLM more detail.",
        )

    factory = get_session_factory()
    with factory() as session:
        existing = session.query(AudienceRow).filter_by(name=spec.name).first()
        if existing:
            existing.spec_json = spec.model_dump_json()
        else:
            session.add(AudienceRow(name=spec.name, spec_json=spec.model_dump_json()))
        session.commit()

    return FromTextResponse(audience_id=spec.name, spec=spec)


@app.post("/personas/generate", response_model=GenerateResponse)
async def post_generate_personas(req: GenerateRequest) -> GenerateResponse:
    factory = get_session_factory()
    with factory() as session:
        row = session.query(AudienceRow).filter_by(name=req.audience_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Audience {req.audience_id} not found")
        spec = AudienceSpec(**json.loads(row.spec_json))

    try:
        personas = await generate_personas(spec)
    except Exception as e:
        raise _llm_error_to_http(e)
    return GenerateResponse(personas=personas, count=len(personas))


@app.post("/browse/run-once")
async def post_browse_once() -> dict:
    from synthaudience.discovery.scheduler import run_browse_once

    return await run_browse_once()


@app.post("/evaluate", response_model=EvaluateResponse)
async def post_evaluate(content: ContentPayload) -> EvaluateResponse:
    run_id = uuid.uuid4()
    await run_evaluation(content, run_id)
    return EvaluateResponse(run_id=run_id)


# Cap uploads at 50 MB to prevent surprise costs on a misclick. A 20s vertical
# 1080p clip is typically 5-15 MB; this leaves headroom without inviting abuse.
_MAX_VIDEO_BYTES = 50 * 1024 * 1024


class VideoEvaluateResponse(BaseModel):
    run_id: uuid.UUID
    description: str
    report: EvaluationReport


@app.post("/evaluate/video", response_model=VideoEvaluateResponse)
async def post_evaluate_video(
    title: str = Form(...),
    video: UploadFile = File(...),
) -> VideoEvaluateResponse:
    """Upload a short video, get back the population's reactions."""
    import tempfile
    from pathlib import Path

    from synthaudience.evaluation.runner import run_evaluation
    from synthaudience.memory import MemoryStore
    from synthaudience.models import ContentPayload
    from synthaudience.video import describe_video

    if not title.strip():
        raise HTTPException(status_code=400, detail="title must not be empty")

    raw = await video.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty video upload")
    if len(raw) > _MAX_VIDEO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Video too large ({len(raw):,} bytes). Limit is {_MAX_VIDEO_BYTES:,}.",
        )

    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        try:
            description = await describe_video(tmp_path, title=title, llm=get_llm_client())
        except Exception as e:
            raise _llm_error_to_http(e)

        content = ContentPayload(
            kind="video",
            title=title,
            body=title,  # for video, title doubles as body since there's no caption text
            media_description=description,
        )
        run_id = uuid.uuid4()

        memory = MemoryStore()
        try:
            report = await run_evaluation(content, run_id, memory_factory=lambda _p: memory)
        except Exception as e:
            raise _llm_error_to_http(e)

        return VideoEvaluateResponse(run_id=run_id, description=description, report=report)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/reports/{run_id}", response_model=EvaluationReport)
def get_report(run_id: str) -> EvaluationReport:
    factory = get_session_factory()
    with factory() as session:
        row = session.query(RunRow).filter_by(id=run_id).first()
        if row is None or not row.report_json:
            raise HTTPException(status_code=404, detail=f"No report for run {run_id}")
        return EvaluationReport(**json.loads(row.report_json))


def _llm_error_to_http(exc: Exception) -> HTTPException:
    """Translate common LLM-provider errors into actionable 4xx/5xx responses."""
    msg = str(exc)
    name = type(exc).__name__
    # Anthropic / OpenAI both raise an "AuthenticationError" subclass on bad keys.
    if "Authentication" in name or "401" in msg or "invalid x-api-key" in msg:
        return HTTPException(
            status_code=401,
            detail=(
                "LLM provider rejected the API key. Set ANTHROPIC_API_KEY (or OPENAI_API_KEY "
                "if LLM_PROVIDER=openai) in your .env to a real key, then restart the server."
            ),
        )
    if "RateLimit" in name or "429" in msg:
        return HTTPException(
            status_code=429, detail="LLM provider rate-limited the request; try again shortly."
        )
    if "Connection" in name or "Timeout" in name:
        return HTTPException(
            status_code=502, detail=f"Could not reach the LLM provider ({name}): {msg}"
        )
    return HTTPException(status_code=500, detail=f"LLM call failed ({name}): {msg}")


@app.get("/", include_in_schema=False)
def get_index() -> FileResponse:
    """Serve the single-page UI."""
    return FileResponse(_UI_PATH)


@app.get("/personas", response_model=list[Persona])
def get_personas(segment_id: Optional[str] = Query(None)) -> list[Persona]:
    factory = get_session_factory()
    with factory() as session:
        q = session.query(PersonaRow)
        if segment_id is not None:
            q = q.filter_by(segment_id=segment_id)
        rows = q.all()
        return [
            Persona(
                id=r.id,
                segment_id=r.segment_id,
                display_name=r.display_name,
                age=r.age,
                country=r.country,
                occupation=r.occupation,
                bio=r.bio,
                tone_examples=json.loads(r.tone_examples),
                interest_graph=json.loads(r.interest_graph),
                posting_ratio=r.posting_ratio,
                created_at=r.created_at,
            )
            for r in rows
        ]
