from pathlib import Path

from app.core.config import Settings
from app.workflows.source_intake import SourceIntakeWorkflow


ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV = ROOT / ".env"

settings = Settings(_env_file=str(ROOT_ENV) if ROOT_ENV.exists() else None)
graph = SourceIntakeWorkflow(settings=settings).graph
