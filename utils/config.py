"""
Loads settings from .env so nothing environment-specific is hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")