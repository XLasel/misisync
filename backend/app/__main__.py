"""Run an on-demand import: python -m app (run separately from the API)."""
import asyncio

from .config import Settings
from .db import Database
from .sync import Synchronizer

settings = Settings.from_env()
database = Database(settings.database_path)
database.initialize()
raise SystemExit(0 if asyncio.run(Synchronizer(database, settings).run_once()) else 1)
