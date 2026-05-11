from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.upstage_api_key:
        # 키 없이 부팅은 허용 (스텁/테스트 환경) — 단, /briefing 호출 시 LLM 폴백 경로 탐
        print("[warn] UPSTAGE_API_KEY 미설정 — LLM 호출은 실패하고 폴백 텍스트로 응답됩니다")
    yield


app = FastAPI(
    title="모닝 브리핑 에이전트 API",
    description="16조 — 날씨 + 뉴스 통합 브리핑 백엔드",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "morning-briefing-backend", "docs": "/docs"}
