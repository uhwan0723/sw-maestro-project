from pathlib import Path

from app.core.config import Settings
from app.main import _sqlite_path_from_url
from app.repositories.sqlite import SQLiteRepository
from app.workflows.qa import RetrievalQAWorkflow


ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV = ROOT / ".env"

settings = Settings(_env_file=str(ROOT_ENV) if ROOT_ENV.exists() else None)
repository = SQLiteRepository(_sqlite_path_from_url(settings.database_url))
repository.initialize()

graph = RetrievalQAWorkflow(repository=repository, upstage_api_key=settings.upstage_api_key).graph
