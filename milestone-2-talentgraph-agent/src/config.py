"""Configuration module for TalentGraph Agent.

Manages environment variables, data file paths, model parameters,
and credential masking utilities.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for Milestone 2
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from milestone directory or workspace root
env_path = BASE_DIR / ".env"
if not env_path.exists():
    env_path = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Data paths
DATA_DIR = BASE_DIR / "data"
STUDENTS_FILE = DATA_DIR / "students.json"
INTERNSHIPS_FILE = DATA_DIR / "internships.json"
LEARNING_TOPICS_FILE = DATA_DIR / "learning_topics.json"

# Evaluation and reports paths
REPORTS_DIR = BASE_DIR / "reports"
EVALUATION_DIR = BASE_DIR / "evaluation"
TEST_QUESTIONS_FILE = EVALUATION_DIR / "test_questions.json"

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini").strip()

# Agent Execution Parameters
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "6"))


def is_live_api_configured() -> bool:
    """Check if a valid, non-placeholder OpenAI API key is present."""
    if not OPENAI_API_KEY:
        return False
    placeholders = ["your_openai_api_key_here", "sk-xxx", "placeholder", "none", "your-api-key"]
    return OPENAI_API_KEY.lower() not in placeholders and len(OPENAI_API_KEY) > 8


def mask_secret(secret: str) -> str:
    """Mask sensitive API keys for safe logging and console output."""
    if not secret:
        return "<not set>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:3]}...{secret[-4:]}"
