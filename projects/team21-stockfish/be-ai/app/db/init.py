from importlib import import_module
from importlib.util import find_spec

from app.db.base import Base
from app.db.session import engine

MODEL_MODULES = (
    "app.models.market",
    "app.models.news",
    "app.models.analysis",
)


def import_model_modules() -> None:
    for module_name in MODEL_MODULES:
        if find_spec(module_name) is not None:
            import_module(module_name)


async def init_db() -> None:
    import_model_modules()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
