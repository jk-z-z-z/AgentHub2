from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.acp_providers import router as acp_providers_router
from app.api.agent_instances import router as agent_instances_router
from app.api.agent_profiles import router as agent_profiles_router
from app.api.groups import router as groups_router
from app.api.mcps import router as mcps_router
from app.api.members import router as members_router
from app.api.messages import router as messages_router
from app.api.skills import router as skills_router
from app.api.tools import router as tools_router
from app.api.users import router as users_router
from app.api.ws_groups import router as ws_groups_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.auth_service import ensure_default_admin

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(groups_router, prefix=settings.api_prefix)
app.include_router(tools_router, prefix=settings.api_prefix)
app.include_router(mcps_router, prefix=settings.api_prefix)
app.include_router(skills_router, prefix=settings.api_prefix)
app.include_router(acp_providers_router, prefix=settings.api_prefix)
app.include_router(agent_profiles_router, prefix=settings.api_prefix)
app.include_router(agent_instances_router, prefix=settings.api_prefix)
app.include_router(members_router, prefix=settings.api_prefix)
app.include_router(messages_router, prefix=settings.api_prefix)
app.include_router(ws_groups_router)
