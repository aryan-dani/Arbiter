"""
Shared utility to load backend/.env regardless of working directory.
Import this at the top of any module that needs environment variables.
"""
import os
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=True)
