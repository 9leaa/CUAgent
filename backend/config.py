from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_token: str
    root: Path
    base_tasks: Path
    cookie_file: Path
    lease_seconds: int = 30

    @classmethod
    def from_env(cls):
        root = Path(os.environ['CUAGENT_BACKEND_ROOT']).resolve()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.stat().st_mode & 0o077:
            raise ValueError('backend root must be private')
        token = os.environ['CUAGENT_BACKEND_TOKEN']
        if len(token) < 32:
            raise ValueError('backend token must be at least 32 characters')
        return cls(os.environ['CUAGENT_DATABASE_URL'], token, root,
                   Path(os.environ['CUAGENT_BASE_TASKS']), Path(os.environ['CUAGENT_DSH_COOKIE_FILE']))
