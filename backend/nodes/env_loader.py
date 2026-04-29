"""
Shared utility to load backend/.env regardless of working directory.
Import this at the top of any module that needs environment variables.
"""
import os
from dotenv import load_dotenv

_backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_env_path = os.path.join(_backend_dir, ".env")
_env_local = os.path.join(_backend_dir, ".env.local")
load_dotenv(dotenv_path=_env_path, override=True)
load_dotenv(dotenv_path=_env_local, override=True)
