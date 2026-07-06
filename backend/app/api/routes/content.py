"""Content routes: list stored ideas and generate new content plans."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...errors import status_for
from ...memory import MemoryService
from ...models.content import ContentRequest, ContentResponse
from ...services.content_creator_service import ContentCreatorService
from ..deps import memory_dep

router = APIRouter(prefix="/content", tags=["content"])


@router.get("")
def list_content(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [c.model_dump(mode="json") for c in memory.content.list()]


@router.post("/generate", response_model=ContentResponse)
def generate_content(request: ContentRequest) -> JSONResponse:
    """Generate a validated TikTok content plan from a business brief."""

    service = ContentCreatorService()
    response = service.generate(request)
    status_code = 200 if response.success else status_for(response.error_type)
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))
