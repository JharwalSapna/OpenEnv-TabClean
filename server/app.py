from __future__ import annotations

import os

from openenv.core.env_server import create_fastapi_app

from models import TabCleanAction, TabCleanObservation
from server.environment import TabCleanEnvironment

app = create_fastapi_app(TabCleanEnvironment, TabCleanAction, TabCleanObservation)


def main() -> None:
    """
    Entry point used by `openenv validate` and `uv run server`.
    """
    import uvicorn  # local import to keep import-time side effects minimal

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    uvicorn.run("server.app:app", host=host, port=port, workers=workers)


if __name__ == "__main__":
    main()

