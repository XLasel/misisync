"""One explicit update using the configured source and storage adapters."""
import asyncio
from .composition import build_repository, build_source, build_transport_factory
from .config import Settings
from .sync import Synchronizer


def main():
    settings = Settings.from_env()
    repository = build_repository(settings)
    repository.initialize()
    updater = Synchronizer(repository, build_source(settings), settings, build_transport_factory(settings))
    return 0 if asyncio.run(updater.run_once()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
