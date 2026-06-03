from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.agent_profiles import router as agent_profiles_router
from app.api.groups import router as groups_router
from app.api.mcps import router as mcps_router
from app.api.members import router as members_router
from app.api.messages import router as messages_router
from app.api.tools import router as tools_router
from app.api.users import router as users_router
from app.api.ws_groups import router as ws_groups_router
from app.api.ai import router as ai_router
from app.api.project_code import router as project_code_router
from app.api.group_tasks import router as group_tasks_router
from app.api.acp_providers import router as acp_providers_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.auth_service import ensure_default_admin
from app.services.storage_init_service import ensure_user_space
from app.agent_runtime.tool._registry import ensure_builtin_tools_seeded


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.env.lower() in {"local", "dev"}:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    if settings.env.lower() in {"local", "dev"}:
        db = SessionLocal()
        try:
            ensure_default_admin(db)
        finally:
            db.close()
        ensure_builtin_tools_seeded()

    # Always ensure storage dirs exist; safe in production and idempotent.
    ensure_user_space(1)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(groups_router, prefix=settings.api_prefix)
app.include_router(tools_router, prefix=settings.api_prefix)
app.include_router(mcps_router, prefix=settings.api_prefix)
app.include_router(agent_profiles_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)
app.include_router(members_router, prefix=settings.api_prefix)
app.include_router(messages_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(project_code_router, prefix=settings.api_prefix)
app.include_router(group_tasks_router, prefix=settings.api_prefix)
app.include_router(acp_providers_router, prefix=settings.api_prefix)
app.include_router(ws_groups_router)
