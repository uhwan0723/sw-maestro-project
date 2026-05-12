from pathlib import Path

from fastapi import APIRouter, Request
from fastapi import Response
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
FRONTEND_FAVICON = FRONTEND_DIST / "favicon.svg"


@router.get("/")
def home(request: Request):
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return templates.TemplateResponse(request, "index.html")


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    if FRONTEND_FAVICON.exists():
        return FileResponse(FRONTEND_FAVICON, media_type="image/svg+xml")
    return Response(status_code=204)


@router.get("/favicon.svg", include_in_schema=False)
def favicon_svg() -> Response:
    if FRONTEND_FAVICON.exists():
        return FileResponse(FRONTEND_FAVICON, media_type="image/svg+xml")
    return Response(status_code=204)
