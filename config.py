# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Centralized configuration for the CodeCredX application.
    Loads sensitive information from environment variables.
    """
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "your-github-personal-access-token-here") # Recommended for higher rate limits

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper() # INFO, DEBUG, WARNING, ERROR, CRITICAL
    LOG_FILE: str = os.getenv("LOG_FILE", "codecredx.log")

    # GitHub API Configuration
    GITHUB_API_BASE_URL: str = "https://api.github.com/repos/"

    # LLM Configuration
    LLM_MODEL: str = "gpt-4o"
    LLM_TIMEOUT: int = 60 # seconds

# Instantiate the Config class for easy access
app_config = Config()
